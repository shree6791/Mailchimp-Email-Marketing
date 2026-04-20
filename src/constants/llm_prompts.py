"""
Trend-insight **data only**: prompt template, JSON schema, fallback payload, key names.

No functions here—treat this like a config module. Small helpers that assemble API
calls from these values live in ``insight_generator.py``.
"""

TREND_INSIGHT_OUTPUT_KEYS: tuple[str, ...] = (
    "summary",
    "campaign_angle",
    "suggested_subject",
    "email_hook",
    "marketing_safe",
)

TREND_INSIGHT_PROMPT_TEMPLATE = """
You generate grounded marketing insights for a Mailchimp-style trend engine.

Return ONLY valid JSON with these keys:
- summary
- campaign_angle
- suggested_subject
- email_hook
- marketing_safe

Inputs:
- topic_keywords: {topic_keywords}
- sample_titles: {sample_titles}
- trend_type: {trend_type}
- avg_views: {avg_views}
- avg_likes: {avg_likes}
- momentum: {momentum}
- avg_proxy_ctr_recency: {avg_proxy_ctr_recency}

Rules:
1. Use only the provided inputs.
2. If a claim cannot be directly supported by topic_keywords or sample_titles, do not include it.
3. Do not invent specific shows, products, events, controversies, relationships, or storylines.
4. Treat names as context, not the main theme unless clearly dominant across multiple keywords or multiple sample_titles.
5. Do not force categories such as tech, business, politics, or social impact unless clearly supported.
6. Do not treat a single sample title detail as the theme of the whole cluster unless it is also supported by multiple keywords or multiple sample_titles.
7. When evidence is mixed, prefer a broader category-level summary over a specific storyline.
8. Do not generalize into societal, economic, health, or abstract themes unless clearly supported by multiple keywords or multiple sample_titles.
9. Do not translate entertainment, creator, or celebrity content into business, technology, or platform strategy language unless those concepts are directly supported.
10. Focus on the most dominant and repeated signals in the keywords, and ignore weak or isolated tokens.
11. Prefer the simplest directly supported interpretation of the cluster.
12. If the topic is not suitable for generic marketing, write a neutral summary, leave other fields empty, and set marketing_safe = false.
13. Use avg_proxy_ctr_recency only as an engagement-intensity hint (high/medium/low); do not mention raw numbers.

If suitable for marketing:
14. Keep the summary to at most 2 sentences.
15. Make the summary grounded, conservative, and cluster-level rather than title-level.
16. suggested_subject must be 4 to 9 words, concise, and specific.
17. campaign_angle must be practical and actionable.
18. email_hook must be engaging but not generic.
19. Avoid overusing celebrity names unless essential to the theme.

Momentum:
20. If momentum > 0.5, frame as emerging or fast-rising.
21. If -0.2 <= momentum <= 0.5, frame as steady or active.
22. If momentum < -0.2, frame as cooling but still engaged if views/likes are high.

Output JSON only.
"""

TREND_INSIGHT_JSON_SCHEMA_NAME = "trend_insight"

TREND_INSIGHT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "campaign_angle": {"type": "string"},
        "suggested_subject": {"type": "string"},
        "email_hook": {"type": "string"},
        "marketing_safe": {"type": "boolean"},
    },
    "required": list(TREND_INSIGHT_OUTPUT_KEYS),
    "additionalProperties": False,
}

TREND_INSIGHT_FALLBACK_RESPONSE = {
    "summary": "Unable to generate summary.",
    "campaign_angle": "",
    "suggested_subject": "",
    "email_hook": "",
    "marketing_safe": False,
}
