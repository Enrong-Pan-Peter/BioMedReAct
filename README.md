# BioMedReAct

A pipeline for finding and summarizing biomedical papers. You give it a research question (e.g. "adverse events with mRNA vaccines in pediatrics"), and it searches PubMed Central, pulls full-text articles from the open-access subset, ranks them by relevance, and produces short summaries with keywords.

Useful when you need a quick overview of the literature on a topic without manually sifting through dozens of abstracts. Everything runs locally — no API keys, no cloud setup. First run downloads the models (~300MB total); after that it's cached.

---

## Setup

Python 3.9 or newer. Create a virtual environment if you like, then:

```bash
pip install -r requirements.txt
```

That pulls boto3 (S3), requests, lxml, chromadb, sentence-transformers, transformers, torch, pandas, and jupyter. Expect a few minutes on first install.

---

## Usage

### CLI (recommended)

```bash
python main.py
```

You'll be asked for:
- **Query** — your research question in plain language
- **K** — how many articles to return (default 5)
- **Pool size** — how many articles to search and rank from (default 50). Larger = more options but slower.

The pipeline runs: search PMC → download XML from S3 → parse metadata → build semantic index → retrieve top K → summarize with T5. Each step shows a spinner. Results print to the terminal and are saved under `reports/report_YYYYMMDD_HHMMSS.json`. You can run another query when done or exit.

### Notebook

Open `notebook.ipynb` in VS Code (Jupyter extension) or JupyterLab. Run cells in order. The notebook uses a batch workflow: it searches three fixed queries, pools the articles, then runs retrieval and summarization for each. Good for exploring the pipeline step by step or comparing multiple queries at once.

---

## Output

Each report includes for each article: title, PMC/PMID IDs, journal, date, relevance score, a 2–3 sentence summary, and keywords. JSON files are plain text — you can open them in any editor or load them into another script.

---

## Project layout

- `main.py` — CLI entrypoint
- `notebook.ipynb` — step-by-step demo
- `agents/` — retriever and summarizer
- `utils/` — search, fetch, parse, spinner
- `reports/` — generated JSON reports
- `TradeOffDiscussion.md` — design choices and tradeoffs
