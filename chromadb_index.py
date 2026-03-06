"""
Step 4 — Build Embeddings & ChromaDB Index

Thought process: We need semantic search over articles — given a query, find the most
relevant ones. ChromaDB is a free, local vector database that handles embedding storage,
metadata, and similarity search. We use all-MiniLM-L6-v2: lightweight (80MB), CPU-friendly,
good general-purpose sentence embeddings. We embed "Title. Abstract" together per article
for the best retrieval signal. ChromaDB metadata must be flat (str, int, float, bool) —
no lists. Keep full abstract in the JSON for the Summarizer Agent.
"""

import json
from typing import List

import chromadb
from chromadb.utils import embedding_functions


def build_index(
    articles: List[dict],
    collection_name: str = "pmc_articles",
    persist_path: str | None = None,
) -> chromadb.Collection:
    """
    Build ChromaDB index from parsed articles.

    Uses sentence-transformers/all-MiniLM-L6-v2 for embeddings.
    Skips articles without abstracts.
    """
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if persist_path:
        client = chromadb.PersistentClient(path=persist_path)
    else:
        client = chromadb.Client()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    documents = []
    metadatas = []
    ids = []

    for article in articles:
        if not article.get("abstract"):
            continue
        # Use pmc_id, fall back to pmid, then to index (some articles may have empty pmc_id)
        article_id = (
            article["pmc_id"]
            or f"PMID{article.get('pmid', '')}"
            or f"article_{len(ids)}"
        )
        doc_text = f"{article['title']}. {article['abstract']}"
        documents.append(doc_text)
        metadatas.append({
            "pmc_id": article.get("pmc_id", ""),
            "pmid": article.get("pmid", ""),
            "title": article["title"],
            "journal": article.get("journal", ""),
            "pub_date": article.get("pub_date", ""),
            "keywords": ", ".join(article.get("keywords", [])),
        })
        ids.append(article_id)

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return collection


def load_articles_and_build_index(
    json_path: str = "articles.json",
    **kwargs,
) -> tuple[chromadb.Collection, List[dict]]:
    """Load articles from JSON and build ChromaDB index."""
    with open(json_path, "r") as f:
        articles = json.load(f)
    collection = build_index(articles, **kwargs)
    return collection, articles
