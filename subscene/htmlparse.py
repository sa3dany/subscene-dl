import re
from lxml import etree
from xextract import Element, Group, Prefix, String, Url
from xextract.parsers import ParsingError


def outer_html(node):
    return etree.tostring(node).decode()


def strip(string):
    return string.strip()


class TooManyRequestsError(Exception):
    """Too many requests"""


class BaseParser:
    THROTTLE_PATTERN = re.compile(r"Too?.+?many.+?requests", flags=re.IGNORECASE)

    def __init__(self, html):
        self.html = html

    def parse_errors(self):
        if self.THROTTLE_PATTERN.search(self.html):
            raise TooManyRequestsError


class MovieSearchResultsParser(BaseParser):
    def __init__(self, html=""):
        super().__init__(html)
        self.data = {"exact": None, "close": None}
        self._sections = Prefix(
            css=".search-result",
            children=[
                Element(
                    name="exact", css=".exact + ul", quant="?", callback=outer_html
                ),
                Element(
                    name="close", css=".close + ul", quant="?", callback=outer_html
                ),
            ],
        )
        self._movie = Group(
            quant="*",
            css="li",
            children=[
                Url(name="url", css=".title a", quant=1),
                String(name="title", css=".title a", quant=1, callback=strip),
            ],
        )

    def parse(self, base_url=None):
        self.parse_errors()
        sections = self._sections.parse(self.html)
        exact = sections["exact"]
        if exact:
            self.data["exact"] = self._movie.parse(exact, url=base_url)
        close = sections["close"]
        if close:
            self.data["close"] = self._movie.parse(close, url=base_url)


class MoviePageParser(BaseParser):
    def __init__(self, html=""):
        super().__init__(html)
        self.data = []
        self._empty = String(quant="?", css=".subtitles.byFilm tbody tr td.empty")
        self._rows = Group(
            quant="*",
            css=".subtitles.byFilm tbody td.a1",
            children=[
                Url(name="url", css="a", quant="1"),
                String(
                    name="name",
                    css="span:last-child",
                    quant="1",
                    callback=strip,
                ),
                String(
                    name="rating",
                    css="span:first-child",
                    attr="class",
                    quant="1",
                    callback=self.parse_rating,
                ),
            ],
        )

    def parse_rating(self, rating_class):
        pattern = re.compile(r".*?(positive|neutral|bad)-icon", flags=re.IGNORECASE)
        if not pattern.match(rating_class):
            raise ParsingError
        return pattern.sub(r"\1", rating_class)

    def parse(self, base_url=None):
        self.parse_errors()
        if not self._empty.parse(self.html):
            self.data = self._rows.parse(self.html, url=base_url)


class SubtitlePageParser(BaseParser):
    def __init__(self, html=""):
        super().__init__(html)
        self.data = None
        self._download = Url(quant="1", css=".download a")

    def parse(self, base_url=None):
        self.data = self._download.parse(self.html, url=base_url)
