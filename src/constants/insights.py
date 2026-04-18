OUTSIDE_LLM_TOP_N_SUMMARY = "LLM not applied (outside top trends)"

INCOHERENT_TOPIC_INSIGHT_RESPONSE = {
    "summary": (
        "This cluster shows mixed or weakly connected signals, so no reliable "
        "marketing theme was identified."
    ),
    "campaign_angle": "",
    "suggested_subject": "",
    "email_hook": "",
    "marketing_safe": False,
}

FRAGMENTED_TOPIC_INSIGHT_RESPONSE = {
    "summary": (
        "This trend shows high engagement across diverse content without a "
        "single clear theme. It reflects broad audience interest but "
        "fragmented topics, making it less suitable for targeted marketing "
        "campaigns."
    ),
    "campaign_angle": "",
    "suggested_subject": "",
    "email_hook": "",
    "marketing_safe": False,
}

EMPTY_CAMPAIGN_COPY = {
    "campaign_angle": "",
    "suggested_subject": "",
    "email_hook": "",
}
