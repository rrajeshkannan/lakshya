"""Clean scheme identity for LPS.

MFAPI catalog rows may carry a raw ``schemeCategory`` code. LPS keeps the
scheme name and replaces that code with ``asset_class`` and ``is_elss``.
"""

from __future__ import annotations


_CATEGORY_FIELDS = ("schemeCategory", "scheme_category")


def scheme_record(metadata: dict | None) -> dict:
    """Return scheme metadata without a raw category code.

    An empty payload stays empty. A category value is removed and recorded
    as ``asset_class`` and ``is_elss`` when those attributes are not already
    present.
    """
    if not metadata:
        return {}
    record = dict(metadata)
    category = ""
    for field in _CATEGORY_FIELDS:
        value = record.pop(field, None)
        if value and not category:
            category = str(value).strip()
    if category and "asset_class" not in record:
        asset_class, is_elss = scheme_class(category)
        record["asset_class"] = asset_class
        record["is_elss"] = is_elss
    return record


def scheme_class(category: str) -> tuple[str, bool]:
    """Map a source category string to ``(asset_class, is_elss)``."""
    text = category.strip().lower()
    if "elss" in text:
        return "equity", True
    if "debt" in text:
        return "debt", False
    if "equity" in text:
        return "equity", False
    if not text:
        return "unknown", False
    return "other", False


__all__ = ["scheme_class", "scheme_record"]
