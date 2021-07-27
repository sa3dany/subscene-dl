import re
import sys
import argparse
from pathlib import Path
from iso639 import languages
from jellyfish import jaro_winkler
from colorama import Fore, Back, Style
from typing import List, Dict, Optional
from colorama import init as termcolor_init

from subscene import api
from subscene import utils


def out(message, color=None, lf=True):
    if color:
        sys.stdout.write(color)
    sys.stdout.write(f"{message}{Style.RESET_ALL}")
    if lf:
        sys.stdout.write("\n")


def error(message, exit_code=1):
    sys.stdout.write(f"{Fore.RED}{message}\n")
    exit(exit_code)


def arg_language(code):
    """Converts a language code to subscene language ID

    Converts a language code like "ar", "fr" or "pt-br" to the internal
    numeric ID used by subscene. You can also directly pass the subscene
    ID.

    >>> arg_language("mni")
    {'id': 65, 'code': 'mni'}

    >>> arg_language("pt-br")
    {'id': 4, 'code': 'pt'}

    >>> arg_language("tu")
    Traceback (most recent call last):
    argparse.ArgumentTypeError: ...

    >>> arg_language("50")
    {'id': 50, 'code': 'ms'}
    """

    if code == "pt-br":
        # Special case. See comment in api.py
        return {"id": api.LANGUAGES["PT_BR"].value, "code": "pt"}

    # Allow passing subscene numeric language IDs directly
    try:
        language_id = int(code)
        language = api.LANGUAGES(language_id)
        if language:
            return {"id": language_id, "code": language.name.lower()}
        raise argparse.ArgumentTypeError(
            "The language ID specified is not a valid subscene language ID"
        )
    except ValueError:
        # A ValueError is raised if the code cannot be parsed to an int
        pass

    try:
        if len(code) == 2:
            language = languages.get(part1=code)
        else:
            language = languages.get(part2b=code)
    except KeyError:
        raise argparse.ArgumentTypeError(
            "The language code specified is not a valid ISO-639-1 or ISO-639-2/B code"
        )

    available_code = language.part1 or language.part2b
    if not api.LANGUAGES[available_code.upper()]:
        raise argparse.ArgumentTypeError(
            "The language code specified is not supported by subscene.com"
        )

    return {"id": api.LANGUAGES[available_code.upper()].value, "code": available_code}


def arg_file(string) -> dict:
    """Represents the expected format for a movie file name: 'Title (Year).ext'"""

    file_path = Path(string)
    if not file_path.exists():
        raise argparse.ArgumentTypeError("File does not exist")

    movie_format = re.compile(r"(.+)\s+\(([12][0-9]{3})\)")
    match = movie_format.match(file_path.stem)
    if not match:
        raise argparse.ArgumentTypeError(
            'Invalid movie format. Accepted format is "Title (Year)"'
        )

    return {
        "path": str(file_path.parent),
        "title": match.group(1),
        "year": match.group(2),
    }


def arg_tags(string) -> List[str]:
    """Extracts usefull metadata about a movie release from a string of common tags

    This can be a custom list of case-insensitive tags using any
    separator or the original release file name.

    Based on: https://github.com/matiassingers/scene-release

    >>> arg_tags("720p.HDTV")
    ['720p', 'HDTV']

    >>> arg_tags("2160p 4k EXTENDED BLURAY")
    ['2160p', 'EXTENDED', 'BLURAY']

    >>> arg_tags("Extended.Cut.DVDRip")
    ['Extended.Cut', 'DVDRip']

    >>> arg_tags("720p WEB-DL")
    ['720p', 'WEB-DL']

    >>> arg_tags("3D.BLURAY")
    ['3D', 'BLURAY']
    """

    tags = []
    patterns = {
        "resolution": re.compile(r"[1-9][0-9]{2,3}p|4k", re.IGNORECASE),
        "edition": re.compile(
            r"UNRATED|DC|(Directors|EXTENDED)[.\s](CUT|EDITION)|EXTENDED|3D|2D|\bNF\b",
            re.IGNORECASE,
        ),
        "type": re.compile(
            r"CAM|TS(?!C)|TELESYNC|(DVD|BD)SCR|SCR|DDC|R5[.\s]LINE|R5"
            + r"|(DVD|HD|BR|BD|WEB)Rip|DVDR|(HD|PD)TV|WEB-DL|WEBDL|BluRay",
            re.IGNORECASE,
        ),
    }
    for tag, pattern in patterns.items():
        match = pattern.search(string)
        if match:
            tags.append(match.group(0))
    return tags


def decode(blob: bytes, language_code) -> str:
    """Gues encoding of subtitle

    Based on work of Hannes Tismer
    see: https://github.com/pannal/Sub-Zero.bundle
    """
    # Here we are using "utf-8-sig" since it correcly
    # handles both BOM and non-BOM utf-8 files.
    encodings = ["utf-8-sig"]

    if language_code == "ar":
        # fallback to window-1256 encoding since many of the
        # Arabic subtitles use that encoding ¯\_(ツ)_/¯
        encodings.extend(["windows-1256", "utf-16"])

    for encoding in encodings:
        try:
            decoded = blob.decode(encoding)
        except UnicodeDecodeError:
            print(f'failed to decode as {language_code}')
            pass
        else:
            return decoded

    raise ValueError("Could not decode subtitle")


def filter_by_rating(
    subtitles: List[Dict], min_rating: api.RATING = api.RATING.NEUTRAL
) -> List[Dict]:
    """Filters subtitles by the subscene user ratings

    Subscene currently has three ratings: "Positive", "Neutral" and "Bad"
    which are represented by the API as:
        `Subscene.RATING.POSITIVE`,
        `Subscene.RATING.NEUTRAL` and
        `Subscene.RATING.BAD`
    """

    rating_scale = [
        api.RATING.BAD.value,
        api.RATING.NEUTRAL.value,
        api.RATING.POSITIVE.value,
    ]

    min_rating_value = rating_scale.index(min_rating.value)
    matching_subtitles = []
    for subtitle in subtitles:
        subtitle_rating = rating_scale.index(subtitle["rating"])
        if subtitle_rating >= min_rating_value:
            matching_subtitles.append(subtitle)

    return matching_subtitles


def filter_by_tags(subtitles: List[Dict], tags: List[str]) -> List[Dict]:
    """Filters a list of subtitles using a list of tags

    Each subtitle name must match **all** the tags.

    >>> filter_by_tags([{"name": "y"}], [])
    [{'name': 'y'}]

    >>> filter_by_tags([{"name": "a.b.c"}, {"name": "a.c"}], ['a', 'b'])
    [{'name': 'a.b.c'}]
    """

    if not len(tags):
        return subtitles

    matching_subtitles = []
    for subtitle in subtitles:
        for tag in tags:
            if tag.lower() not in subtitle["name"].lower():
                break
        else:
            matching_subtitles.append(subtitle)

    return matching_subtitles


def match_title(title, year, results):
    """Find the best matching title from subscene search results"""
    # TODO: When comparing years: 1 year +/- is okay as long as there is
    # no other close matches
    results = results["results"]
    if results["exact"]:
        # If a single exact match, just return that
        if len(results["exact"]) == 1:
            return results["exact"][0]
        # Else, look for the exact match with same year as our title
        for match in results["exact"]:
            if match["year"] == year:
                return match
    # If only close matches, return the closest with the same year
    if results["close"]:
        best_score = 0
        best_match = None
        same_year_matches = [
            match for match in results["close"] if match["year"] == year
        ]
        for match in same_year_matches:
            score = jaro_winkler(match["title"], title)
            if score > best_score:
                best_score = score
                best_match = match
        return best_match
    return None


def download(title, year, language, output_dir, tags=[]):
    """Downloads movie subtitles from subscene"""

    sc = api.Subscene()

    search_results = sc.search_titles(title)
    search_match = match_title(title, year, search_results)
    if not search_match:
        error("Title not found", 1)
    out(f'{search_match["title"]} {search_match["year"]}', Fore.YELLOW)

    subtitles = sc.get_title(search_match["url"], language["id"], hi=api.HI.HINONE)
    subtitles = subtitles["subtitles"]
    if not len(subtitles):
        error("No subtitles", 1)

    subtitles = filter_by_tags(subtitles, tags)
    if not len(subtitles):
        error("No subtitles matched tags", 1)

    subtitles = filter_by_rating(subtitles)
    if not len(subtitles):
        error("No matching subtitles with 'neutral' or better rating", 1)

    subtitle_pack = sc.get_subtitle(subtitles[0]["url"])
    if len(subtitle_pack["files"]) > 1:
        out(f'{"Subtitle:": <10}{subtitles[0]["name"]}')
        raise NotImplementedError("Subtitle packs are currently not supported")

    output_filename = Path(f"{output_dir}/{title} ({year}).{language['code']}.srt")
    with open(output_filename, "wb+") as file:
        # Using binary mode since text mode caused some weird
        # line-ending conversion for some subtitle files and caused
        # extra empty lines

        subtitle_file = subtitle_pack["files"][0]["body"]
        subtitle_bytes = subtitle_file.read()
        subtitle_file.close()

        subtitle_text = decode(subtitle_bytes, language['code'])

        file.write(subtitle_text.encode("utf-8"))

    out(f'{"Subtitle:": <10}{subtitles[0]["name"]}')


def main(argv=None):
    """CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Downloads movie subtitles from subscene"
    )

    parser.add_argument(
        "language",
        help="ISO-639-1 (2-letter) or ISO-639-2/B (3-letter) language code",
        type=arg_language,
    )
    parser.add_argument(
        "file",
        help="File name must be in the form 'MOVIE_NAME (RELEASE_DATE)'",
        type=arg_file,
    )
    parser.add_argument(
        "-t",
        "--tags",
        help="Filter subtitles by release tags like type and resolution",
        type=arg_tags,
        default=[],
    )

    args = parser.parse_args()

    download(
        output_dir=args.file["path"],
        title=args.file["title"],
        year=args.file["year"],
        language=args.language,
        tags=args.tags,
    )


if __name__ == "__main__":
    termcolor_init()
    main()
