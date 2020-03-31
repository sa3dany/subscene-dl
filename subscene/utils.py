import requests
import re
import zipfile

from html.parser import HTMLParser
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


class MoviePageParser(HTMLParser):
    def error(self, message):
        pass

    LOCATIONS = {"TBODY": 0, "TR": 1, "TD_FIRST": 2, "NAME": 3}
    RATING = {"NEUTRAL": 0, "POSITIVE": 1}
    SOURCE = {"BLURAY": "br", "WEB": "web"}

    def __init__(self, url, subtitle_type=None):
        HTMLParser.__init__(self)
        self.url = url
        self.source = subtitle_type
        self.subtitle = {"url": None, "rating": None, "name": None}
        self.location = None

    def handle_starttag(self, tag, attrs):
        if self.check_subtitle():
            return

        if tag == "tbody":
            self.location = self.LOCATIONS["TBODY"]

        elif tag == "tr":
            if self.location == self.LOCATIONS["TBODY"]:
                self.location = self.LOCATIONS["TR"]

        elif tag == "td":
            if self.location == self.LOCATIONS["TR"]:
                if dict(attrs).get("class", None) == "a1":
                    self.location = self.LOCATIONS["TD_FIRST"]

        elif tag == "a":
            if self.location == self.LOCATIONS["TD_FIRST"]:
                self.subtitle["url"] = f'{self.url}{dict(attrs)["href"]}'

        elif tag == "span":
            if self.location == self.LOCATIONS["TD_FIRST"]:
                class_list = dict(attrs).get("class", None)
                if class_list:
                    if "positive" in class_list:
                        self.subtitle["rating"] = self.RATING["POSITIVE"]
                    else:
                        self.subtitle["rating"] = self.RATING["NEUTRAL"]
                else:
                    self.location = self.LOCATIONS["NAME"]

    def handle_data(self, data):
        if self.location == self.LOCATIONS["NAME"]:
            self.subtitle["name"] = data.strip()

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.location = None

        elif tag == "tr":
            self.location = self.LOCATIONS["TBODY"]

        elif tag == "td":
            if self.location != None:
                self.location = self.LOCATIONS["TR"]

        elif tag == "span":
            if self.location == self.LOCATIONS["NAME"]:
                self.location = self.LOCATIONS["TR"]

    def check_subtitle(self):
        name = self.subtitle["name"]
        if not name:
            return False

        if self.subtitle["rating"] != self.RATING["POSITIVE"]:
            return False

        if not self.source:
            return True

        if self.source == self.SOURCE["BLURAY"]:
            if re.search(r"bluray|brrip|bdrip", name, flags=re.IGNORECASE):
                return True
        elif self.source == self.SOURCE["WEB"]:
            if re.search(r"webrip|web-dl", name, flags=re.IGNORECASE):
                return True
        else:
            return False

    def get_subtitle_url(self):
        if self.check_subtitle():
            return self.subtitle["url"]
        return None


class SubtitlePageParser(HTMLParser):
    def error(self, message):
        pass

    def __init__(self, url):
        HTMLParser.__init__(self)
        self.url = url
        self.download_url = None
        self.in_download = False

    def handle_starttag(self, tag, attrs):
        if self.download_url:
            return

        attrs_dict = dict(attrs)
        if attrs_dict.get("class", None) == "download":
            self.in_download = True

        elif self.in_download and tag == "a":
            self.download_url = f'{self.url}{attrs_dict["href"]}'

    def handle_data(self, data):
        pass

    def handle_endtag(self, tag):
        if self.in_download and tag == "a":
            self.in_download = False

    def get_download_url(self):
        return self.download_url
