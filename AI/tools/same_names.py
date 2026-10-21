"""Find files that share a name ("Payment_Schedule.pdf" and "old/Payment_Schedule.pdf", or an upload copy
"Payment_Schedule (2).pdf"). They are often two versions of one document, and their facts can disagree."""

import re
from collections import defaultdict
from pathlib import PurePosixPath

COPY_MARK = re.compile(r"(\s*\(\d+\)|\s*-?\s*copy(\s*\d+)?)$", re.IGNORECASE)  # "x (2)", "x - Copy", "x copy 3"


def base_name(name: str) -> str:
    """'old/Payment_Schedule (2).PDF' -> 'payment_schedule.pdf'"""
    path = PurePosixPath(name)
    return f"{COPY_MARK.sub('', path.stem).strip()}{path.suffix}".lower()


def same_name_groups(names: list[str]) -> list[list[str]]:
    """Groups of two or more file names that are the same file name, in the order given."""
    groups: dict[str, list[str]] = defaultdict(list)
    for name in names:
        groups[base_name(name)].append(name)
    return [group for group in groups.values() if len(group) > 1]


def same_name_note(names: list[str]) -> str:
    """One line for the system prompt, or "" when every name is different."""
    groups = same_name_groups(names)
    if not groups:
        return ""
    listed = "; ".join(" and ".join(f"'{name}'" for name in group) for group in groups)
    return (
        f"Files with the same name (maybe different versions): {listed}. Say which file each fact comes from, "
        "and point out where they disagree."
    )
