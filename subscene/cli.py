import re
import argparse
from pathlib import Path
from iso639 import languages
from subscene.api import Subscene

SOURCES = {
    "bluray": dict(tags=["bluray", "brrip", "bdrip"]),
    "web": dict(tags=["webrip", "web-dl"]),
}


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

    Converts a language code like "ar", "fr" or "pt-br" to the internal numeric ID
    used by subscene. You can also directly pass the subscene ID.

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


def source_filter_gen(source):
    """Generates a labda function that can be used to filter subtitles
    based on a realease source (e.g. "BluRay" or "WEB-DL") tags that are
    in a subtitle's name.

    >>> source_filter_gen(SOURCES["bluray"])("Example.Release.2020.BDRip")
    True

    >>> source_filter_gen(SOURCES["web"])("Another.Example.1999.BDRip")
    False
    """
    pattern = re.compile("|".join(source["tags"]), flags=re.IGNORECASE)
    return lambda sub: pattern.search(sub) != None


def download(title, year, language, output_dir, source=None):
    # TODO: Skip 4k, REPACKS, etc
    sc = Subscene()

    title_info = sc.searchbytitle(title, year)
    if not title_info:
        return

    language_id = language["id"]
    subtitles = sc.subtitles(title_info["id"], language_id, hi_flag=Subscene.HINONE)
    if not len(subtitles):
        return

    if source:
        source_filter = source_filter_gen(SOURCES[source])
        subtitles = [
            sub
            for sub in subtitles
            if sub["rating"] == "positive" and source_filter(sub["name"])
        ]
    if not len(subtitles):
        return

    print(subtitles[0]["name"])
    subtitle_text = sc.download(subtitles[0]["url"])
    subtitle_filename = Path(output_dir) / f"{title} ({year}).{language['code']}.srt"
    with open(subtitle_filename, "w+", encoding="utf-8") as subfile:
        subfile.write(subtitle_text)


def main(argv=None):
    """Entry point for the cli interface"""

    parser = argparse.ArgumentParser(
        prog="subscene-dl", description="Downloads movie subtitles from subscene"
    )
    parser.add_argument("-s", "--source", help="Release source", choices=SOURCES)
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
    args = parser.parse_args()
    download(
        output_dir=args.file["path"],
        title=args.file["title"],
        year=args.file["year"],
        language=args.language,
        source=args.source,
    )


if __name__ == "__main__":
    main()
