"""Scripture semantic search using precomputed Bible embeddings.

Loads bible_index.npz and web_bible.json once at import and provides
find_related() to surface thematically connected verses for a given note.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

BASE_DIR = Path(__file__).parent
INDEX_PATH = BASE_DIR / "bible_index.npz"
BIBLE_PATH = BASE_DIR / "web_bible.json"

_model = None
_embeddings: Optional[np.ndarray] = None
_references: Optional[list[str]] = None
_bible: Optional[dict[str, str]] = None


def _load_index() -> tuple[np.ndarray, list[str], dict[str, str]]:
    """Load the precomputed index and Bible text. Called once."""
    global _embeddings, _references, _bible

    if _embeddings is not None:
        return _embeddings, _references, _bible

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Bible index not found at {INDEX_PATH}. "
            "Run build_bible_index.py first."
        )
    if not BIBLE_PATH.exists():
        raise FileNotFoundError(
            f"Bible text not found at {BIBLE_PATH}. "
            "Run build_bible_index.py first."
        )

    data = np.load(INDEX_PATH, allow_pickle=False)
    _embeddings = data["embeddings"].astype(np.float32)
    _references = data["references"].tolist()

    with open(BIBLE_PATH, encoding="utf-8") as f:
        _bible = json.load(f)

    return _embeddings, _references, _bible


def _get_model():
    """Load the sentence-transformers model (cached)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_verse_text(reference: str) -> str:
    """Look up the KJV text for a given reference (e.g. '1 Samuel 16:14').

    Handles YouVersion → KJV book name conversions (Arabic → Roman numerals,
    Psalm/Psalms variants, Song of Solomon variants).
    Returns empty string if not found.
    """
    _, _, bible = _load_index()

    candidates = [
        reference,
        _yv_to_kjv_ref(reference),
        reference.replace("Psalm ", "Psalms "),
        reference.replace("Psalms ", "Psalm "),
        reference.replace("Song of Songs", "Song of Solomon"),
        reference.replace("Song of Solomon", "Song of Songs"),
    ]
    for candidate in candidates:
        text = bible.get(candidate, "")
        if text:
            return text

    return ""


def find_related(
    note_text: str,
    top_k: int = 5,
    exclude_ref: Optional[str] = None,
    snippet_length: int = 120,
) -> list[dict]:
    """Find Bible verses thematically related to a note.

    Args:
        note_text: The user's note content (e.g. "Depression is a spirit")
        top_k: Number of results to return
        exclude_ref: A verse reference to exclude from results (the noted verse itself)
        snippet_length: Max characters of verse text to include in each result

    Returns:
        List of dicts: [{reference, text, snippet, score}]
    """
    if not note_text or not note_text.strip():
        return []

    embeddings, references, bible = _load_index()
    model = _get_model()

    # Embed the note text
    query_embedding = model.encode(
        [note_text],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0].astype(np.float32)

    # Cosine similarity (embeddings are pre-normalised, so dot product = cosine)
    scores = embeddings @ query_embedding

    # Get top results, excluding the noted verse
    top_indices = np.argsort(scores)[::-1]

    results = []
    for idx in top_indices:
        kjv_ref = references[idx]
        # Exclude the noted verse (handle book name variants)
        if exclude_ref and _refs_match(kjv_ref, exclude_ref):
            continue

        verse_text = bible.get(kjv_ref, "")
        snippet = verse_text[:snippet_length]
        if len(verse_text) > snippet_length:
            snippet = snippet.rstrip() + "..."

        # Convert KJV reference (Roman) back to Arabic for display
        display_ref = kjv_ref
        for roman, arabic in _ROMAN_TO_ARABIC.items():
            if kjv_ref.startswith(roman + " "):
                display_ref = arabic + kjv_ref[len(roman):]
                break

        results.append({
            "reference": display_ref,
            "text": verse_text,
            "snippet": snippet,
            "score": float(scores[idx]),
        })

        if len(results) >= top_k:
            break

    return results


# Arabic ↔ Roman numeral book name mapping (YouVersion uses Arabic, KJV uses Roman)
_ARABIC_TO_ROMAN = {
    "1 Samuel": "I Samuel", "2 Samuel": "II Samuel",
    "1 Kings": "I Kings", "2 Kings": "II Kings",
    "1 Chronicles": "I Chronicles", "2 Chronicles": "II Chronicles",
    "1 Corinthians": "I Corinthians", "2 Corinthians": "II Corinthians",
    "1 Thessalonians": "I Thessalonians", "2 Thessalonians": "II Thessalonians",
    "1 Timothy": "I Timothy", "2 Timothy": "II Timothy",
    "1 Peter": "I Peter", "2 Peter": "II Peter",
    "1 John": "I John", "2 John": "II John", "3 John": "III John",
    "1 Maccabees": "I Maccabees", "2 Maccabees": "II Maccabees",
}
_ROMAN_TO_ARABIC = {v: k for k, v in _ARABIC_TO_ROMAN.items()}


def _normalise_ref(ref: str) -> str:
    """Normalise a reference to a canonical form for comparison."""
    ref = ref.strip()
    # Convert Arabic numbers to Roman (KJV style) for matching
    for arabic, roman in _ARABIC_TO_ROMAN.items():
        if ref.startswith(arabic + " "):
            ref = roman + ref[len(arabic):]
            break
    # Normalise Psalm/Psalms
    ref = ref.replace("Psalm ", "Psalms ")
    # Normalise Song of Solomon variants
    ref = ref.replace("Song of Songs", "Song of Solomon")
    return ref


def _yv_to_kjv_ref(ref: str) -> str:
    """Convert a YouVersion reference (Arabic) to KJV format (Roman numerals)."""
    for arabic, roman in _ARABIC_TO_ROMAN.items():
        if ref.startswith(arabic + " "):
            return roman + ref[len(arabic):]
    return ref


def _refs_match(ref_a: str, ref_b: str) -> bool:
    """Loosely match two verse references, ignoring book name variants."""
    return _normalise_ref(ref_a) == _normalise_ref(ref_b)
