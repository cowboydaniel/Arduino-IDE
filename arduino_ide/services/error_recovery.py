"""Helpers for turning compiler errors into actionable advice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class ErrorSuggestion:
    """Container describing a potential fix for a compiler error."""

    issue: str
    suggestions: List[str]
    confidence: float

    def __post_init__(self) -> None:
        # Ensure we always store a copy so callers can't mutate internals
        self.suggestions = list(self.suggestions)


class SmartErrorRecovery:
    """Analyze compiler output and return friendly recovery hints."""

    def __init__(self) -> None:
        self._common_fixes: Dict[str, Sequence[str]] = {
            "missing semicolon": ["Add ; at end of line"],
            "undeclared identifier": [
                "Did you forget to #include?",
                "Check spelling",
                "Variable out of scope",
            ],
            "not enough memory": [
                "Use PROGMEM for constants",
                "Reduce buffer sizes",
                "Optimize String usage",
            ],
        }
        self._fallback_suggestions = [
            "Double-check the line referenced in the compiler output",
            "Search the Arduino documentation for the exact error text",
        ]

    def analyze_compile_error(self, error_msg: str) -> List[ErrorSuggestion]:
        """Return human friendly hints for ``error_msg``.

        Args:
            error_msg: Raw text emitted by the compiler

        Returns:
            A list of :class:`ErrorSuggestion` objects.  Suggestions are ordered
            by match confidence and will include a generic fallback when no
            known patterns are matched.
        """

        normalized = (error_msg or "").lower()
        suggestions: List[ErrorSuggestion] = []

        for needle, fixes in self._common_fixes.items():
            if needle in normalized:
                suggestions.append(
                    ErrorSuggestion(
                        issue=needle,
                        suggestions=list(fixes),
                        confidence=self._confidence_for_match(needle, normalized),
                    )
                )

        if not suggestions:
            suggestions.append(
                ErrorSuggestion(
                    issue="unknown",
                    suggestions=self._fallback_suggestions,
                    confidence=0.2,
                )
            )

        return suggestions

    @staticmethod
    def _confidence_for_match(needle: str, haystack: str) -> float:
        """Derive a simple confidence score for a substring match."""

        if not needle:
            return 0.0
        coverage = haystack.count(needle)
        base = 0.5 + min(len(needle) / 40.0, 0.4)
        return min(1.0, base + (coverage - 1) * 0.05)
