"""
Summarizer agent — T5-small for abstract summarization.
"""

import re
from collections import Counter
from typing import Any, Dict, List

import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer


class SummarizerAgent:
    def __init__(self, model_name: str = "t5-small"):
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.model.eval()

    def summarize(self, article: Dict[str, Any]) -> Dict[str, Any]:
        abstract = article.get("abstract", "")

        if not abstract or len(abstract.split()) < 20:
            summary = abstract
        else:
            inp = f"summarize: {abstract}"
            tok = self.tokenizer(inp, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                out_ids = self.model.generate(
                    input_ids=tok["input_ids"],
                    attention_mask=tok["attention_mask"],
                    max_length=100,
                    min_length=30,
                    num_beams=4,
                    early_stopping=True,
                    no_repeat_ngram_size=2,
                )
            summary = self.tokenizer.decode(out_ids[0], skip_special_tokens=True)

        keywords = article.get("keywords", [])
        if not keywords:
            keywords = self._extract_keywords(abstract)

        return {**article, "summary": summary, "extracted_keywords": keywords}

    def summarize_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.summarize(a) for a in articles]

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 5) -> List[str]:
        words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        cnt = Counter(words)
        return [w for w, _ in cnt.most_common(top_n)]
