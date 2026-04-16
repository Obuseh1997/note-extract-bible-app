"""Markdown formatter for YouVersion export data."""

import re
from datetime import datetime
from typing import Any, Optional

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


def _render_note_entry(item: dict[str, Any]) -> list[str]:
    """Render a single note entry to markdown lines."""
    lines = []
    ref = item["reference"]
    translation = item.get("version", "")
    note_text = item.get("note", "")
    date = item.get("date", "")

    header = f"### {ref}"
    if translation:
        header += f" ({translation})"
    if date:
        header += f"  <sub>{date}</sub>"
    lines.append(header)
    lines.append("")

    if note_text:
        lines.append(f"**My note:** {note_text}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines


def _render_highlight_entry(item: dict[str, Any]) -> list[str]:
    """Render a single highlight entry to markdown lines."""
    lines = []
    ref = item["reference"]
    translation = item.get("version", "")
    color_emoji = item.get("color_emoji", "")
    note_text = item.get("note", "")
    date = item.get("date", "")

    header = f"### {ref}"
    if translation:
        header += f" ({translation})"
    if color_emoji:
        header += f" {color_emoji}"
    if date:
        header += f"  <sub>{date}</sub>"
    lines.append(header)
    lines.append("")

    if note_text:
        lines.append(f"**My note:** {note_text}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines


def format_markdown(
    data: dict[str, list[dict[str, Any]]],
    group_by_book: bool = True,
    include_toc: bool = True,
    include_related: bool = False,
    top_k: int = 5,
) -> str:
    """Convert extracted notes and highlights to a markdown string.

    Args:
        data: Dict with 'notes' and 'highlights' from extract_all()
        group_by_book: If True, group entries by Bible book (canonical order).
                       If False, output as a flat chronological list.
        include_toc: If True, prepend a table of contents.

    Returns:
        Formatted markdown string.
    """
    lines = []
    today = datetime.now().strftime("%Y-%m-%d")

    lines.append("# My YouVersion Notes & Highlights")
    lines.append(f"Exported: {today}")
    lines.append("")

    notes = data.get("notes", [])
    highlights = data.get("highlights", [])

    lines.append(f"**{len(notes)} notes** | **{len(highlights)} highlights**")
    lines.append("")

    if not group_by_book:
        return _format_flat(lines, notes, highlights)

    # Group by book
    notes_by_book: dict[str, list[dict[str, Any]]] = {}
    highlights_by_book: dict[str, list[dict[str, Any]]] = {}

    for n in notes:
        book = extract_book_name(n["reference"])
        notes_by_book.setdefault(book, []).append(n)

    for h in highlights:
        book = extract_book_name(h["reference"])
        highlights_by_book.setdefault(book, []).append(h)

    # TOC
    if include_toc and (notes_by_book or highlights_by_book):
        lines.append("## Table of Contents")
        lines.append("")

        if notes_by_book:
            lines.append("**Notes**")
            for book in sorted(notes_by_book.keys(), key=book_sort_key):
                count = len(notes_by_book[book])
                anchor = slugify(f"notes-{book}")
                lines.append(f"- [{book}](#{anchor}) ({count})")
            lines.append("")

        if highlights_by_book:
            lines.append("**Highlights**")
            for book in sorted(highlights_by_book.keys(), key=book_sort_key):
                count = len(highlights_by_book[book])
                anchor = slugify(f"highlights-{book}")
                lines.append(f"- [{book}](#{anchor}) ({count})")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Notes section
    if notes_by_book:
        lines.append("## Notes")
        lines.append("")

        for book in sorted(notes_by_book.keys(), key=book_sort_key):
            lines.append(f"### {book}")
            lines.append("")
            for item in notes_by_book[book]:
                lines.extend(_render_item_under_book(
                    item, kind="note",
                    include_related=include_related, top_k=top_k,
                ))

    # Highlights section
    if highlights_by_book:
        lines.append("## Highlights")
        lines.append("")

        for book in sorted(highlights_by_book.keys(), key=book_sort_key):
            lines.append(f"### {book}")
            lines.append("")
            for item in highlights_by_book[book]:
                lines.extend(_render_item_under_book(
                    item, kind="highlight",
                    include_related=False,
                ))

    return "\n".join(lines)


def _render_item_under_book(
    item: dict[str, Any],
    kind: str,
    include_related: bool = False,
    top_k: int = 5,
) -> list[str]:
    """Render an item nested under a book heading (uses #### for ref)."""
    lines = []
    ref = item["reference"]
    translation = item.get("version", "")
    note_text = item.get("note", "")
    date = item.get("date", "")

    header = f"#### {ref}"
    if translation:
        header += f" ({translation})"
    if kind == "highlight" and item.get("color_emoji"):
        header += f" {item['color_emoji']}"
    if date:
        header += f"  <sub>{date}</sub>"
    lines.append(header)
    lines.append("")

    # Noted verse text (KJV) — pulled from the Bible index
    try:
        from scripture_search import get_verse_text
        verse_text = get_verse_text(ref)
        if verse_text:
            lines.append(f"> *{verse_text}*")
            lines.append("")
    except Exception:
        pass  # Index not available — skip silently

    if note_text:
        lines.append(f"**My note:** {note_text}")
        lines.append("")

    # Related scriptures (notes only, not highlights)
    if include_related and kind == "note" and note_text:
        try:
            from scripture_search import find_related
            related = find_related(note_text, top_k=top_k, exclude_ref=ref)
            if related:
                lines.append("🔗 **Related scriptures**")
                lines.append("")
                for r in related:
                    lines.append(f"- **{r['reference']}** — *{r['snippet']}*")
                lines.append("")
        except Exception:
            pass  # Index not available — skip silently

    return lines


def _format_flat(
    lines: list[str],
    notes: list[dict[str, Any]],
    highlights: list[dict[str, Any]],
) -> str:
    """Original flat-list layout — kept as an opt-out of book grouping."""
    if notes:
        lines.append("---")
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for item in notes:
            lines.extend(_render_note_entry(item))

    if highlights:
        if not notes:
            lines.append("---")
            lines.append("")
        lines.append("## Highlights")
        lines.append("")
        for item in highlights:
            lines.extend(_render_highlight_entry(item))

    return "\n".join(lines)
