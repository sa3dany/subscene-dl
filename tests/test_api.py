import doctest
import unittest
from pathlib import Path
from collections import namedtuple
from unittest.mock import Mock, patch, call

from subscene import api

SAMPLES = Path(__file__).parent / "samples"


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(api, optionflags=doctest.ELLIPSIS))
    return tests


class TestTitleSearch(unittest.TestCase):
    def setUp(self):
        self.sc = api.Subscene()

    def tearDown(self):
        self.sc = None

    @patch("subscene.api.Subscene._post")
    def test_exact(self, mock_post):
        mock_post.return_value.text = (SAMPLES / "search/exact.html").read_text()
        data = self.sc.search_titles("Official Secrets")
        self.assertEqual(
            data["results"]["exact"],
            [
                {
                    "url": f"{api.BASE_URL}/subtitles/official-secrets",
                    "title": "Official Secrets",
                    "year": "2019",
                }
            ],
        )

    @patch("subscene.api.Subscene._post")
    def test_section_existance(self, mock_post):
        mock_post.return_value.text = (SAMPLES / "search/popular_2.html").read_text(
            encoding="utf-8"
        )
        data = self.sc.search_titles("Miss and Mrs Cops")
        self.assertEqual(data["results"]["exact"], [])
        self.assertEqual(data["results"]["close"], [])

    @patch("subscene.api.Subscene._post")
    def test_popular(self, mock_post):
        mock_post.return_value.text = (SAMPLES / "search/popular_2.html").read_text(
            encoding="utf-8"
        )
        data = self.sc.search_titles("Miss and Mrs Cops")
        self.assertEqual(len(data["results"]["popular"]), 12)
        self.assertEqual(
            data["results"]["popular"][8],
            {
                "url": f"{api.BASE_URL}/subtitles/playboy-cops-fa-fa-ying-king",
                "title": "Playboy Cops (花花型警 / Fa fa ying king)",
                "year": "2008",
            },
        )

    @patch("subscene.api.Subscene._post")
    def test_section_count(self, mock_post):
        mock_post.return_value.text = (SAMPLES / "search/exact.html").read_text()
        data = self.sc.search_titles("Miss and Mrs Cops")
        self.assertEqual(len(list(data["results"])), 3)


class TestTitle(unittest.TestCase):
    def setUp(self):
        self.sc = api.Subscene()

    def tearDown(self):
        self.sc = None

    @patch("subscene.api.Subscene._get")
    def test_many(self, mock_get):
        mock_get.return_value.text = (SAMPLES / "movie/movie.html").read_text(
            encoding="utf-8"
        )
        data = self.sc.get_title("", api.LANGUAGES.AR)
        self.assertEqual(len(data["subtitles"]), 16)
        self.assertEqual(
            data["subtitles"][0],
            {
                "url": "https://subscene.com/subtitles/official-secrets/arabic/2159626",
                "name": "Official.Secrets.BluRay",
                "rating": "positive",
            },
        )

    @patch("subscene.api.Subscene._get")
    def test_empty(self, mock_get):
        mock_get.return_value.text = (SAMPLES / "movie/movie-empty.html").read_text(
            encoding="utf-8"
        )
        data = self.sc.get_title("", api.LANGUAGES.AR)
        self.assertEqual(data, {"subtitles": []})

    @patch("subscene.api.Subscene._get")
    def test_referer(self, mock_get):
        mock_get.return_value.text = (SAMPLES / "movie/movie-empty.html").read_text(
            encoding="utf-8"
        )
        data = self.sc.get_title("x", api.LANGUAGES.AR)
        mock_get.assert_called_with("x", headers={"Referer": api.ENDPOINTS.SEARCH.value})


class TestSubtitle(unittest.TestCase):
    def setUp(self):
        self.sc = api.Subscene()
        self.r = namedtuple("r", ["content", "text"])
        self.values = {
            "https://subscene.com/subtitles/official-secrets/arabic/2088118": self.r(
                content=None,
                text=(SAMPLES / "subtitle/subtitle.html").read_text(encoding="utf-8"),
            ),
            "https://subscene.com/subtitles/arabic-text/tb-75H99hPT5akNHyzyJla9ZN-r_V8IVepJ3sNZNVAHQ8vX4OvGjiskcIlADZs6DDEUzyRN5Skwpdhz4Tlggyx8Q-S3GUe_1W2aiZlH3exU81t32ZxBOntgPa2bZ9YfD0": self.r(
                content=(SAMPLES / "subtitle/multi-file.zip").read_bytes(), text=None
            ),
        }

    def tearDown(self):
        self.sc = None

    def _get(self, url, **kwargs):
        return self.values[url]

    @patch("subscene.api.Subscene._get")
    def test_extracting(self, mock_get):
        mock_get.side_effect = self._get
        data = self.sc.get_subtitle(
            "https://subscene.com/subtitles/official-secrets/arabic/2088118"
        )
        self.assertEqual(
            data["files"][0]["name"], "The.Terminal.PROPER.DVDRip.XViD-ALLiANCE-CD1.srt"
        )
        self.assertEqual(len(data["files"][0]["body"].read()), 50640)
        self.assertEqual(
            data["files"][1]["name"], "The.Terminal.PROPER.DVDRip.XViD-ALLiANCE-CD2.srt"
        )
        self.assertEqual(len(data["files"][1]["body"].read()), 45084)

    @patch("subscene.api.Subscene._get")
    def test_referer(self, mock_get):
        mock_get.side_effect = self._get
        data = self.sc.get_subtitle(
            "https://subscene.com/subtitles/official-secrets/arabic/2088118"
        )
        calls = [
            call(
                "https://subscene.com/subtitles/official-secrets/arabic/2088118",
                headers={"Referer": "https://subscene.com/subtitles/official-secrets"},
            ),
            call(
                "https://subscene.com/subtitles/arabic-text/tb-75H99hPT5akNHyzyJla9ZN-r_V8IVepJ3sNZNVAHQ8vX4OvGjiskcIlADZs6DDEUzyRN5Skwpdhz4Tlggyx8Q-S3GUe_1W2aiZlH3exU81t32ZxBOntgPa2bZ9YfD0",
                headers={
                    "Referer": "https://subscene.com/subtitles/official-secrets/arabic/2088118"
                },
            ),
        ]
        mock_get.assert_has_calls(calls)


if __name__ == "__main__":
    unittest.main()
