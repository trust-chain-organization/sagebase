"""Evaluation module for LLM performance testing

This module provides functionality to evaluate LLM outputs against predefined test cases
for different tasks such as minutes division, speaker matching, party member extraction,
and conference member matching.
"""

from .metrics import EvaluationMetrics, MetricsCalculator
from .runner import EvaluationRunner


__all__ = [
    "EvaluationRunner",
    "EvaluationMetrics",
    "MetricsCalculator",
]
