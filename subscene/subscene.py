import argparse
import requests
import re
import time

from html.parser import HTMLParser
from utils import *

# Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument("movie", help="Movie name + year")
parser.add_argument("-l", "--language", help="Subtitle language", default="ar")
parser.add_argument("-t", "--type", help="Release type", choices=["br", "web"])
args = parser.parse_args()

# Prepare arguments
movie_parser = re.compile("([^()]+)\s+\(([0-9]{4})\)")
movie_match = movie_parser.match(args.movie)
if not movie_match:
    raise ValueError("Invalid Movie Title")
movie_title = movie_match.group(1)
movie_year = movie_match.group(2)
# print(f'Movie: {movie_title}, Year: {movie_year}')

# set search filters
search_filter = {}
search_filter["ForeignOnly"] = "False"
search_filter["HearingImpaired"] = "0"
search_filter["LanguageFilter"] = get_language_id(args.language)
# print(f'Language filter: {search_filter["LanguageFilter"]}')

# create a requests session
session = requests.Session()
session.cookies = requests.cookies.cookiejar_from_dict(search_filter)

# get movie page url
movie_search_url = "https://subscene.com/subtitles/searchbytitle"
# r = session.post(movie_search_url, data={"query": movie_title, "l": ""})
parser = SearchResultsParser("https://subscene.com")
with open("movie-results.html", "r") as file:
    parser.feed(file.read())
    parser.close()
movie_url = parser.get_movie_url()
if not movie_url:
    print("Didn't match any movie")
    exit(0)

time.sleep(1)

# get first good subtitle match
# r = session.get(movie_url, headers={"Referer": movie_search_url})
# with open("subtitle-results.html", "wb") as file:
#     file.write(r.content)
parser = MoviePageParser("https://subscene.com", subtitle_type=args.type)
with open("subtitle-results.html", "r", encoding="utf-8") as file:
    parser.feed(file.read())
    parser.close()
subtitle_url = parser.get_subtitle_url()
if not subtitle_url:
    print("Didn't find matching subtitle")
    exit(0)
print(f'Subtitle: {subtitle_url}')

time.sleep(1)

# get subtitle download url
# r = session.get(subtitle_url, headers={"Referer": movie_url})
# with open("subtitle.html", "wb") as file:
#     file.write(r.content)
parser = SubtitlePageParser("https://subscene.com")
with open("subtitle.html", "r", encoding="utf-8") as file:
    parser.feed(file.read())
    parser.close()
download_url = parser.get_download_url()
print(f'url: {download_url}')

time.sleep(1)

# download subtitle
# r = session.get(download_url)
# with open("subtitle.zip", "wb") as file:
#     file.write(r.content)
with open("subtitle.zip", "rb") as zipfile:
    subtitle_text = extract_subtitle(zipfile.read())

# write subtitle
with open(f'{args.movie}.srt', "w+", encoding="utf-8") as subfile:
    subfile.write(subtitle_text)

# Done
