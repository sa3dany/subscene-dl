import unittest
from pathlib import Path
from subscene import parser, BASE_URL

SAMPLES = Path(__file__).parent / "samples"


class TestMovieSearchResultsParsing(unittest.TestCase):
    def setUp(self):
        self.parser = parser.MovieSearchResultsParser()

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
        with self.assertRaises(parser.TooManyRequestsError):
            self.parser.parse(base_url=BASE_URL)


class TestMoviePageParsing(unittest.TestCase):
    def setUp(self):
        self.parser = parser.MoviePageParser()

    def tearDown(self):
        self.parser = None

    def test(self):
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


class TestSubtitlePageParsing(unittest.TestCase):
    def setUp(self):
        self.parser = parser.SubtitlePageParser()

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


if __name__ == "__main__":
    unittest.main()
