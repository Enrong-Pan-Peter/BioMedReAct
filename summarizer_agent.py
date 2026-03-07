"""
Step 6 — Summarizer Agent

Thought process: We need to condense article abstracts into 2-3 sentence summaries for
the report. T5-small (60M parameters) is CPU-friendly and runs in seconds. We load the
tokenizer and model explicitly (not the pipeline shortcut) to demonstrate understanding
of the transformer inference pipeline: tokenization → encoding → generation → detokenization.
T5 uses text prefixes ("summarize:") to determine the task. Keywords: prefer XML-extracted
from article metadata; fall back to frequency-based extraction when missing.
"""

import re
from collections import Counter
from typing import Any, Dict, List

import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer


class SummarizerAgent:
    """Summarizes article abstracts using T5-small with explicit transformer loading."""

    def __init__(self, model_name: str = "t5-small"):
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.model.eval()

    def summarize(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize a single article.

        Input: article dict from RetrieverAgent (must have 'abstract' key)
        Output: same dict with 'summary' and 'extracted_keywords' added
        """
        abstract = article.get("abstract", "")

        if not abstract or len(abstract.split()) < 20:
            summary = abstract
        else:
            input_text = f"summarize: {abstract}"
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                output_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_length=100,
                    min_length=30,
                    num_beams=4,
                    early_stopping=True,
                    no_repeat_ngram_size=2,
                )
            summary = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

        keywords = article.get("keywords", [])
        if not keywords:
            keywords = self._extract_keywords(abstract)

        return {**article, "summary": summary, "extracted_keywords": keywords}

    def summarize_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Summarize a list of articles."""
        return [self.summarize(a) for a in articles]

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 5) -> List[str]:
        """
        Fallback when XML keywords are missing.
        Extracts most frequent capitalized multi-word terms.
        """
        words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        counts = Counter(words)
        return [w for w, _ in counts.most_common(top_n)]
