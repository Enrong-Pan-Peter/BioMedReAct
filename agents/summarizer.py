"""
Summarizer agent — T5-small or BART-large-CNN for abstract summarization.
Includes ROUGE scoring against the original abstract.
"""

import re
from collections import Counter
from typing import Any, Dict, List

import torch
from rouge_score import rouge_scorer
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
)

_rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

# generation defaults per model family
_T5_DEFAULTS = dict(max_length=100, min_length=30, num_beams=4, early_stopping=True, no_repeat_ngram_size=2)
_BART_DEFAULTS = dict(max_length=150, min_length=40, num_beams=4, length_penalty=2.0, no_repeat_ngram_size=3)


class SummarizerAgent:
    def __init__(self, model_name: str = "t5-small"):
        self.model_name = model_name
        self.is_t5 = "t5" in model_name.lower()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.eval()
        self._gen_kwargs = dict(_T5_DEFAULTS) if self.is_t5 else dict(_BART_DEFAULTS)

    def summarize(self, article: Dict[str, Any]) -> Dict[str, Any]:
        abstract = article.get("abstract", "")

        if not abstract or len(abstract.split()) < 20:
            summary = abstract
        else:
            input_text = f"summarize: {abstract}" if self.is_t5 else abstract
            max_input = 512 if self.is_t5 else 1024
            tok = self.tokenizer(input_text, return_tensors="pt", truncation=True, max_length=max_input)
            with torch.no_grad():
                out_ids = self.model.generate(
                    input_ids=tok["input_ids"],
                    attention_mask=tok["attention_mask"],
                    **self._gen_kwargs,
                )
            summary = self.tokenizer.decode(out_ids[0], skip_special_tokens=True)

        summary = self._postprocess(summary)

        # ROUGE against original abstract
        rouge_scores = self._compute_rouge(abstract, summary)

        keywords = article.get("keywords", [])
        if not keywords:
            keywords = self._extract_keywords(abstract)

        return {
            **article,
            "summary": summary,
            "extracted_keywords": keywords,
            "rouge_scores": rouge_scores,
        }

    def summarize_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.summarize(a) for a in articles]

    @staticmethod
    def _postprocess(text: str) -> str:
        """Capitalize sentences, fix spacing, ensure trailing period."""
        text = " ".join(text.split())  # collapse whitespace
        if not text:
            return text
        text = text[0].upper() + text[1:]
        # capitalize after sentence-ending punctuation
        result = []
        cap_next = False
        for ch in text:
            if cap_next and ch.isalpha():
                result.append(ch.upper())
                cap_next = False
            else:
                result.append(ch)
            if ch in ".!?":
                cap_next = True
        text = "".join(result)
        if text and text[-1] not in ".!?":
            text += "."
        return text

    @staticmethod
    def _compute_rouge(reference: str, hypothesis: str) -> Dict[str, float]:
        if not reference or not hypothesis:
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
        scores = _rouge.score(reference, hypothesis)
        return {
            "rouge1": round(scores["rouge1"].fmeasure, 4),
            "rouge2": round(scores["rouge2"].fmeasure, 4),
            "rougeL": round(scores["rougeL"].fmeasure, 4),
        }

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 5) -> List[str]:
        words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        cnt = Counter(words)
        return [w for w, _ in cnt.most_common(top_n)]
