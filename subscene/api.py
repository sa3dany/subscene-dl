import os
import time
import zipfile
import requests
from enum import Enum
from io import BytesIO
from typing import Dict
from urllib.parse import urlparse
from collections import namedtuple

from subscene import htmlparse, utils

BASE_URL = "https://subscene.com"


class ENDPOINTS(Enum):
    SEARCH = f"{BASE_URL}/subtitles/searchbytitle"
    TITLE = f"{BASE_URL}/subtitles"


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


class Subscene:
    """Acts as an API for subscene.com

    Since subscene.com does not have apublic API this class aims to
    emulate one. For each public method we parse the response html and
    return structured data.
    """

    def __init__(self):
        # As of Apr 2020, subscene.com is using CloudFlare. We make sure
        # to use the same session across all requets from the class so
        # that we can persist cookies that are set by CloudFlare. I am
        # not sure but creating new sessions and not persisting these
        # cookies might flag us more as bots.
        self._session = requests.Session()

    def _get(self, url, headers={}):
        """Perform a get request using a persistent requests session"""
        return self._session.get(url, headers=headers)

    def _post(self, url, data):
        """Perform a post request using a persistent requests session

        Aditionally, a special field "l" with en empty value is added to
        match the search form on subscene.com.
        """
        return self._session.post(url, {**data, "l": ""})

    def _editfilter(self, language: LANGUAGES, hi: HI, foreign_only: bool):
        self._session.cookies = requests.cookies.cookiejar_from_dict(
            {
                "ForeignOnly": str(foreign_only),
                "LanguageFilter": str(language),
                "HearingImpaired": str(hi),
                "SortSubtitlesByDate": str(False).lower(),
            },
            self._session.cookies,
        )

    def _unzip(self, rawbytes: bytes) -> str:
        """Returns file references of all items in a zip file"""
        filestype = namedtuple("SubtitleFile", ["name", "body"])
        files = []
        zippedfile = zipfile.ZipFile(rawbytes)
        for name in zippedfile.namelist():
            for file_type in FILE_TYPES:
                if not name.endswith(file_type.value):
                    continue
                files.append(filestype(name, zippedfile.open(name)))
        return files

    def search_titles(self, query: str) -> Dict:
        """Searches for a title on subscene & returns the results

        Parameters:
            query: search query

        Return Syntax: {
            'results': {
                'exact': [Title],
                'close': [Title],
                'popular': [Title]
            }
        }

        Title: {
            'url': 'string',
            'title': 'string',
            'year': 'string'
        }
        """
        r = self._post(ENDPOINTS.SEARCH.value, data={"query": query})

        parser = htmlparse.TitleSearchResultsParser()
        parser.html = r.text
        data = parser.parse(base_url=BASE_URL)

        responce = {"results": {"exact": [], "close": [], "popular": []}}

        for key, section in data.items():
            responce["results"][key] = section
            for title in section:
                titleparts = utils.parsetitle(title["title"])
                title["title"] = titleparts.title
                title["year"] = titleparts.year

        return responce

    def get_title(
        self,
        url: str,
        language: LANGUAGES,
        hi: HI = HI.HIANY,
        foreign_only: bool = False,
    ) -> Dict:
        """Get a list of subtitles for a title

        Parameters:
            url: URL of the title page
            language: subtitles language

        Options:
            foreign_only: Flag for subtitles with foreign-only parts
            hi: Hearing impaired flag. Possible values:
                subscene.HIANY
                subscene.HIONLY
                subscene.HINONE

        Return syntax: {
            'subtitles': [
                'url': 'string',
                'name': 'string',
                'rating': 'positive'|'neutral'|'bad'
            ]
        }
        """
        self._editfilter(language, hi.value, foreign_only)
        r = self._get(url, headers={"Referer": ENDPOINTS.SEARCH.value},)
        parser = htmlparse.TitlePageParser()
        parser.html = r.text
        data = parser.parse(base_url=BASE_URL)

        responce = {"subtitles": data}

        return responce

    def get_subtitle(self, url: str) -> Dict:
        """Get subtitle file (or files)

        Parameters:
            url: Subtitle page URL

        Returns syntax:
            {
                'files': [
                    'name': 'string',
                    'body': zipfile.ZipExtFile()
                ]
            }
        """
        r1 = self._get(url, headers={"Referer": "/".join(url.split("/")[0:-2])})

        parser = htmlparse.SubtitlePageParser()
        parser.html = r1.text
        zip_url = parser.parse(base_url=BASE_URL)

        r2 = self._get(zip_url, headers={"Referer": url})

        zip_bytes = r2.content
        zip_files = self._unzip(BytesIO(zip_bytes))

        responce = {
            "files": [{"name": file.name, "body": file.body} for file in zip_files]
        }

        return responce
