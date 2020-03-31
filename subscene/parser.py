from html.parser import HTMLParser


class MovieSearchResultsParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.movie_url = None

        self._in_exact = False
        self._in_exact_item = False

    def handle_starttag(self, tag, attrs):
        if self.movie_url:
            return

        attrs_dict = dict(attrs)
        if attrs_dict.get("class", None) == "exact":
            self.in_exact = True

        elif self.in_exact and tag == "a":
            self.in_exact_item = True
            self.movie_url = attrs_dict["href"]

    def handle_data(self, data):
        if self.in_exact_item:
            print(f"Exact match: {data}")

    def handle_endtag(self, tag):
        if self.in_exact and tag == "ul":
            self.in_exact = False

        elif self.in_exact_item and tag == "a":
            self.in_exact_item = False
