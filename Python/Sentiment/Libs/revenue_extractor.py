"""
Compatibility shim: older imports may reference
`Python.Sentiment.Libs.revenue_extractor`.

Re-export the public API from `revenue`.
"""

from .revenue import collect_recent_years, derive_quarters_from_reports

__all__ = [
    "collect_recent_years",
    "derive_quarters_from_reports",
]

