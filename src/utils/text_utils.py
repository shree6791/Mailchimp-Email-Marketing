import math
import re
import pandas as pd


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def parse_tags(tags: str) -> str:
    raw = safe_text(tags).strip()
    if not raw or raw.lower() == "[none]":
        return ""
    raw = raw.strip('"')
    return raw.replace("|", " ")


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_document(row: pd.Series, use_description: bool = False) -> str:
    parts = [
        safe_text(row.get("title", "")),
        parse_tags(safe_text(row.get("tags", ""))),
    ]

    if use_description:
        parts.append(safe_text(row.get("description", "")))

    return clean_whitespace(" ".join(part for part in parts if part))