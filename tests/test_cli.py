import doctest
import unittest
import tempfile
import argparse
from pathlib import Path

from subscene import api, cli
from subscene.htmlparse import TitlePageParser

SAMPLES = Path(__file__).parent / "samples"


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(cli, optionflags=doctest.ELLIPSIS))
    return tests


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
            cli.arg_file(str(self.movie_file)),
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
            cli.arg_file(str(self.movie_file)),
            {"path": str(self.temp), "title": "إشاعة حب", "year": "1961",},
        )

    def test_invalid_missing_year(self):
        self.movie_file = self.temp / "Ne Zha.mkv"
        self.movie_file.touch()
        with self.assertRaises(argparse.ArgumentTypeError):
            cli.arg_file(str(self.movie_file))

    def test_invalid_missing_title(self):
        self.movie_file = self.temp / "(1917).avi"
        self.movie_file.touch()
        with self.assertRaises(argparse.ArgumentTypeError):
            cli.arg_file(str(self.movie_file))

    def test_invalid_missing_file(self):
        self.movie_file = self.temp / "ThisFileWontExists.mkv"
        with self.assertRaises(argparse.ArgumentTypeError):
            cli.arg_file(str(self.movie_file))


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
        self.assertEqual(len(cli.filter_by_rating(self.data)), 7)
        self.assertEqual(
            len(cli.filter_by_rating(self.data, min_rating=api.RATING.BAD)),
            10,
        )
        self.assertEqual(
            len(
                cli.filter_by_rating(self.data, min_rating=api.RATING.POSITIVE)
            ),
            4,
        )

    def test_content(self):
        self.assertEqual(
            cli.filter_by_rating(self.data)[0],
            {
                "name": "Ip.Man.2.Legend.of.the.Grandmaster.2010.1080p.BluRay.DTS.x264-CyTSuNee",
                "rating": "positive",
                "url": "/subtitles/ip-man-2-legend-of-the-grandmaster-2-yip-man-2/danish/1130097",
            },
        )
        self.assertEqual(
            cli.filter_by_rating(self.data)[6],
            {
                "name": "Ip.Man.2.2010.720p.BluRay.x264.DTS-WiKi",
                "rating": "neutral",
                "url": "/subtitles/ip-man-2-legend-of-the-grandmaster-2-yip-man-2/danish/751207",
            },
        )

    def test_unknown_rating(self):
        with self.assertRaises(AttributeError):
            cli.filter_by_rating(self.data, min_rating="excellent")


if __name__ == "__main__":
    unittest.main()
