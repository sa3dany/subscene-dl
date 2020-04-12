import requests
import zipfile
import time
import re
import os
from enum import Enum
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

    # These are taken from the filter page on subscene.com. They all
    # have keys corresponding to the ISO 639-1 (with fallback to 639-3
    # if a 2 letter code is not avilable) code except for Brazillian
    # Portuguese which does not have a coresponding code and instead I
    # choose to use the IETF tag 'pt-BR'
    class LANGUAGES(Enum):
        SQ = 1
        AR = 2
        PT_BR = 4
        BG = 5
        HR = 8
        CS = 9
        DA = 10
        NL = 11
        EN = 13
        ET = 16
        FI = 17
        FR = 18
        DE = 19
        EL = 21
        IW = 22
        HU = 23
        IS = 25
        IT = 26
        JA = 27
        KO = 28
        LV = 29
        NO = 30
        PL = 31
        PT = 32
        RO = 33
        RU = 34
        SR = 35
        SK = 36
        SL = 37
        ES = 38
        SV = 39
        TH = 40
        TR = 41
        UR = 42
        LT = 43
        ID = 44
        VI = 45
        FA = 46
        EO = 47
        MK = 48
        CA = 49
        MS = 50
        HI = 51
        KU = 52
        TL = 53
        BN = 54
        AZ = 55
        UK = 56
        KL = 57
        SI = 58
        TA = 59
        BS = 60
        MY = 61
        KA = 62
        TE = 63
        ML = 64
        MNI = 65
        PA = 66
        PS = 67
        BE = 68
        SO = 70
        YO = 71
        MN = 72
        HY = 73
        EU = 74
        SW = 75
        SU = 76
        KN = 78
        KM = 79
        NE = 80

    # The following `languages` dot not have a language code since they
    # either refer to an encoding or dual-language subtitle zip files.
    # You can still use the numeric id to get subtitles with these
    # language IDs, but dual-subtitle language IDs have no defined
    # behaviour.
    #
    #   - Big 5 code (3)
    #   - Bulgarian/ English (6)
    #   - Chinese BG code (7)
    #   - Dutch/ English (12)
    #   - English/ German (15)
    #   - Hungarian/ English (24)

    # These are the flags used by subscene to filter subtitles based on
    # the availiablity of HI tags. These values are sent as request
    # cookie "HearingImpaired"
    class HI(Enum):
        HIANY = 2
        HIONLY = 1
        HINONE = 0

    class RATING(Enum):
        """Rating scale used by subscene.com.

        Subscene only exposes these textual ratings and does not prodive
        a numerical scale.
        """

        POSITIVE = "positive"
        NEUTRAL = "neutral"
        BAD = "bad"

    class FILE_TYPES(Enum):
        SRT = "srt"
        SRT_STYLE = "srt.style"
        SUB = "sub"
        TXT = "txt"
        SSA = "ssa"
        ASS = "ass"
        SMI = "smi"

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
                    # handles both BOM and non-BOM utf-8 files. We
                    # fallback to window-1256 encoding since many of the
                    # Arabic subtitles use that encoding¯\_(ツ)_/¯
                    file_contents = subtitle_file.read()
                    try:
                        return file_contents.decode("utf-8-sig")
                    except UnicodeDecodeError:
                        return file_contents.decode("windows-1256")

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
        self, title_id: str, language: int, foreign_only=False, hi=2
    ) -> List[Dict]:
        """Get a list of available subtitles for a given title.

        Parameters:
            title_id: Title (film/tv) ID.
            language: Language code for subtitles.

        Options:
            foreign_only: Flag for subtitles for foreign-only parts.
            hi: Hearing impaired flag. Possible values:
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
                LanguageFilter=str(language),
                HearingImpaired=str(hi),
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
