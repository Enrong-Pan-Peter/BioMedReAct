"""
Step 1 — Article Discovery via PubMed E-utilities

Thought process: The S3 CSV file list only contains citation strings, PMC IDs, and S3 keys —
no titles or abstracts to filter by topic. We need a way to discover relevant articles by
searching PubMed Central. NCBI's free E-utilities API lets us search PMC by topic and
retrieve PMC IDs, which we can then use to fetch XML from S3.
"""

import time
from typing import List

import requests


def search_pmc(query: str, max_results: int = 30) -> List[str]:
    """
    Search PubMed Central by topic and return a list of PMC IDs.

    Uses the ESearch endpoint. Returns numeric IDs converted to PMC format (e.g., PMC1234567).
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pmc",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    pmc_ids = data["esearchresult"]["idlist"]
    return [f"PMC{pid}" for pid in pmc_ids]


def discover_articles(
    queries: List[str], max_per_query: int = 30, verbose: bool = True
) -> List[str]:
    """
    Search PMC for multiple queries, collect PMC IDs, and deduplicate.

    Rate limiting: E-utilities allows 3 requests/sec without an API key.
    We add a 0.5s delay between calls to stay under the limit.
    """
    all_pmc_ids = set()
    for query in queries:
        pmc_ids = search_pmc(query, max_results=max_per_query)
        all_pmc_ids.update(pmc_ids)
        if verbose:
            print(f"Searching: {query}")
            print(f"  Found {len(pmc_ids)} IDs")
        time.sleep(0.5)
    return list(all_pmc_ids)
