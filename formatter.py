"""Markdown formatter for YouVersion export data."""

import re
from datetime import datetime
from typing import Any

# Canonical book order (66 books) for sorting
BOOK_ORDER = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Psalm", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Song of Songs", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea",
    "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum",
    "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy",
    "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
]


def extract_book_name(reference: str) -> str:
    """Pull the book name off a reference like '1 Samuel 16:14'."""
    match = re.match(r"^((?:\d\s+)?[A-Za-z]+(?:\s+of\s+\w+)?)\s+\d", reference)
    if match:
        return match.group(1).strip()
    parts = reference.rsplit(" ", 1)
    return parts[0] if len(parts) > 1 else reference


def book_sort_key(book: str) -> tuple[int, str]:
    """Sort key: canonical order first, unknown books alphabetically at the end."""
    try:
        return (BOOK_ORDER.index(book), book)
    except ValueError:
        return (len(BOOK_ORDER), book)


def slugify(text: str) -> str:
    """Convert text to a markdown anchor slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug


def format_markdown(
    data: dict[str, list[dict[str, Any]]],
    group_by_book: bool = True,
    include_toc: bool = True,
    include_related: bool = False,
    top_k: int = 5,
) -> str:
    """Convert extracted notes to a markdown string.

    Args:
        data: Dict with 'notes' list from extract_all()
        group_by_book: Group by Bible book in canonical order (default True).
        include_toc: Prepend a clickable table of contents (default True).
        include_related: Surface related scriptures under each note (default False).
        top_k: Number of related scriptures per note.

    Returns:
        Formatted markdown string.
    """
    lines = []
    today = datetime.now().strftime("%Y-%m-%d")

    lines.append("# My YouVersion Notes")
    lines.append(f"Exported: {today}")
    lines.append("")

    notes = data.get("notes", [])
    lines.append(f"**{len(notes)} notes**")
    lines.append("")

    if not group_by_book:
        return _format_flat(lines, notes, include_related, top_k)

    # Group notes by book
    notes_by_book: dict[str, list[dict[str, Any]]] = {}
    for n in notes:
        book = extract_book_name(n["reference"])
        notes_by_book.setdefault(book, []).append(n)

    # TOC
    if include_toc and notes_by_book:
        lines.append("## Table of Contents")
        lines.append("")
        for book in sorted(notes_by_book.keys(), key=book_sort_key):
            count = len(notes_by_book[book])
            anchor = slugify(f"notes-{book}")
            lines.append(f"- [{book}](#{anchor}) ({count})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Notes grouped by book
    for book in sorted(notes_by_book.keys(), key=book_sort_key):
        lines.append(f"### {book}")
        lines.append("")
        for item in notes_by_book[book]:
            lines.extend(_render_note(item, include_related=include_related, top_k=top_k))

    return "\n".join(lines)


def _render_note(
    item: dict[str, Any],
    include_related: bool = False,
    top_k: int = 5,
) -> list[str]:
    """Render a single note entry."""
    lines = []
    ref = item["reference"]
    translation = item.get("version", "")
    note_text = item.get("note", "")
    date = item.get("date", "")

    header = f"#### {ref}"
    if translation:
        header += f" ({translation})"
    if date:
        header += f"  <sub>{date}</sub>"
    lines.append(header)
    lines.append("")

    # KJV verse text from local index
    try:
        from scripture_search import get_verse_text
        verse_text = get_verse_text(ref)
        if verse_text:
            lines.append(f"> *{verse_text}*")
            lines.append("")
    except Exception:
        pass

    if note_text:
        lines.append(f"**My note:** {note_text}")
        lines.append("")

    # Related scriptures
    if include_related and note_text:
        try:
            from scripture_search import find_related
            related = find_related(verse_text or note_text, top_k=top_k, exclude_ref=ref)
            if related:
                lines.append("🔗 **Related scriptures**")
                lines.append("")
                for r in related:
                    lines.append(f"- **{r['reference']}** — *{r['snippet']}*")
                lines.append("")
        except Exception:
            pass

    return lines


def _format_flat(
    lines: list[str],
    notes: list[dict[str, Any]],
    include_related: bool,
    top_k: int,
) -> str:
    """Flat chronological list layout."""
    lines.append("---")
    lines.append("")
    for item in notes:
        lines.extend(_render_note(item, include_related=include_related, top_k=top_k))
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
