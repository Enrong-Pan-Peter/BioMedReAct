"""
Retriever agent — semantic search over articles via ChromaDB.
"""

from typing import List


class RetrieverAgent:
    def __init__(self, collection, articles_data: List[dict] = None, lookup: dict = None, k: int = 5):
        self.collection = collection
        self.k = k
        if lookup is not None:
            self.articles_lookup = lookup
        else:
            self.articles_lookup = {}
            for a in (articles_data or []):
                key = a.get("pmc_id") or f"PMID{a.get('pmid', '')}" or "article_unknown"
                self.articles_lookup[key] = a

    def retrieve(self, query: str, k: int = None) -> List[dict]:
        k = k or self.k
        results = self.collection.query(query_texts=[query], n_results=k)

        ids_list = results["ids"][0] or []
        distances_list = results.get("distances", [[]])
        distances_list = distances_list[0] if distances_list else []

        out = []
        for i, chroma_id in enumerate(ids_list):
            dist = distances_list[i] if i < len(distances_list) else None
            art = self.articles_lookup.get(chroma_id, {})
            out.append({
                "pmc_id": art.get("pmc_id", chroma_id),
                "pmid": art.get("pmid", ""),
                "title": art.get("title", ""),
                "abstract": art.get("abstract", ""),
                "authors": art.get("authors", []),
                "journal": art.get("journal", ""),
                "pub_date": art.get("pub_date", ""),
                "keywords": art.get("keywords", []),
                "relevance_score": round(1 - dist, 4) if dist is not None else None,
            })
        return out
