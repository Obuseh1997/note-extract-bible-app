"""Core extraction logic for YouVersion notes and highlights."""

import asyncio
from datetime import datetime
from typing import Any, Optional

import httpx

# YouVersion API constants (from youversion-bible-client library)
MOMENTS_API_BASE = "https://moments.youversionapi.com"
MOMENTS_ITEMS_URL = "/3.1/items.json"
AUTH_URL = "https://auth.youversionapi.com/token"
CLIENT_ID = "85b61d97a79b96be465ebaeee83b1313"
CLIENT_SECRET = "75cf0e141cbf41ef410adce5b6537a49"

DEFAULT_HEADERS = {
    "Referer": "http://android.youversionapi.com/",
    "X-YouVersion-App-Platform": "android",
    "X-YouVersion-App-Version": "17114",
    "X-YouVersion-Client": "youversion",
}

# Highlight color mapping (hex → emoji)
COLOR_MAP = {
    "ffd556": "\U0001f7e1",  # yellow
    "6dc1a7": "\U0001f7e2",  # green
    "ff8683": "\U0001f534",  # red
    "7bd0ed": "\U0001f535",  # blue
    "d783ff": "\U0001f7e3",  # purple
    "f89645": "\U0001f7e0",  # orange
}


def color_emoji(hex_color: str) -> str:
    """Convert a hex color code to an emoji circle."""
    clean = hex_color.lower().lstrip("#")
    return COLOR_MAP.get(clean, f"({hex_color})")


async def authenticate_password(username: str, password: str) -> tuple[str, Optional[int]]:
    """Authenticate with YouVersion using username/password.

    Returns (access_token, user_id).
    """
    import jwt

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            AUTH_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": username,
                "password": password,
            },
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data["access_token"]

        # Extract user_id from JWT
        user_id = None
        try:
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            user_id = decoded.get("user_id") or decoded.get("sub")
        except Exception:
            pass

        return access_token, user_id


async def fetch_all_items(
    token: str,
    user_id: int,
    kind: str,
    max_pages: int = 100,
) -> list[dict[str, Any]]:
    """Fetch all items of a given kind (note, highlight, etc.) with pagination.

    Args:
        token: Bearer token for auth
        user_id: YouVersion user ID
        kind: Moment kind (e.g. "note", "highlight")
        max_pages: Safety limit on pages to fetch

    Returns:
        List of raw moment dicts from the API
    """
    all_items = []
    headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for page in range(1, max_pages + 1):
            url = f"{MOMENTS_API_BASE}{MOMENTS_ITEMS_URL}"
            params = {"page": page, "kind": kind, "user_id": user_id}

            response = await client.get(url, params=params)
            if response.status_code == 404:
                break  # No more pages
            if response.status_code == 401:
                raise RuntimeError(
                    "Auth token rejected (401). Your 'yva' cookie has expired.\n"
                    "Go back to bible.com, refresh the page, and copy a fresh 'yva' value."
                )
            response.raise_for_status()
            data = response.json()

            # Navigate the response envelope
            if "response" in data:
                data = data["response"].get("data", {})

            moments = data.get("moments", [])
            if not moments:
                break

            all_items.extend(moments)
            print(f"  Fetched page {page}: {len(moments)} {kind}(s)")

    return all_items


def parse_reference(moment: dict[str, Any]) -> tuple[str, str]:
    """Extract human-readable reference and translation abbreviation.

    Returns (reference, translation_abbrev).
    """
    extras = moment.get("extras", {})
    references = extras.get("references", [])
    if not references:
        return ("Unknown", "")

    human = references[0].get("human", "Unknown")

    # Translation abbreviation lives in base.title.l_args
    l_args = moment.get("base", {}).get("title", {}).get("l_args", {})
    translation = l_args.get("version_abbreviation", "")

    return (human, translation)


def parse_verse_text(moment: dict[str, Any]) -> str:
    """Verse text is not included in this API endpoint — returns empty string."""
    return ""


def parse_note_body(moment: dict[str, Any]) -> str:
    """Extract the user's written note text from a moment."""
    return (moment.get("extras", {}).get("content") or "").strip()


def parse_color(moment: dict[str, Any]) -> str:
    """Extract highlight color hex from a moment."""
    return (moment.get("extras", {}).get("color") or "").strip()


def parse_created_date(moment: dict[str, Any]) -> str:
    """Extract and format the creation date."""
    dt_str = moment.get("created_dt", "")
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return dt_str


async def extract_all(token: str, user_id: int) -> dict[str, list[dict[str, Any]]]:
    """Extract all notes and highlights from YouVersion.

    Returns dict with 'notes' and 'highlights' keys, each containing
    a list of parsed item dicts.
    """
    print("Fetching notes...")
    raw_notes = await fetch_all_items(token, user_id, kind="note")
    print(f"Total notes: {len(raw_notes)}")

    print("\nFetching highlights...")
    raw_highlights = await fetch_all_items(token, user_id, kind="highlight")
    print(f"Total highlights: {len(raw_highlights)}")

    notes = []
    for m in raw_notes:
        ref, version = parse_reference(m)
        notes.append({
            "reference": ref,
            "version": version,
            "verse_text": parse_verse_text(m),
            "note": parse_note_body(m),
            "date": parse_created_date(m),
        })

    highlights = []
    for m in raw_highlights:
        ref, version = parse_reference(m)
        highlights.append({
            "reference": ref,
            "version": version,
            "verse_text": parse_verse_text(m),
            "color": parse_color(m),
            "color_emoji": color_emoji(parse_color(m)),
            "note": parse_note_body(m),
            "date": parse_created_date(m),
        })

    return {"notes": notes, "highlights": highlights}
