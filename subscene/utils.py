import re
from typing import Tuple
from collections import namedtuple


def parsetitle(title: str) -> Tuple[str, str]:
    """Converts string title to named tuple(title, year)"""
    Title = namedtuple("Title", ["title", "year"])
    match = re.match(r"(.+)\s+\(([12][0-9]{3})\)$", title, flags=re.IGNORECASE)
    return Title(title=match.group(1), year=match.group(2))
