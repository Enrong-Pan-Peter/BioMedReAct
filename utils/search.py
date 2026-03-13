"""
PubMed Central search via E-utilities.
Query preprocessing to handle natural language — E-utilities prefers keyword-style.
"""

import time
from typing import List

import requests

# phrases where stopwords are part of the meaning — don't break these
PROTECTED_PHRASES = [
    "in vitro",
    "in vivo",
    "in situ",
    "in utero",
    "based on",
    "onset of",
    "risk of",
    "rate of",
    "response to",
    "resistance to",
    "sensitive to",
    "compared to",
    "due to",
    "prior to",
]

# safe to strip — rarely carry meaning in biomedical queries
STOPWORDS = {"with", "the", "a", "an", "and", "or", "to", "by", "from", "is", "are", "was", "were", "what", "how"}

# aggressive mode: also strip these (they often do carry meaning)
AGGRESSIVE_STOPWORDS = STOPWORDS | {"in", "of", "for", "on"}


def clean_query_for_api(query: str, aggressive: bool = False) -> str:
    """
    Preprocess query for E-utilities. Protects biomedical phrases, strips filler.
    """
    if not query or not query.strip():
        return query

    q = query.strip().lower()
    stopwords = AGGRESSIVE_STOPWORDS if aggressive else STOPWORDS

    # pass 1: protect phrases
    placeholders = {}
    for i, phrase in enumerate(PROTECTED_PHRASES):
        if phrase in q:
            tok = f"__P{i}__"
            placeholders[tok] = phrase
            q = q.replace(phrase, tok)

    # pass 2: remove stopwords (but not in middle of protected tokens)
    words = q.split()
    if not aggressive:
        # only strip at start/end for "in", "of", "for", "on"
        edge_stop = {"in", "of", "for", "on"}
        while words and words[0] in edge_stop:
            words.pop(0)
        while words and words[-1] in edge_stop:
            words.pop()

    filtered = [w for w in words if w not in stopwords]

    # pass 3: restore placeholders
    result_parts = []
    for w in filtered:
        if w in placeholders:
            result_parts.append(placeholders[w])
        else:
            result_parts.append(w)

    return " ".join(result_parts)


def _do_search(term: str, max_results: int) -> List[str]:
    """Actual E-utilities call. Appends open access filter."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    # filter for open access so results are more likely in S3
    full_term = f"({term}) AND open access[filter]" if term.strip() else term
    params = {
        "db": "pmc",
        "term": full_term,
        "retmax": max_results,
        "retmode": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    return [f"PMC{pid}" for pid in ids]


def search_pmc(query: str, max_results: int = 50) -> List[str]:
    """
    Search PMC with smart query cleaning and fallback.
    Returns list of PMC IDs.
    """
    cleaned = clean_query_for_api(query, aggressive=False)
    results = _do_search(cleaned, max_results)

    if not results:
        results = _do_search(query, max_results)

    if not results:
        cleaned_agg = clean_query_for_api(query, aggressive=True)
        results = _do_search(cleaned_agg, max_results)

    time.sleep(0.5)  # rate limit
    return results
