"""
Phase 1 — Data Acquisition Pipeline

Orchestrates the full flow: discover articles via PubMed E-utilities → fetch XML from S3
→ parse to structured JSON → quality check. Mirrors the notebook cell sequence.
"""

import json
from typing import List

from pmc_search import discover_articles
from s3_fetcher import fetch_all_xmls
from xml_parser import parse_and_filter

# Test queries from the plan
TEST_QUERIES = [
    "Adverse events with mRNA vaccines in pediatrics",
    "Transformer-based models for protein folding",
    "Clinical trial outcomes for monoclonal antibodies in oncology",
]


def run_quality_check(articles: List[dict]) -> None:
    """Print stats: total articles, with abstracts, with keywords."""
    total = len(articles)
    with_abstracts = sum(1 for a in articles if a.get("abstract"))
    with_keywords = sum(1 for a in articles if a.get("keywords"))

    print("=== Quality Check ===")
    print(f"Total articles:        {total}")
    print(f"With abstracts:       {with_abstracts}")
    print(f"With keywords:        {with_keywords}")
    print(f"Without abstracts:    {total - with_abstracts} (excluded from index)")


def run(output_path: str = "articles.json") -> List[dict]:
    """
    Run the full Phase 1 pipeline and return parsed articles.
    """
    # Step 1: Discover PMC IDs
    print("Step 1 — Article Discovery")
    pmc_ids = discover_articles(TEST_QUERIES, max_per_query=30)
    print(f"\nTotal unique PMC IDs: {len(pmc_ids)}\n")

    # Step 2: Fetch XML from S3
    print("Step 2 — Fetch XML from S3")
    raw_xmls = fetch_all_xmls(pmc_ids)
    print(f"  Successfully fetched {len(raw_xmls)} XML files\n")

    # Step 3: Parse and save
    print("Step 3 — Parse XML to JSON")
    articles = parse_and_filter(raw_xmls)
    with open(output_path, "w") as f:
        json.dump(articles, f, indent=2)
    print(f"  Saved {len(articles)} articles to {output_path}\n")

    # Quality check
    print("Quality Check")
    run_quality_check(articles)

    return articles


if __name__ == "__main__":
    run()
