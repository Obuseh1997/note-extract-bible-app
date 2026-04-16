"""
One-time script to build the Bible search index.

Downloads the World English Bible (public domain), embeds all verses
using sentence-transformers, and saves the index for use by scripture_search.py.

Run once:
    python build_bible_index.py

Outputs:
    web_bible.json       - verse text keyed by reference (e.g. "John 3:16")
    bible_index.npz      - verse embeddings + reference list
"""

import json
import time
from pathlib import Path

import httpx
import numpy as np

# KJV Bible — public domain, single structured JSON file
KJV_BIBLE_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/KJV.json"

OUTPUT_DIR = Path(__file__).parent

# Book ID → name mapping (matches the t_web.json format)
BOOK_NAMES = {
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Samuel", 10: "2 Samuel",
    11: "1 Kings", 12: "2 Kings", 13: "1 Chronicles", 14: "2 Chronicles",
    15: "Ezra", 16: "Nehemiah", 17: "Esther", 18: "Job", 19: "Psalms",
    20: "Proverbs", 21: "Ecclesiastes", 22: "Song of Solomon", 23: "Isaiah",
    24: "Jeremiah", 25: "Lamentations", 26: "Ezekiel", 27: "Daniel",
    28: "Hosea", 29: "Joel", 30: "Amos", 31: "Obadiah", 32: "Jonah",
    33: "Micah", 34: "Nahum", 35: "Habakkuk", 36: "Zephaniah", 37: "Haggai",
    38: "Zechariah", 39: "Malachi",
    40: "Matthew", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Romans", 46: "1 Corinthians", 47: "2 Corinthians", 48: "Galatians",
    49: "Ephesians", 50: "Philippians", 51: "Colossians",
    52: "1 Thessalonians", 53: "2 Thessalonians", 54: "1 Timothy",
    55: "2 Timothy", 56: "Titus", 57: "Philemon", 58: "Hebrews",
    59: "James", 60: "1 Peter", 61: "2 Peter", 62: "1 John", 63: "2 John",
    64: "3 John", 65: "Jude", 66: "Revelation",
}


def download_bible() -> dict[str, str]:
    """Download KJV Bible and return {reference: verse_text} dict."""
    print("Downloading KJV Bible...")
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(KJV_BIBLE_URL)
        resp.raise_for_status()
        raw = resp.json()

    # Structure: {books: [{name, chapters: [{chapter, verses: [{verse, text}]}]}]}
    verses: dict[str, str] = {}
    for book in raw.get("books", []):
        book_name = book.get("name", "")
        for chapter_obj in book.get("chapters", []):
            chapter_num = chapter_obj.get("chapter")
            for verse_obj in chapter_obj.get("verses", []):
                verse_num = verse_obj.get("verse")
                text = verse_obj.get("text", "").strip()
                if not text:
                    continue
                ref = f"{book_name} {chapter_num}:{verse_num}"
                verses[ref] = text

    print(f"Loaded {len(verses):,} verses")
    return verses


def build_embeddings(verses: dict[str, str]) -> tuple[list[str], np.ndarray]:
    """Embed all verses. Returns (references_list, embeddings_matrix)."""
    from sentence_transformers import SentenceTransformer

    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    references = list(verses.keys())
    texts = list(verses.values())

    print(f"Embedding {len(texts):,} verses (this takes 2-5 minutes)...")
    t0 = time.time()

    embeddings = model.encode(
        texts,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True,  # pre-normalise for fast cosine similarity
        convert_to_numpy=True,
    )

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s — embedding shape: {embeddings.shape}")
    return references, embeddings


def save_outputs(
    verses: dict[str, str],
    references: list[str],
    embeddings: np.ndarray,
) -> None:
    """Save web_bible.json and bible_index.npz."""
    bible_path = OUTPUT_DIR / "web_bible.json"
    index_path = OUTPUT_DIR / "bible_index.npz"

    with open(bible_path, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False)
    print(f"Saved {bible_path} ({bible_path.stat().st_size / 1024 / 1024:.1f} MB)")

    np.savez_compressed(
        index_path,
        embeddings=embeddings,
        references=np.array(references),
    )
    print(f"Saved {index_path} ({index_path.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    verses = download_bible()

    with open(OUTPUT_DIR / "web_bible.json", "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False)

    references, embeddings = build_embeddings(verses)
    save_outputs(verses, references, embeddings)

    print("\nAll done! Files ready:")
    print("  web_bible.json")
    print("  bible_index.npz")
    print("\nNow run: git add web_bible.json bible_index.npz && git commit -m 'Add Bible index'")
