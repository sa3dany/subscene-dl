import requests
import re
import zipfile
from io import BytesIO


def get_language_id(language_code):
    id_dict = {"ar": "2", "en": "13"}
    return id_dict.get(language_code, "")


def extract_subtitle(raw):
    filebytes = BytesIO(raw)
    subtitle_zip = zipfile.ZipFile(filebytes)
    for name in subtitle_zip.namelist():
        if name.endswith(".srt"):
            with subtitle_zip.open(name) as subtitle_file:
                return subtitle_file.read().decode("utf-8-sig")
