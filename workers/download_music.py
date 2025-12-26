import os
import sys
import django
import logging
import time
from yt_dlp import YoutubeDL
from django.core.files import File

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'masta.settings')
django.setup()

from app.models import Track

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# get tracks with missing files
tracks = Track.objects.filter(file="")
logger.info(f"Found {tracks.count()} tracks with missing file")

ydl_opts = {
        'extract_flat': 'discard_in_playlist',
        'format': 'bestaudio',
        'fragment_retries': 10,
        'ignoreerrors': 'only_download',
        'postprocessors': [{'key': 'FFmpegExtractAudio',
                            'nopostoverwrites': False,
                            'preferredcodec': 'best',
                            'preferredquality': '5'},
                           {'key': 'FFmpegConcat',
                            'only_multi_video': True,
                            'when': 'playlist'}],
        'retries': 10,
        'warn_when_outdated': True,
        "outtmpl": "/tmp/%(id)s.%(ext)s",
}

for track in tracks:
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(track.yt_id, download=True)

        filepath = info["requested_downloads"][0]["filepath"]
        with open(filepath, "rb") as f:
            track.file.save(
                os.path.basename(filepath),
                File(f),
                save=True,
            )
        os.remove(filepath)

    time.sleep(3)

