"""Core extraction logic for YouVersion notes and highlights.

Version: 0.2.0 — progress callbacks, typed errors.
"""

from datetime import datetime
from typing import Any, Callable, Optional

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


class AuthError(Exception):
    """Raised when authentication fails or token is expired."""


class NetworkError(Exception):
    """Raised when we can't reach YouVersion's API."""


def color_emoji(hex_color: str) -> str:
    """Convert a hex color code to an emoji circle."""
    clean = hex_color.lower().lstrip("#")
    return COLOR_MAP.get(clean, f"({hex_color})")


# Progress callback signature: fn(kind: str, page: int, items_on_page: int, total_so_far: int)
ProgressCallback = Callable[[str, int, int, int], None]


async def authenticate_password(username: str, password: str) -> tuple[str, Optional[int]]:
    """Authenticate with YouVersion using username/password.

    Returns (access_token, user_id). Raises AuthError on failure.
    """
    import jwt

    try:
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
    except httpx.RequestError as e:
        raise NetworkError(f"Couldn't reach YouVersion auth server: {e}") from e

    if response.status_code in (400, 401, 403):
        raise AuthError(
            "YouVersion rejected your credentials. "
            "Double-check your email and password."
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
    progress: Optional[ProgressCallback] = None,
) -> list[dict[str, Any]]:
    """Fetch all items of a given kind (note, highlight) with pagination.

    Args:
        token: Bearer token for auth
        user_id: YouVersion user ID
        kind: Moment kind (e.g. "note", "highlight")
        max_pages: Safety limit on pages to fetch
        progress: Optional callback invoked after each page

    Returns:
        List of raw moment dicts from the API
    """
    all_items: list[dict[str, Any]] = []
    headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for page in range(1, max_pages + 1):
                url = f"{MOMENTS_API_BASE}{MOMENTS_ITEMS_URL}"
                params = {"page": page, "kind": kind, "user_id": user_id}

                response = await client.get(url, params=params)

                if response.status_code == 404:
                    break  # No more pages
                if response.status_code == 401:
                    raise AuthError(
                        "Your auth token has expired. Go back to bible.com, "
                        "refresh the page, and copy a fresh 'yva' cookie value."
                    )
                if response.status_code == 403:
                    raise AuthError(
                        "Access forbidden. Your token may not have permission "
                        "to read this user's data. Make sure the user ID matches "
                        "the account that owns the token."
                    )
                response.raise_for_status()

                data = response.json()
                if "response" in data:
                    data = data["response"].get("data", {})

                moments = data.get("moments", [])
                if not moments:
                    break

                all_items.extend(moments)

                if progress:
                    progress(kind, page, len(moments), len(all_items))

    except httpx.RequestError as e:
        raise NetworkError(
            f"Couldn't reach YouVersion's API: {e}. Check your internet connection."
        ) from e

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

    l_args = moment.get("base", {}).get("title", {}).get("l_args", {})
    translation = l_args.get("version_abbreviation", "")

    return (human, translation)


def parse_verse_text(moment: dict[str, Any]) -> str:
    """Verse text is not included in this API endpoint."""
    return ""


def parse_note_body(moment: dict[str, Any]) -> str:
    """Extract the user's written note text from a moment."""
    return (moment.get("extras", {}).get("content") or "").strip()


def parse_color(moment: dict[str, Any]) -> str:
    """Extract highlight color hex from a moment."""
    return (moment.get("extras", {}).get("color") or "").strip()


def parse_created_date(moment: dict[str, Any]) -> str:
    """Extract and format the creation date (YYYY-MM-DD)."""
    dt_str = moment.get("created_dt", "")
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return dt_str


async def extract_all(
    token: str,
    user_id: int,
    progress: Optional[ProgressCallback] = None,
) -> dict[str, list[dict[str, Any]]]:
    """Extract all notes and highlights from YouVersion.

    Returns dict with 'notes' and 'highlights' keys.
    """
    raw_notes = await fetch_all_items(
        token, user_id, kind="note", progress=progress
    )
    raw_highlights = await fetch_all_items(
        token, user_id, kind="highlight", progress=progress
    )

    notes = [
        {
            "reference": (p := parse_reference(m))[0],
            "version": p[1],
            "verse_text": parse_verse_text(m),
            "note": parse_note_body(m),
            "date": parse_created_date(m),
        }
        for m in raw_notes
    ]

    highlights = [
        {
            "reference": (p := parse_reference(m))[0],
            "version": p[1],
            "verse_text": parse_verse_text(m),
            "color": parse_color(m),
            "color_emoji": color_emoji(parse_color(m)),
            "note": parse_note_body(m),
            "date": parse_created_date(m),
        }
        for m in raw_highlights
    ]

    return {"notes": notes, "highlights": highlights}
