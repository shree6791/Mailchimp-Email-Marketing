"""Smoke tests for ``_key_phrases_for_details`` (topic vs dominant keyword merge)."""

import pandas as pd

from src.serving.streamlit.components import _key_phrases_for_details


def test_identical_topic_and_dominant_returns_single_line() -> None:
    row = pd.Series(
        {
            "topic_label": "music, official, video",
            "dominant_topic_keywords": ["music", "official", "video"],
        }
    )
    out = _key_phrases_for_details(row)
    assert out == "music, official, video"


def test_subset_returns_longer_list() -> None:
    row = pd.Series(
        {
            "topic_label": "music, official",
            "dominant_topic_keywords": ["music", "official", "video", "acoustic"],
        }
    )
    out = _key_phrases_for_details(row)
    assert out is not None
    assert "acoustic" in out


def test_disjoint_lists_joined_with_middle_dot() -> None:
    row = pd.Series(
        {
            "topic_label": "a, b",
            "dominant_topic_keywords": ["c", "d"],
        }
    )
    out = _key_phrases_for_details(row)
    assert out == "a, b · c, d"


def test_overlap_high_jaccard_merges_to_sorted_union() -> None:
    row = pd.Series(
        {
            "topic_label": "music, official, video, acoustic, camila",
            "dominant_topic_keywords": ["music", "official", "acoustic", "camila", "harmony"],
        }
    )
    out = _key_phrases_for_details(row)
    assert out is not None
    assert "harmony" in out and "video" in out
    assert " · " not in out
