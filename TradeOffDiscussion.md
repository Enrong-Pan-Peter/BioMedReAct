# Key Design Decisions & Tradeoffs

This document tracks the architectural and implementation decisions made throughout the project, along with the reasoning and tradeoffs for each.

---

## 1. Data Format: XML over TXT

**Decision:** Use XML format for article retrieval from S3.

**Why:** JATS XML provides structured tags for every field we need — `<article-title>`, `<abstract>`, `<contrib>`, `<kwd-group>`, etc. This allows precise, programmatic extraction of title, abstract, authors, keywords, and body text separately.

**Tradeoff:** XML parsing is more complex than reading plain text (requires `lxml` or `xml.etree`), and JATS XML varies across publishers so defensive coding is needed. However, TXT files have no structure at all — you'd need heuristics or regex to guess where the abstract ends and the body begins, which is fragile and error-prone.

---

## 2. Article Discovery: PubMed E-utilities API over CSV Filtering

**Decision:** Use the PubMed E-utilities ESearch API to find relevant articles by topic, rather than filtering the S3 CSV file list.

**Why:** The S3 CSV file list (`oa_comm.filelist.csv`) only contains: S3 key, ETag, brief article citation, AccessionID, last updated date, PMID, license, and retracted status. It has no titles and no abstracts — just a short citation string like "PLoS Biol. 2005 Apr 22; 3(4):e60". There is no way to filter by topic from this metadata alone. The best approaches we can do by going directly to the article base is randomly pick several articles or pick a consecutive list of articles sorted by their IDs, both of which are not reliable in giving articles relevant to the query.

**Tradeoff:** Adds an external API dependency (NCBI servers) and introduces rate limiting (3 requests/sec without API key). But the alternative — downloading the full CSV (~500MB+) and trying to keyword-match citation strings — would be both slow and inaccurate. E-utilities gives us PubMed's actual search index, which understands biomedical terminology, MeSH terms, and synonyms. (However, we found later that E-utilities API is not so good at processing natural language, whose fix will be addressed in the next decision)

---

## 3. Query Preprocessing: Stopword Removal for E-utilities

**Decision:** Add a preprocessing step that strips common stopwords from user queries before sending them to the E-utilities API.

**Why:** During testing, the natural-language query "Adverse events with mRNA vaccines in pediatrics" returned 0 results from E-utilities using the implementation decided in decision 2, while the keyword-style query "mRNA vaccine adverse events pediatric" returned 10,686 results. E-utilities performs exact term matching and doesn't handle natural language well; stopwords like "with", "in", "for" can interfere with search.

**Tradeoff:** Aggressive stopword removal could occasionally strip meaningful words (e.g., "in vitro" where "in" is part of a technical term). A more sophisticated approach would use NLP-based query parsing or PubMed's MeSH term mapping. For this project, simple stopword removal solves the immediate problem and is transparent to debug. We will keep testing if we need to implement more fixes.

---

## 4. Storage: JSON File (with SQLite as Future Migration)

**Decision:** Store parsed articles as a single `articles.json` file.

**Why:** For <100 articles, JSON is simple, human-readable, and easy to inspect during development. It requires no additional dependencies and works directly with Python's built-in `json` module.

**Tradeoff:** JSON doesn't support querying (e.g., "find all articles from 2023"), requires loading the entire file into memory, and doesn't handle concurrent writes. SQLite would add queryability (`SELECT * FROM articles WHERE pub_date > '2023'`) and scale better, but adds complexity for a small prototype. The plan is to migrate to SQLite once the pipeline is validated.

---

## 5. Embedding Strategy: Title + Abstract Combined

**Decision:** Embed `"{title}. {abstract}"` as a single string per article, rather than title-only or full-text.

**Why:** The title captures the main topic concisely. The abstract adds essential context about methods, results, and conclusions. Together they provide the best signal-to-noise ratio for semantic search.

**Tradeoff:** 
- Title-only would be faster but too shallow — many titles are vague or don't mention key terms.
- Full-text embedding would capture more detail but introduces noise (references, methods boilerplate, acknowledgments) and is much slower to process.
- Title + abstract is the standard approach in biomedical information retrieval for good reason.

---

## 6. Embedding Model: all-MiniLM-L6-v2 (General-Purpose)

**Decision:** Use `sentence-transformers/all-MiniLM-L6-v2` for generating embeddings.

**Why:** Recommended by Sanofi in the case study. It's lightweight (~80MB), CPU-friendly, produces 384-dimensional embeddings, and runs fast enough for interactive use. No GPU required.

**Tradeoff:** This is a general-purpose model trained on diverse text. A biomedical-specific model like `PubMedBERT` or `BioSentVec` would better understand domain terminology (e.g., knowing that "mAb" and "monoclonal antibody" are the same thing). However, domain-specific models are larger (~420MB+), slower on CPU, and the quality difference is marginal for a <100 article prototype. Probably improve afterwards.

---

## 7. Vector Store: ChromaDB over NumPy/FAISS

**Decision:** Use ChromaDB as the vector database.

**Why:** ChromaDB is free, open-source, runs locally as a Python library, and handles embedding storage, metadata storage, and similarity search in one integrated package. It also auto-generates embeddings when given an embedding function, reducing boilerplate code.

**Tradeoff:**
- A simple NumPy array + `cosine_similarity` from scikit-learn would work fine for <100 articles and has zero extra dependencies. But it doesn't persist data or handle metadata.
- FAISS (Facebook's library) is faster at scale but is a lower-level tool — you'd manage embeddings, metadata, and IDs separately.
- ChromaDB is overkill for <100 articles but demonstrates production patterns and would scale to thousands of articles without code changes.

---

## 8. Summarization Model: t5-small with Explicit Transformer Loading

**Decision:** Use `t5-small` for summarization, loaded explicitly via `T5Tokenizer` and `T5ForConditionalGeneration` rather than the `pipeline` shortcut.

**Why:** The explicit approach demonstrates understanding of the transformer inference pipeline: tokenization → encoding → generation → detokenization. Each step is visible in the code with comments explaining what's happening at the architectural level.

**Tradeoff:** The `pipeline("summarization", model="t5-small")` one-liner does the same thing in less code and is easier to read. The explicit approach adds ~5 extra lines but shows the interviewer that we understand what's happening under the hood — tokenizer converting text to IDs, encoder processing through self-attention layers, decoder generating output autoregressively, and detokenization back to text.

---

## 9. Summarization Quality: t5-small (Speed) over bart-large-cnn (Quality)

**Decision:** Use `t5-small` (60M parameters) instead of larger models like `facebook/bart-large-cnn` (400M parameters).

**Why:** Runs on CPU in seconds per article. Sanofi recommended it as CPU-friendly. Fast iteration during development.

**Tradeoff:** t5-small produces functional but generic summaries. It may miss nuances in biomedical text and occasionally produce choppy output. `bart-large-cnn` would produce noticeably better summaries but is 6x larger and slower on CPU. An LLM via RAG would be best but adds API costs and complexity. The current approach prioritizes a working prototype; summary quality is noted as the primary area for improvement.

---

## 10. Keyword Extraction: XML-First with Fallback

**Decision:** Use keywords from the XML `<kwd-group>` when available, fall back to simple frequency-based extraction when not.

**Why:** Author-provided keywords from the XML are curated and domain-accurate. They're free metadata that many articles include. The fallback handles articles that lack keyword tags.

**Tradeoff:** The frequency-based fallback is crude — it just finds repeated capitalized terms. A better fallback would use KeyBERT (embedding-based keyword extraction) or TF-IDF across the article corpus. But the XML keywords cover most articles, and the fallback is a reasonable placeholder that can be upgraded independently.

---


## Summary Table

| Decision | Chose | Over | Key Reason |
|----------|-------|------|------------|
| Data format | XML | TXT | Structured field extraction |
| Article discovery | E-utilities API | CSV filtering | CSV lacks titles/abstracts |
| Query handling | Stopword removal | Raw natural language | E-utilities needs keyword-style queries |
| Storage | JSON file | SQLite | Simplicity for prototype |
| Embedding input | Title + Abstract | Title-only / Full-text | Best signal-to-noise ratio |
| Embedding model | all-MiniLM-L6-v2 | PubMedBERT | CPU-friendly, recommended by Sanofi |
| Vector store | ChromaDB | NumPy / FAISS | Integrated solution, production patterns |
| Transformer usage | Explicit loading | Pipeline shortcut | Shows architectural understanding |
| Summarization model | t5-small | bart-large-cnn | CPU speed, fast iteration |
| Keywords | XML-first + fallback | Pure extraction | Author keywords are highest quality |
| Dev environment | VS Code + Jupyter ext | Separate JupyterLab | Single tool, no context-switching |