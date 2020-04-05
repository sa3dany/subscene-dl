import re
import argparse
from subscene.api import Subscene

SOURCES = {
    "bluray": dict(tags=["bluray", "brrip", "bdrip"]),
    "web": dict(tags=["webrip", "web-dl"]),
}


def movie_title(string) -> dict:
    """Represents the expected format for a movie title: "Title (Year)"

    >>> movie_title("Parasite (Gisaengchung / 기생충) (2019)")
    {'title': 'Parasite (Gisaengchung / 기생충)', 'year': '2019'}

    >>> movie_title("Ne Zha")
    Traceback (most recent call last):
    argparse.ArgumentTypeError: ...
    """

    movie_format = re.compile(r"(.+)\s+\(([12][0-9]{3})\)")
    match = movie_format.match(string)
    if not match:
        raise argparse.ArgumentTypeError(
            'Invalid movie format.\nAccepted format is "Title (Year)"'
        )
    return {"title": match.group(1), "year": match.group(2)}


def subtitle_language(language_code):
    """Converts a language code like "en", "ar" to the internal numeric ID
    used by subscene

    >>> subtitle_language("en")
    {'description': 'English', 'subscene_id': '13'}

    >>> subtitle_language("sq")
    Traceback (most recent call last):
    argparse.ArgumentTypeError: ...
    """

    if language_code not in Subscene.LANGUAGES:
        raise argparse.ArgumentTypeError(
            "The language specified is either not supported by"
            + " subscene or not implemented"
        )
    return Subscene.LANGUAGES[language_code]


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


def download(title, year, language, source=None):
    # TODO: Skip 4k, REPACKS, etc
    sc = Subscene()

    title_info = sc.searchbytitle(title, year)
    if not title_info:
        return

    language_id = language["subscene_id"]
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
    subtitle_filename = f"{title} ({year}).{language['code']}.srt"
    with open(subtitle_filename, "w+", encoding="utf-8") as subfile:
        subfile.write(subtitle_text)


def main(argv=None):
    """Entry point for the cli interface"""

    parser = argparse.ArgumentParser(
        prog="subscene-dl", description="Downloads movie subtitles from subscene"
    )
    parser.add_argument("-s", "--source", help="Release source", choices=SOURCES)
    parser.add_argument("movie", help="Movie title", type=movie_title)
    parser.add_argument(
        "language", help="Subtitle language code", type=subtitle_language
    )
    args = parser.parse_args()
    download(
        title=args.movie["title"],
        year=args.movie["year"],
        language=args.language,
        source=args.source,
    )


if __name__ == "__main__":
    main()
