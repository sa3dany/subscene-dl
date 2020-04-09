import re
import argparse
from pathlib import Path
from iso639 import languages
from subscene.api import Subscene
from typing import List, Dict, Optional


def keyof(object, value):
    """Returns key in dict that has the given value

    Returns `None` if there is no such value in dict.
    """

    keys = list(object.keys())
    values = list(object.values())
    try:
        return keys[values.index(value)]
    except ValueError:
        return None


def type_language(code):
    """Converts a language codes to subscene language ID

    Converts a language code like "ar", "fr" or "pt-br" to the internal
    numeric ID used by subscene. You can also directly pass the subscene
    ID.

    >>> type_language("mni")
    {'id': 65, 'code': 'mni'}

    >>> type_language("pt-br")
    {'id': 4, 'code': 'pt'}

    >>> type_language("tu")
    Traceback (most recent call last):
    argparse.ArgumentTypeError: ...

    >>> type_language("50")
    {'id': 50, 'code': 'ms'}
    """

    if code == "pt-br":
        # Special case. See comment in api.py
        return {"id": Subscene.LANGUAGES[code], "code": "pt"}

    # Allow passing subscene numeric language IDs directly
    try:
        language_id = int(code)
        language_code = keyof(Subscene.LANGUAGES, language_id)
        if language_code:
            return {"id": language_id, "code": language_code}
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
    if available_code not in Subscene.LANGUAGES:
        raise argparse.ArgumentTypeError(
            "The language code specified is not supported by subscene.com"
        )

    return {"id": Subscene.LANGUAGES[available_code], "code": code}


def type_file(string) -> dict:
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


def type_tags(string) -> List[str]:
    """Extracts usefull metadata about a movie release from a string of common tags

    This can be a custom list of case-insensitive tags using any
    separator or the original release file name.

    Based on: https://github.com/matiassingers/scene-release

    >>> type_tags("720p.HDTV")
    ['720p', 'HDTV']

    >>> type_tags("2160p 4k EXTENDED BLURAY")
    ['2160p', 'EXTENDED', 'BLURAY']

    >>> type_tags("Extended.Cut.DVDRip")
    ['Extended.Cut', 'DVDRip']

    >>> type_tags("720p WEB-DL")
    ['720p', 'WEB-DL']

    >>> type_tags("3D.BLURAY")
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
            if tag not in subtitle["name"]:
                break
        else:
            matching_subtitles.append(subtitle)

    return matching_subtitles


def download(title, year, language, output_dir, tags=[]):
    """Downloads movie subtitles from subscene"""

    sc = Subscene()

    search_result = sc.searchbytitle(title, year)
    if not search_result:
        return

    subtitles = sc.subtitles(search_result["id"], language["id"], hi=Subscene.HINONE)
    if not len(subtitles):
        return

    subtitles = filter_by_tags(subtitles, tags)
    if not len(subtitles):
        return

    print(subtitles[0]["name"])
    subtitle_bytes = sc.download(subtitles[0]["url"])
    subtitle_filename = Path(f"{output_dir}/{title} ({year}).{language['code']}.srt")
    with open(subtitle_filename, "wb+") as subfile:
        # Using binary mode since text mode caused some weird
        # line-ending conversion for some subtitle files and caused
        # extra empty lines
        subfile.write(subtitle_bytes.encode("utf-8"))


def main(argv=None):
    """CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Downloads movie subtitles from subscene"
    )

    parser.add_argument(
        "language",
        help="ISO-639-1 (2-letter) or ISO-639-2/B (3-letter) language code",
        type=type_language,
    )
    parser.add_argument(
        "file",
        help="File name must be in the form 'MOVIE_NAME (RELEASE_DATE)'",
        type=type_file,
    )
    parser.add_argument(
        "-t",
        "--tags",
        help="Filter subtitles by release tags like type and resolution",
        type=type_tags,
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
    main()
