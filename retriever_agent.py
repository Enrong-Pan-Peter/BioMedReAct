"""
Step 5 — Retriever Agent

Thought process: The Retriever Agent wraps ChromaDB queries and enriches results with
full article data from our JSON/articles list. ChromaDB returns only IDs and distances —
we need the full abstract, authors, etc. for the Summarizer Agent. We convert ChromaDB's
distance (lower = more similar for cosine) to a user-friendly relevance_score as 1 - distance.
"""

from typing import List


class RetrieverAgent:
    """Retrieves top-K relevant articles from ChromaDB given a query."""

    def __init__(self, collection, articles_data: List[dict], k: int = 5):
        self.collection = collection
        self.k = k
        self.articles_lookup = {}
        for a in articles_data:
            key = (
                a.get("pmc_id")
                or f"PMID{a.get('pmid', '')}"
                or "article_unknown"
            )
            self.articles_lookup[key] = a

    def retrieve(self, query: str, k: int | None = None) -> List[dict]:
        """
        Query ChromaDB and return top-K articles with full data.

        Returns list of dicts with keys:
        pmc_id, pmid, title, abstract, authors, journal, pub_date, keywords,
        relevance_score (cosine similarity — higher = more relevant)
        """
        k = k or self.k
        results = self.collection.query(query_texts=[query], n_results=k)

        retrieved = []
        ids_list = results["ids"][0] or []
        distances_list = (
            results.get("distances", [[]])[0] if results.get("distances") else []
        )

        for i in range(len(ids_list)):
            chroma_id = ids_list[i]
            distance = distances_list[i] if i < len(distances_list) else None
            article_data = self.articles_lookup.get(chroma_id, {})

            retrieved.append({
                "pmc_id": article_data.get("pmc_id", chroma_id),
                "pmid": article_data.get("pmid", ""),
                "title": article_data.get("title", ""),
                "abstract": article_data.get("abstract", ""),
                "authors": article_data.get("authors", []),
                "journal": article_data.get("journal", ""),
                "pub_date": article_data.get("pub_date", ""),
                "keywords": article_data.get("keywords", []),
                "relevance_score": round(1 - distance, 4) if distance is not None else None,
            })

        return retrieved
