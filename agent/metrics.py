"""Tracks LLM usage for a run so it can be written to `runs_meta` (spec section 7's
gemini_calls/tokens_used columns existed in the schema but nothing populated them)."""

from dataclasses import dataclass


@dataclass
class RunMetrics:
    gemini_calls: int = 0
    groq_calls: int = 0
    tokens_used: int = 0

    def record_gemini(self, tokens: int = 0) -> None:
        self.gemini_calls += 1
        self.tokens_used += tokens

    def record_groq(self, tokens: int = 0) -> None:
        self.groq_calls += 1
        self.tokens_used += tokens
