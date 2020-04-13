import re
from lxml import etree
from typing import Dict
from xextract.parsers import ParsingError
from xextract import Element, Group, Prefix, String, Url


class TooManyRequestsError(Exception):
    """Too many requests"""


class BaseParser:
    THROTTLE_PATTERN = re.compile(r"Too?.+?many.+?requests", flags=re.IGNORECASE)

    def __init__(self, html):
        self.html = html

    def _strip(self, string: str):
        """Strips excess spaces & converts newlines to spaces"""
        return re.sub(r"\s{2,}", " ", re.sub(r"\r?\n", " ", string.strip()))

    def _parse_errors(self) -> None:
        """Throws if page content indicates a know error state"""
        if self.THROTTLE_PATTERN.search(self.html):
            raise TooManyRequestsError


class TitleSearchResultsParser(BaseParser):
    def __init__(self, html: str = ""):
        super().__init__(html)
        self._sections = Prefix(
            css=".search-result",
            children=[
                Element(name="exact", css=".exact + ul", callback=self._outerhtml),
                Element(name="close", css=".close + ul", callback=self._outerhtml),
                Element(name="popular", css=".popular + ul", callback=self._outerhtml,),
            ],
        )
        self._movies = Group(
            quant="*",
            css="li",
            children=[
                Url(name="url", css=".title a", quant=1),
                String(name="title", css=".title a", quant=1, callback=self._strip),
            ],
        )

    def _outerhtml(self, etree_node):
        """Returns outer html for an HTML node"""
        return etree.tostring(etree_node).decode()

    def parse(self, base_url: str = None) -> Dict:
        self._parse_errors()
        sections = {}
        for key, section in self._sections.parse(self.html).items():
            if section:
                sections[key] = []
                for movie in self._movies.parse(section[0], url=base_url):
                    sections[key].append(movie)
        return sections


class TitlePageParser(BaseParser):
    def __init__(self, html: str = ""):
        super().__init__(html)
        self._empty = String(quant="?", css=".subtitles.byFilm tbody tr td.empty")
        self._rows = Group(
            quant="+",
            css=".subtitles.byFilm tbody td.a1",
            children=[
                Url(name="url", css="a", quant=1),
                String(
                    name="name", css="span:last-child", quant=1, callback=self._strip,
                ),
                String(
                    name="rating",
                    css="span:first-child",
                    attr="class",
                    quant=1,
                    callback=self._parse_rating,
                ),
            ],
        )

    def _parse_rating(self, rating_class: str) -> str:
        """Extract rating from icon class name"""
        pattern = re.compile(r".*?(positive|neutral|bad)-icon", flags=re.IGNORECASE)
        if not pattern.match(rating_class):
            raise ParsingError
        return pattern.sub(r"\1", rating_class)

    def parse(self, base_url: str = None) -> Dict:
        self._parse_errors()
        if self._empty.parse(self.html):
            return []
        return self._rows.parse(self.html, url=base_url)


class SubtitlePageParser(BaseParser):
    def __init__(self, html: str = ""):
        super().__init__(html)
        self._download = Url(quant="1", css=".download a")

    def parse(self, base_url: str = None) -> Dict:
        self._parse_errors()
        return self._download.parse(self.html, url=base_url)
