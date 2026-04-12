"""
FastAPI wrapper around the pipeline.
Run with: uvicorn api:app --reload
Docs at:  http://localhost:8000/docs
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from main import run_pipeline

app = FastAPI(
    title="BioMedReAct API",
    description="Biomedical literature review — search, retrieve, summarize.",
    version="0.1.0",
)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


# --- request / response models ---

class QueryRequest(BaseModel):
    query: str = Field(..., description="Research question in plain language")
    k: int = Field(default=5, ge=1, le=20, description="Number of articles to return")
    pool_size: int = Field(default=50, ge=5, le=200, description="Article pool to search")
    model: str = Field(default="t5-small", description="t5-small or facebook/bart-large-cnn")


class ArticleResponse(BaseModel):
    pmc_id: Optional[str] = None
    pmid: Optional[str] = None
    title: Optional[str] = None
    authors: list = []
    journal: Optional[str] = None
    pub_date: Optional[str] = None
    summary: Optional[str] = None
    keywords: list = []
    relevance_score: Optional[float] = None
    rouge_scores: dict = {}


class ReportResponse(BaseModel):
    query: str
    timestamp: str
    model: str
    num_results: int
    avg_rouge: dict = {}
    articles: list[ArticleResponse] = []


# --- endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=ReportResponse)
def query_pipeline(req: QueryRequest):
    """Run the full pipeline for a single query."""
    report = run_pipeline(
        query=req.query,
        k=req.k,
        pool_size=req.pool_size,
        model_name=req.model,
    )

    fname = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w") as f:
        json.dump(report, f, indent=2)

    return report


@app.get("/reports")
def list_reports():
    """List all saved report filenames."""
    files = sorted(REPORTS_DIR.glob("report_*.json"), reverse=True)
    return {"reports": [f.name for f in files]}


@app.get("/reports/{filename}")
def get_report(filename: str):
    """Retrieve a saved report by filename."""
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    with open(path) as f:
        return json.load(f)
