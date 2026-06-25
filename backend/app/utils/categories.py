"""Category matching utilities for transaction classification."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Optional


def match_category(text: str, categories: list[dict]) -> Optional[dict]:
    """Match user text against a list of category definitions."""
    if not text or not categories:
        return None

    text_lower = text.lower().strip()
    best_cat = None
    best_score = 0

    for cat in categories:
        keywords = cat.get("keywords", [])
        cat_name = cat.get("name", "")

        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hits > best_score:
            best_score = hits
            best_cat = cat

        if cat_name.lower() in text_lower:
            if best_score < 999:
                best_score = 999
                best_cat = cat

    if best_score == 0:
        best_ratio = 0.0
        for cat in categories:
            cat_name = cat.get("name", "")
            ratio = SequenceMatcher(None, text_lower, cat_name.lower()).ratio()
            if ratio > best_ratio and ratio > 0.5:
                best_ratio = ratio
                best_cat = cat

    return best_cat
