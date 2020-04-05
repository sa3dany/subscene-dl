import requests
import zipfile
import time
import re
import os
from io import BytesIO
from urllib.parse import urlparse
from jellyfish import jaro_winkler
from typing import List, Dict, Optional

from subscene import htmlparse
from urllib.parse import urlparse


BASE_URL = "https://subscene.com"
ENDPOINTS = {
    "searchbytitle": f"{BASE_URL}/subtitles/searchbytitle",
    "subtitles": f"{BASE_URL}/subtitles",
}


class Subscene:
    """Acts as an API for subscene.com

    Since subscene.com does not have apublic API this class aims to
    emulate one. For each public method we parse the response html and
    return structured data.
    """

    # These are taken for the popular languages section on subscene.com.
    # More languages are supported by subscene.com.
    LANGUAGES = {
        "ar": {"description": "Arabic", "subscene_id": "2", "code": "ar"},
        "da": {"description": "Danish", "subscene_id": "10", "code": "da"},
        "nl": {"description": "Dutch", "subscene_id": "11", "code": "nl"},
        "en": {"description": "English", "subscene_id": "13", "code": "en"},
        "fa": {"description": "Persian", "subscene_id": "46", "code": "fa"},
        "fi": {"description": "Finnish", "subscene_id": "17", "code": "fi"},
        "fr": {"description": "French", "subscene_id": "18", "code": "fr"},
        "el": {"description": "Greek", "subscene_id": "21", "code": "el"},
        "iw": {"description": "Hebrew", "subscene_id": "22", "code": "iw"},
        "id": {"description": "Indonesian", "subscene_id": "44", "code": "id"},
        "it": {"description": "Italian", "subscene_id": "26", "code": "it"},
        "ko": {"description": "Korean", "subscene_id": "28", "code": "ko"},
        "ms": {"description": "Malay", "subscene_id": "50", "code": "ms"},
        "no": {"description": "Norwegian", "subscene_id": "30", "code": "no"},
        "pt": {"description": "Portuguese", "subscene_id": "32", "code": "pt"},
        "ro": {"description": "Romanian", "subscene_id": "33", "code": "ro"},
        "es": {"description": "Spanish", "subscene_id": "38", "code": "es"},
        "sv": {"description": "Swedish", "subscene_id": "39", "code": "sv"},
        "tr": {"description": "Turkish", "subscene_id": "41", "code": "tr"},
        "vi": {"description": "Vietnamese", "subscene_id": "45", "code": "vi"},
        "pt-br": {
            "description": "Brazillian Portuguese",
            "subscene_id": "4",
            "code": "pt",
        },
    }

    # These are the flags used by subscene to filter subtitles based on
    # the availiablity of HI tags. These values are sent as request
    # cookie "HearingImpaired"
    HIANY = 2
    HIONLY = 1
    HINONE = 0

    def __init__(self):
        # As of Apr 2020, subscene.com is using CloudFlare. We make sure
        # to use the same session across all requets from the class so
        # that we can persist cookies that are set by CloudFlare. I am
        # not sure but creating new sessions and not persisting these
        # cookies might flag us more as bots.
        self._session = requests.Session()

    def _get(self, url, cookies={}, headers={}):
        """Perform a get request using a persistent requests session."""
        r = self._session.get(url, cookies=cookies, headers=headers)
        return r

    def _post(self, url, data):
        """Perform a post request using a persistent requests session.
        Aditionally, a special field "l" with en empty value is added to
        match the search form on subscene.com.
        """
        r = self._session.post(url, {**data, "l": ""})
        return r.text

    def _extract_sub(self, rawbytes: bytes):
        """Extracts the first SRT file from subtitle zip files"""
        subtitle_zip = zipfile.ZipFile(rawbytes)
        for name in subtitle_zip.namelist():
            if name.endswith(".srt"):
                with subtitle_zip.open(name) as subtitle_file:
                    # Here we are using "utf-8-sig" since it correcly
                    # handles both BOM and non-BOM utf-8 files
                    return subtitle_file.read().decode("utf-8-sig")

    def _parse_title(self, title):
        """Parses a film title and returns a dict with the title and year
        separated.
        """
        match = re.match(r"(.+)\s+\(([12][0-9]{3})\)", title, flags=re.IGNORECASE)
        return {"title": match.group(1), "year": match.group(2)}

    def _match_movie(self, title, year, matches):
        if matches["exact"]:
            # If a single exact match, just return that
            if len(matches["exact"]) == 1:
                return matches["exact"][0]
            # Else, look for the exact match with same year as our title
            for match in matches["exact"]:
                match_year = self._parse_title(match["title"])["year"]
                if match_year == year:
                    return match
        # If only close matches, return the closest with the same year
        if matches["close"]:
            best_score = 0
            best_match = None
            same_year_matches = [
                match
                for match in matches["close"]
                if self._parse_title(match["title"])["year"] == year
            ]
            for match in same_year_matches:
                match_title = self._parse_title(match["title"])["title"]
                score = jaro_winkler(match_title, title)
                if score > best_score:
                    best_score = score
                    best_match = match
            return best_match
        return None

    def searchbytitle(self, title: str, year: str) -> Optional[Dict]:
        """Searches for a movie on subscene & returns the best match.

        Parameters:
            title: Movie name
            year: Movie release year

        Returns:
            a Movie match or None if no matching movies were found.
        """
        parser = htmlparse.MovieSearchResultsParser()
        parser.html = self._post(ENDPOINTS["searchbytitle"], data={"query": title})
        parser.parse(base_url=BASE_URL)

        match = self._match_movie(title, year, parser.data)
        if not match:
            return None

        return {"id": os.path.basename(urlparse(match["url"]).path), **match}

    def subtitles(
        self, title_id: str, language: str, foreign_only=False, hi_flag=2
    ) -> List[Dict]:
        """Get a list of available subtitles for a given title.

        Parameters:
            title_id: Title (film/tv) ID.
            language: Language code for subtitles.

        Options:
            foreign_only: Flag for subtitles for foreign-only parts.
            hi_flag: Hearing impaired flag. Possible values:
                >>> Subscene.HIANY      # Any (default)
                2
                >>> Subscene.HIONLY     # Only subtitles with HI tags
                1
                >>> Subscene.HINONE     # Only subtitles without HI tags
                0

        Returns:
            List of subtitles or empty list if none found.
        """
        parser = htmlparse.MoviePageParser()
        parser.html = self._get(
            f"{ENDPOINTS['subtitles']}/{title_id}",
            headers=dict(Referer=ENDPOINTS["searchbytitle"]),
            cookies=dict(
                ForeignOnly=str(foreign_only),
                LanguageFilter=language,
                HearingImpaired=str(hi_flag),
                SortSubtitlesByDate=str(False).lower(),
            ),
        ).text
        parser.parse(base_url=BASE_URL)

        subtitles = parser.data
        return subtitles

    def download(self, url: str) -> Optional[str]:
        """Download a subtitle from subscene using it's page URL.

        This method will return the subtitle text as a string.

        Parameters:
            url: The subtitle page url.

        Returns:
            The subtitle file contents as a string. Or None in-case a
            download link could not be found.
        """
        # Get the URL of the movie page to use in the Referer header
        title_url = f"{BASE_URL}{'/'.join(urlparse(url).path.split('/')[0:3])}"

        parser = htmlparse.SubtitlePageParser()
        parser.html = self._get(url, headers=dict(Referer=title_url)).text
        parser.parse(base_url=BASE_URL)

        download_url = parser.data
        if not download_url:
            return None

        r = self._get(download_url, headers=dict(Referer=url))
        return self._extract_sub(BytesIO(r.content))
