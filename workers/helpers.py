import requests
from django.core.files.base import ContentFile
from urllib.parse import urlparse
from django.conf import settings
import os
import uuid
from mutagen.oggopus import OggOpus


def download_and_save_image(obj, url):
    if not url:
        return 
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    filename = uuid.uuid4().hex + ".jpg"

    obj.save(filename, ContentFile(response.content), save=True)
    

ARTIST_NFO_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<artist>
    <name>{name}</name>
    <sortname>{name}</sortname>
    <type>Person</type>
    <gender></gender>
    <disambiguation></disambiguation>{genres}
    <style></style>
    <mood></mood>
    <yearsactive></yearsactive> 
    <born></born>
    <formed></formed>
    <biography>{bio}</biography>
    <died></died>
    <disbanded></disbanded>
</artist>
"""

def save_artist_nfo(artist):
    genres = ""
    for genre in artist.genres.all():
        genres += f"\n    <genre>{genre.name}</genre>"
    content = ARTIST_NFO_TEMPLATE.format(name=artist.name, genres=genres, bio=artist.bio)
    path = os.path.join(settings.BASE_DIR, settings.MEDIA_ROOT, "music", artist.name)
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    file = os.path.join(path, "artist.nfo")
    with open(file, "w") as f:
        f.write(content)


def write_metadata(filepath, track):
    audio = OggOpus(filepath)

    # basic required tags
    audio["title"] = track.title
    if track.featured_artists.count() > 0:
        artists = track.album.artist.name
        for feat_art in track.featured_artists.all():
            artists += f";{feat_art.name}"
        audio["artists"] = artists
    else:
        audio["artist"] = track.album.artist.name
    audio["album"] = track.album.title
    audio["albumartist"] = track.album.artist.name
    audio["tracknumber"] = str(track.order)

    audio.save()

