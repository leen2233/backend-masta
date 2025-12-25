import requests
from django.core.files.base import ContentFile
from urllib.parse import urlparse
import os
import uuid


def download_and_save_image(obj, url):
    if not url:
        return 
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    filename = uuid.uuid4().hex + ".jpg"

    obj.save(filename, ContentFile(response.content), save=False)
    

