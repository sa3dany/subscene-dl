import unittest
import tempfile
import argparse
import doctest
from pathlib import Path

import subscene.cli
from subscene.api import BASE_URL
from subscene.htmlparse import (
    TooManyRequestsError,
    MovieSearchResultsParser,
    MoviePageParser,
    SubtitlePageParser,
)

SAMPLES = Path(__file__).parent / "samples"


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(subscene.cli, optionflags=doctest.ELLIPSIS))
    tests.addTests(doctest.DocTestSuite(subscene.api, optionflags=doctest.ELLIPSIS))
    return tests


class TestMovieSearchResultsParsing(unittest.TestCase):
    def setUp(self):
        self.parser = MovieSearchResultsParser()

    def tearDown(self):
        self.parser = None

    def test_exact(self):
        self.parser.html = (SAMPLES / "search/exact.html").read_text()
        self.parser.parse(base_url=BASE_URL)
        self.assertEqual(
            self.parser.data["exact"],
            [
                {
                    "title": "Official Secrets (2019)",
                    "url": f"{BASE_URL}/subtitles/official-secrets",
                }
            ],
        )

    def test_multi_exact(self):
        self.parser.html = (SAMPLES / "search/multi_exact.html").read_text()
        self.parser.parse(base_url=BASE_URL)
        self.assertListEqual(
            self.parser.data["exact"],
            [
                {
                    "title": "The Parent Trap (1998)",
                    "url": f"{BASE_URL}/subtitles/walt-disneys-the-parent-trap",
                },
                {
                    "title": "The Parent Trap (1961)",
                    "url": f"{BASE_URL}/subtitles/the-parent-trap",
                },
            ],
        )

    def test_popular(self):
        self.parser.html = (SAMPLES / "search/popular.html").read_text()
        self.parser.parse(base_url=BASE_URL)
        self.assertEqual(self.parser.data, {"exact": None, "close": None})

    def test_empty(self):
        self.parser.html = (SAMPLES / "search/empty.html").read_text()
        self.parser.parse(base_url=BASE_URL)
        self.assertEqual(self.parser.data, {"exact": None, "close": None})

    def test_rate_limit(self):
        self.parser.html = (SAMPLES / "rate-limit.html").read_text()
        with self.assertRaises(TooManyRequestsError):
            self.parser.parse(base_url=BASE_URL)


class TestMoviePageParsing(unittest.TestCase):
    def setUp(self):
        self.parser = MoviePageParser()

    def tearDown(self):
        self.parser = None

    def test_many(self):
        self.parser.html = (SAMPLES / "movie/movie.html").read_text(encoding="utf-8")
        self.parser.parse()
        self.assertEqual(
            self.parser.data[1],
            {
                "name": "Official.Secrets.2019.REPACK.720p.10bit.BluRay.6CH.x265.HEVC-PSA",
                "rating": "neutral",
                "url": "/subtitles/official-secrets/arabic/2171760",
            },
        )
        self.assertEqual(
            self.parser.data[7],
            {
                "name": "Official.Secrets.2019.720p/1080p.BluRay.H264.AAC-RARBG",
                "rating": "positive",
                "url": "/subtitles/official-secrets/arabic/2159626",
            },
        )
        self.assertEqual(
            self.parser.data[15],
            {
                "name": "Official Secrets",
                "rating": "positive",
                "url": "/subtitles/official-secrets/arabic/2088094",
            },
        )

    def test_many_2(self):
        self.parser.html = (SAMPLES / "movie/movie-inline-ad.html").read_text(
            encoding="utf-8"
        )
        self.parser.parse()
        self.assertEqual(
            self.parser.data[4],
            {
                "name": "Parasite.2019.1080p.BluRay.x264-REGRET",
                "rating": "positive",
                "url": "/subtitles/parasite-gisaengchung/arabic/2146903",
            },
        )
        self.assertEqual(
            self.parser.data[5],
            {
                "name": "Parasite.2019.720p.BluRay.x264-REGRET",
                "rating": "positive",
                "url": "/subtitles/parasite-gisaengchung/arabic/2146903",
            },
        )

    def test_empty(self):
        self.parser.html = (SAMPLES / "movie/movie-empty.html").read_text(
            encoding="utf-8"
        )
        self.parser.parse()
        self.assertEqual(self.parser.data, [])


class TestSubtitlePageParsing(unittest.TestCase):
    def setUp(self):
        self.parser = SubtitlePageParser()

    def tearDown(self):
        self.parser = None

    def test(self):
        self.parser.html = (SAMPLES / "subtitle/subtitle.html").read_text(
            encoding="utf-8"
        )
        self.parser.parse(base_url=BASE_URL)
        self.assertEqual(
            self.parser.data,
            f"{BASE_URL}/subtitles/arabic-text/tb-75H99hPT5akNHyzyJla9ZN-r_V8IVepJ3sNZNVAHQ8vX4OvGjiskcIlADZs6DDEUzyRN5Skwpdhz4Tlggyx8Q-S3GUe_1W2aiZlH3exU81t32ZxBOntgPa2bZ9YfD0",
        )


class TestMovieFileNameMatching(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.movie_file = None

    def tearDown(self):
        try:
            self.movie_file.unlink()
            self.temp.rmdir()
        except FileNotFoundError:
            pass

    def test_valid_with_foreign_name(self):
        self.movie_file = self.temp / "Parasite (Gisaengchung 기생충) (2019).mp4"
        self.movie_file.touch()
        self.assertEqual(
            subscene.cli.type_file(str(self.movie_file)),
            {
                "path": str(self.temp),
                "title": "Parasite (Gisaengchung 기생충)",
                "year": "2019",
            },
        )

    def test_valid_with_utf8(self):
        self.movie_file = self.temp / "إشاعة حب (1961).mp4"
        self.movie_file.touch()
        self.assertEqual(
            subscene.cli.type_file(str(self.movie_file)),
            {
                "path": str(self.temp),
                "title": "إشاعة حب",
                "year": "1961",
            },
        )

    def test_invalid_missing_year(self):
        self.movie_file = self.temp / "Ne Zha.mkv"
        self.movie_file.touch()
        with self.assertRaises(argparse.ArgumentTypeError):
            subscene.cli.type_file(str(self.movie_file))

    def test_invalid_missing_title(self):
        self.movie_file = self.temp / "(1917).avi"
        self.movie_file.touch()
        with self.assertRaises(argparse.ArgumentTypeError):
            subscene.cli.type_file(str(self.movie_file))

    def test_invalid_missing_file(self):
        self.movie_file = self.temp / "ThisFileWontExists.mkv"
        with self.assertRaises(argparse.ArgumentTypeError):
            subscene.cli.type_file(str(self.movie_file))


class TestSubtitleFilteringByRating(unittest.TestCase):
    def setUp(self):
        self.parser = TitlePageParser()
        self.parser.html = (SAMPLES / "movie/movie-bad-subs.html").read_text(
            encoding="utf-8"
        )
        self.data = self.parser.parse()

    def tearDown(self):
        self.parser = None

    def test_count(self):
        self.assertEqual(len(subscene.cli.filter_by_rating(self.data["subtitles"])), 7)
        self.assertEqual(
            len(
                subscene.cli.filter_by_rating(
                    self.data["subtitles"], min_rating=Subscene.RATING.BAD
                )
            ),
            10,
        )
        self.assertEqual(
            len(
                subscene.cli.filter_by_rating(
                    self.data["subtitles"], min_rating=Subscene.RATING.POSITIVE
                )
            ),
            4,
        )

    def test_content(self):
        self.assertEqual(
            subscene.cli.filter_by_rating(self.data["subtitles"])[0],
            {
                "name": "Ip.Man.2.Legend.of.the.Grandmaster.2010.1080p.BluRay.DTS.x264-CyTSuNee",
                "rating": "positive",
                "url": "/subtitles/ip-man-2-legend-of-the-grandmaster-2-yip-man-2/danish/1130097",
            },
        )
        self.assertEqual(
            subscene.cli.filter_by_rating(self.data["subtitles"])[6],
            {
                "name": "Ip.Man.2.2010.720p.BluRay.x264.DTS-WiKi",
                "rating": "neutral",
                "url": "/subtitles/ip-man-2-legend-of-the-grandmaster-2-yip-man-2/danish/751207",
            },
        )

    def test_unknown_rating(self):
        with self.assertRaises(AttributeError):
            subscene.cli.filter_by_rating(
                self.data["subtitles"], min_rating="excellent"
            )


if __name__ == "__main__":
    unittest.main()
