from src.constants.topic_display import (
    DEFAULT_FALLBACK_TITLE,
    DEFAULT_FRAGMENTED_TITLE,
    FALLBACK_TITLE_BY_TREND_TYPE,
    FRAGMENTED_TITLE_BY_TREND_TYPE,
    THEME_STRONG_MATCH_MIN,
    TOPIC_THEME_RULES,
)


class TopicNamer:
    @staticmethod
    def _score_theme(keywords: set[str], rule_keywords: frozenset[str]) -> int:
        return len(keywords & rule_keywords)

    def name_topic(
        self,
        keywords: list[str],
        trend_type: str,
        fragmented_trend: bool = False,
    ) -> str:
        normalized = {
            str(k).strip().lower()
            for k in keywords
            if k and str(k).strip()
        }

        if fragmented_trend:
            return FRAGMENTED_TITLE_BY_TREND_TYPE.get(
                trend_type, DEFAULT_FRAGMENTED_TITLE
            )

        best_name: str | None = None
        best_score = 0

        for name, rule_keywords in TOPIC_THEME_RULES:
            score = self._score_theme(normalized, rule_keywords)
            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score >= THEME_STRONG_MATCH_MIN:
            return best_name

        if best_name and best_score == 1:
            return best_name.replace("&", "").strip()

        return FALLBACK_TITLE_BY_TREND_TYPE.get(trend_type, DEFAULT_FALLBACK_TITLE)
