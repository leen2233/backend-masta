import sys
import os
import django
import argparse
import logging
import pprint
from ytmusicapi import YTMusic
from django.db.models import Q
from datetime import date
from yt_dlp import YoutubeDL

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'masta.settings')
django.setup()

from app.models import Artist, Album, Track
from workers.helpers import download_and_save_image, save_artist_nfo

ytmusic = YTMusic()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description="Update metadata")
parser.add_argument("--name", action="store_true", help="Update metadata of artists with blank name")
parser.add_argument("--banner", action="store_true", help="Update metadata of artists with no banner image")
parser.add_argument("--album", action="store_true", help="Update album metadata of artists with no album")
parser.add_argument("--pp", action="store_true", help="Update profile pic of artists with no profile pic")
parser.add_argument("--tracks", action="store_true", help="Update tracks of albums")
args = parser.parse_args()

if args.name or args.banner or args.album:
    query = Q()
    if args.name:
        query &= Q(name__isnull=True) | Q(name="")

    if args.banner:
        query &= Q(banner__isnull=True) | Q(banner="")

    if args.album:
        query &= Q(albums__isnull=True, parse_tracks=True)

    artists_to_fetch = Artist.objects.filter(query)

    logger.info(f"Found {artists_to_fetch.count()} artists to update metadata")

    for artist in artists_to_fetch:
        logger.debug(f"Processing artist with id: {artist.yt_id}")
        try:
            metadata = ytmusic.get_artist(artist.yt_id)
        except:
            continue

        artist.name = metadata.get("name")
        artist.bio = metadata.get("description")
        artist.save()

        # save metadata to nfo file
        save_artist_nfo(artist)

        if len(metadata.get("thumbnails")) > 0 and (artist.banner.name == "" or artist.banner is None):
            url = metadata.get("thumbnails", [{}])[1].get("url")
            download_and_save_image(artist.banner, url)


        if artist.parse_tracks:
            # update albums
            logger.debug(f"Saving albums of artist {artist.name}")
            for album in metadata.get("albums", {"results": []}).get("results"):
                if not Album.objects.filter(yt_id=album.get("browseId")).exists():
                    album_obj = Album.objects.create(
                            title=album.get("title"),
                            yt_id=album.get("browseId"),
                            release_date=date(int(album.get("type")), 1, 1), # because type is actually presents year, it is misnamed at ytmusicapi package
                            artist=artist
                    )
                    album_obj.save()

                    download_and_save_image(album_obj.cover, album.get("thumbnails", [{}])[-1].get("url"))
            
            # create Single album
            logger.debug(f"Saving singles of artist {artist.name}")
            if metadata.get("singles", {}).get("browseId") and args.tracks:
                browseId = metadata.get("singles").get("browseId")
                params = metadata.get("singles", {}).get("params")
                singles = ytmusic.get_artist_albums(browseId, params)
                for single in singles:
                    album = Album.objects.create(
                            title=single.get("title"),
                            type=single.get("type").lower(),
                            yt_id=single.get("browseId"),
                            release_date=date(int(single.get("year")), 1, 1),
                            artist=artist
                    )
                    album.save()
                    download_and_save_image(album.cover, single.get("thumbnails", [{}])[-1].get("url"))
        else:
            logger.debug(f"Passing artist {artist.name}, because parse_tracks is False")
            
    logger.info("Completed updating artists metadata")

if args.pp:
    artists = Artist.objects.filter(profile_picture="")
    logger.info(f"Found {artists.count()} artists with no profile image. Starting...")

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }

    for artist in artists:
        with YoutubeDL(ydl_opts) as ydl:
            artist_url = artist.yt_id if artist.yt_id.startswith("https://") else f"https://youtube.com/channel/{artist.yt_id}"
            info = ydl.extract_info(artist_url, download=False)
            if info.get("thumbnails"):
                pprint.pprint(info.get("thumbnails"))
                url = info.get("thumbnails", [{}])[0].get("url")
                download_and_save_image(artist.profile_picture, url)
                artist.save()

    logger.info("Completed updating artists profile pictures")

if args.tracks:
    albums = Album.objects.filter(tracks__isnull=True)
    logger.info(f"Found {albums.count()} albums with no tracks. Starting...")
    for album in albums:
        metadata = ytmusic.get_album(album.yt_id)
        album.title = metadata.get("title")
        album.track_count = int(metadata.get("trackCount", 0))
        album.save()

        if album.cover.name == "" or album.cover is None:
            download_and_save_image(album.cover, metadata.get("thumbnails", [{}])[-1].get("url"))
        
        for track in metadata.get("tracks", []):
            track_obj, created = Track.objects.get_or_create(
                    yt_id=track.get("videoId"),
                    defaults={
                        "title": track.get("title"),
                        "order": track.get("trackNumber"),
                        "duration": track.get("duration_seconds"),
                        "album": album,
                    }
            )

            for artist in track.get("artists"):
                if artist.get("id") and artist.get("name") != album.artist.name:
                    artist, created = Artist.objects.get_or_create(
                            yt_id=artist.get("id"), 
                            defaults={
                                "name": artist.get("name"),
                                "parse_tracks": False
                            }
                    )
                    if artist not in track_obj.featured_artists.all():
                        track_obj.featured_artists.add(artist)
        logger.debug(f"Completed updating album {album.title}, with track count: {album.track_count}")
    logger.info("Completed updating tracks metadata")

