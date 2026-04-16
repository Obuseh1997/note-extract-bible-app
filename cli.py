#!/usr/bin/env python3
"""CLI entry point for YouVersion Notes & Highlights Exporter."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from extractor import AuthError, NetworkError, authenticate_password, extract_all
from formatter import format_markdown


def get_token_instructions() -> str:
    """Return instructions for getting a YouVersion auth token from browser."""
    return """
╔══════════════════════════════════════════════════════════════════╗
║  How to get your YouVersion auth token (for Google Sign-In):    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  1. Open https://www.bible.com in your browser                   ║
║  2. Log in with your Google account                              ║
║  3. Open Developer Tools (F12 or Cmd+Option+I)                   ║
║  4. Go to Application tab → Storage → Cookies →                  ║
║     https://www.bible.com                                        ║
║  5. Find the cookie named "yva" (it starts with eyJhbGci...)     ║
║  6. Click the row, copy the full value from the Value field      ║
║  7. Paste it when prompted below                                 ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""


async def run_export(
    token: str,
    user_id: int,
    output_path: str,
    group_by_book: bool,
    include_toc: bool,
    include_related: bool = True,
) -> None:
    """Run the full export pipeline."""
    print("\nStarting export...\n")

    def progress_cb(kind: str, page: int, items_on_page: int, total_so_far: int):
        label = "Notes" if kind == "note" else "Highlights"
        print(f"  {label}: page {page} fetched ({items_on_page} items, {total_so_far} total)")

    try:
        data = await extract_all(token, user_id, progress=progress_cb)
    except AuthError as e:
        print(f"\nAuth error: {e}")
        sys.exit(1)
    except NetworkError as e:
        print(f"\nNetwork error: {e}")
        sys.exit(1)

    total = len(data["notes"]) + len(data["highlights"])
    if total == 0:
        print("\nNo notes or highlights found. Check your credentials and try again.")
        sys.exit(1)

    if include_related:
        print("\nFinding related scriptures...")
    markdown = format_markdown(
        data,
        group_by_book=group_by_book,
        include_toc=include_toc,
        include_related=include_related,
        top_k=5,
    )

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    abs_path = str(Path(output_path).resolve())
    print(f"\nExport complete!")
    print(f"  Notes:      {len(data['notes'])}")
    print(f"  Highlights: {len(data['highlights'])}")
    print(f"  Output:     {abs_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Export your YouVersion notes and highlights to markdown."
    )
    parser.add_argument(
        "-o", "--output",
        default="output/youversion-export.md",
        help="Output file path (default: output/youversion-export.md)",
    )
    parser.add_argument(
        "--token",
        help="YouVersion auth token (Bearer token). If not provided, will prompt.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="YouVersion user ID. If not provided, will prompt.",
    )
    parser.add_argument(
        "--username",
        help="YouVersion username (for password-based auth).",
    )
    parser.add_argument(
        "--password",
        help="YouVersion password (for password-based auth).",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Output as a flat chronological list instead of grouped by book.",
    )
    parser.add_argument(
        "--no-toc",
        action="store_true",
        help="Skip the table of contents.",
    )
    parser.add_argument(
        "--no-related",
        action="store_true",
        help="Skip related scriptures (faster export, no AI lookup).",
    )

    args = parser.parse_args()

    token = args.token or os.environ.get("YV_TOKEN")
    user_id = args.user_id or os.environ.get("YV_USER_ID")

    # Auth mode 1: Username/password
    if args.username or args.password:
        username = args.username or input("YouVersion username: ")
        password = args.password or input("YouVersion password: ")
        print("Authenticating...")
        try:
            token, user_id = asyncio.run(authenticate_password(username, password))
            print(f"Authenticated as user {user_id}")
        except AuthError as e:
            print(f"Authentication failed: {e}")
            sys.exit(1)
        except NetworkError as e:
            print(f"Network error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Authentication failed: {e}")
            sys.exit(1)

    # Auth mode 2: Token-based (for Google Sign-In users)
    if not token:
        print(get_token_instructions())
        token = input("Paste your auth token: ").strip()

    if not user_id:
        # Try to extract user_id from JWT token
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("user_id") or decoded.get("sub")
            if user_id:
                print(f"Detected user ID from token: {user_id}")
        except Exception:
            pass

    if not user_id:
        user_id_str = input("Enter your YouVersion user ID: ").strip()
        try:
            user_id = int(user_id_str)
        except ValueError:
            print("Invalid user ID. Must be a number.")
            sys.exit(1)

    asyncio.run(
        run_export(
            token,
            int(user_id),
            args.output,
            group_by_book=not args.flat,
            include_toc=not args.no_toc,
            include_related=not args.no_related,
        )
    )


if __name__ == "__main__":
    main()
