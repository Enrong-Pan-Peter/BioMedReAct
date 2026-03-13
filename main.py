#!/usr/bin/env python3
"""
Interactive CLI for biomedical literature review.
Per-query pipeline: search → fetch → parse → index → retrieve → summarize.
"""

import json
import os
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions

from agents.retriever import RetrieverAgent
from agents.summarizer import SummarizerAgent
from utils.fetch import fetch_xml_from_s3, fetch_all_xmls
from utils.parse import parse_and_filter
from utils.search import search_pmc
from utils.spinner import Spinner


def _article_id(article: dict, index: int) -> str:
    """Same ID logic as ChromaDB indexing."""
    pmc = article.get("pmc_id") or ""
    pmid = article.get("pmid") or ""
    if pmc:
        return pmc
    if pmid:
        return f"PMID{pmid}"
    return f"article_{index}"


def _build_index(articles: list, client: chromadb.Client) -> tuple:
    """Build ChromaDB index with dedup. Returns (collection, lookup_dict)."""
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    try:
        client.delete_collection("pmc_articles")
    except Exception:
        pass

    coll = client.create_collection(
        name="pmc_articles",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    seen = set()
    docs, metas, ids = [], [], []
    lookup = {}

    for i, art in enumerate(articles):
        if not art.get("abstract"):
            continue
        aid = _article_id(art, i)
        if aid in seen:
            continue
        seen.add(aid)
        lookup[aid] = art

        docs.append(f"{art['title']}. {art['abstract']}")
        metas.append({
            "pmc_id": art.get("pmc_id", ""),
            "pmid": art.get("pmid", ""),
            "title": art["title"],
            "journal": art.get("journal", ""),
            "pub_date": art.get("pub_date", ""),
            "keywords": ", ".join(art.get("keywords", [])),
        })
        ids.append(aid)

    if docs:
        coll.add(documents=docs, metadatas=metas, ids=ids)
    return coll, lookup


def _format_report(report: dict) -> str:
    lines = [
        "",
        "=" * 70,
        f"Query: {report['query']}",
        f"Generated: {report['timestamp']}  |  Results: {report['num_results']}",
        "=" * 70,
    ]
    for i, art in enumerate(report["articles"], 1):
        lines.extend([
            "",
            f"--- Article {i} ---",
            f"Title:   {art.get('title', '')}",
            f"ID:      {art.get('pmc_id', '')}  |  PMID: {art.get('pmid', '')}",
            f"Journal: {art.get('journal', '')}  |  Date: {art.get('pub_date', '')}",
            f"Score:   {art.get('relevance_score')}",
            f"Summary: {art.get('summary', '')}",
            f"Keywords: {', '.join(art.get('keywords', []))}",
        ])
    return "\n".join(lines)


def run_pipeline(query: str, k: int, pool_size: int) -> dict:
    """Run full pipeline for one query. Returns report dict."""

    # 1. Search
    s = Spinner("Searching PubMed Central")
    s.start()
    pmc_ids = search_pmc(query, max_results=pool_size)
    s.stop()
    print(f"  Found {len(pmc_ids)} IDs")

    # 2. Fetch
    s = Spinner("Downloading articles from AWS S3")
    s.start()
    raw_xmls = fetch_all_xmls(pmc_ids, quiet=True)
    s.stop()
    print(f"  Downloaded {len(raw_xmls)} XML files")

    # 3. Parse
    s = Spinner("Parsing article metadata")
    s.start()
    articles = parse_and_filter(raw_xmls)
    s.stop()
    print(f"  Parsed {len(articles)} articles with abstracts")

    if not articles:
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "num_results": 0,
            "articles": [],
        }

    # 4. Index
    s = Spinner("Building semantic search index")
    s.start()
    client = chromadb.Client()
    coll, lookup = _build_index(articles, client)
    s.stop()
    print(f"  Indexed {len(coll.get()['ids'])} articles")

    # 5. Retrieve
    s = Spinner("Finding top K articles")
    s.start()
    retriever = RetrieverAgent(coll, lookup=lookup, k=k)
    results = retriever.retrieve(query, k=k)
    s.stop()

    # 6. Summarize
    s = Spinner("Generating summaries with T5")
    s.start()
    summarizer = SummarizerAgent()
    summarized = summarizer.summarize_batch(results)
    s.stop()

    report = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "num_results": len(summarized),
        "articles": [
            {
                "pmc_id": a.get("pmc_id"),
                "pmid": a.get("pmid"),
                "title": a.get("title"),
                "authors": a.get("authors", []),
                "journal": a.get("journal"),
                "pub_date": a.get("pub_date"),
                "summary": a.get("summary"),
                "keywords": a.get("extracted_keywords", a.get("keywords", [])),
                "relevance_score": a.get("relevance_score"),
            }
            for a in summarized
        ],
    }
    return report


def main():
    os.makedirs("reports", exist_ok=True)

    print()
    print("  Biomed Literature Review — Interactive CLI")
    print("  PubMed Central → S3 → ChromaDB → T5")
    print()

    while True:
        query = input("Enter your research query: ").strip()
        if not query:
            print("Query cannot be empty.")
            continue

        k_str = input("Number of articles to recommend (default 5): ").strip()
        k = int(k_str) if k_str else 5

        pool_str = input("Size of article pool to search (default 50): ").strip()
        pool_size = int(pool_str) if pool_str else 50

        try:
            report = run_pipeline(query, k, pool_size)
        except Exception as e:
            print(f"Error: {e}")
            print("Try again or check your network.")
            continue

        print(_format_report(report))

        fname = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fname, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved to {fname}")

        again = input("\nRun another query? (y/n): ").strip().lower()
        if again != "y":
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()
