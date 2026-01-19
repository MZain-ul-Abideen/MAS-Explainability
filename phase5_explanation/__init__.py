"""
Phase 5: Explanation Generation Module
Generates natural language explanations using LLM.
"""

from .explainer import Explainer, generate_explanation, Explanation

__all__ = [
    'Explainer',
    'generate_explanation',
    'Explanation',
]