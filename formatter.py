"""Markdown formatter for YouVersion export data."""

from datetime import datetime
from typing import Any


def format_markdown(data: dict[str, list[dict[str, Any]]]) -> str:
    """Convert extracted notes and highlights to a markdown string.

    Args:
        data: Dict with 'notes' and 'highlights' lists from extractor.extract_all()

    Returns:
        Formatted markdown string
    """
    lines = []
    today = datetime.now().strftime("%Y-%m-%d")

    lines.append(f"# My YouVersion Notes & Highlights")
    lines.append(f"Exported: {today}")
    lines.append("")

    notes = data.get("notes", [])
    highlights = data.get("highlights", [])

    lines.append(f"**{len(notes)} notes** | **{len(highlights)} highlights**")
    lines.append("")

    # --- Notes ---
    if notes:
        lines.append("---")
        lines.append("")
        lines.append("## Notes")
        lines.append("")

        for item in notes:
            ref = item["reference"]
            verse_text = item.get("verse_text", "")
            note_text = item.get("note", "")
            date = item.get("date", "")

            translation = item.get("version", "")
            ref_line = f"### {ref}"
            if translation:
                ref_line += f" ({translation})"
            if date:
                ref_line += f"  <sub>{date}</sub>"
            lines.append(ref_line)
            lines.append("")

            if note_text:
                lines.append(f"**My note:** {note_text}")
                lines.append("")

            lines.append("---")
            lines.append("")

    # --- Highlights ---
    if highlights:
        if not notes:
            lines.append("---")
            lines.append("")
        lines.append("## Highlights")
        lines.append("")

        for item in highlights:
            ref = item["reference"]
            verse_text = item.get("verse_text", "")
            color_emoji = item.get("color_emoji", "")
            note_text = item.get("note", "")
            date = item.get("date", "")

            translation = item.get("version", "")
            ref_line = f"### {ref}"
            if translation:
                ref_line += f" ({translation})"
            if color_emoji:
                ref_line += f" {color_emoji}"
            if date:
                ref_line += f"  <sub>{date}</sub>"
            lines.append(ref_line)
            lines.append("")

            if note_text:
                lines.append(f"**My note:** {note_text}")
                lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)
