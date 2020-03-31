import os
import unittest

from subscene import parser

TEST_DIR = os.path.dirname(__file__)

class TestMovieSearchResultsParsing(unittest.TestCase):
    def setUp(self):
        self.parser = parser.MovieSearchResultsParser()

    def tearDown(self):
        self.parser.close()

    def test_only_exact(self):
        filename = os.path.join(TEST_DIR, "samples", "movie-search-results.html")
        with open(filename, "r") as file:
            self.parser.feed(file.read())
        self.assertEqual(
            self.parser.movie_url, f"/subtitles/official-secrets"
        )


if __name__ == "__main__":
    unittest.main()
