"""Human-readable topic titles from keywords and trend_type."""

# (display name, keyword set for scoring overlap)
TOPIC_THEME_RULES: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "Vintage & Everyday Fashion",
        frozenset(
            {
                "fashion",
                "outfit",
                "dress",
                "clothe",
                "style",
                "wardrobe",
                "look",
            }
        ),
    ),
    (
        "Beauty & Hair Trends",
        frozenset(
            {"beauty", "hair", "makeup", "skin", "routine", "skincare"}
        ),
    ),
    (
        "Consumer Tech & Vehicles",
        frozenset(
            {
                "iphone",
                "apple",
                "pixel",
                "surface",
                "tesla",
                "roadster",
                "truck",
                "semi",
                "robot",
                "ai",
            }
        ),
    ),
    (
        "Music & Artist Buzz",
        frozenset(
            {
                "music",
                "song",
                "acoustic",
                "album",
                "video",
                "swift",
                "beyonce",
                "gomez",
                "selena",
                "marshmello",
                "paramore",
                "twice",
            }
        ),
    ),
    (
        "Late-Night Comedy Clips",
        frozenset(
            {
                "late",
                "corden",
                "colbert",
                "fallon",
                "jimmy",
                "snl",
                "joke",
                "letterman",
                "lawrence",
            }
        ),
    ),
    (
        "Food & Street Food Trends",
        frozenset(
            {
                "food",
                "recipe",
                "steak",
                "pizza",
                "chef",
                "cook",
                "kitchen",
                "cream",
                "cheese",
                "ice",
                "roll",
            }
        ),
    ),
    (
        "Comics & Film Storytelling",
        frozenset(
            {
                "comic",
                "comix",
                "film",
                "movie",
                "trailer",
                "maus",
                "spiegelman",
                "pacific",
                "rim",
            }
        ),
    ),
    (
        "Creator Q&A & Interviews",
        frozenset({"question", "interview", "ask", "answer"}),
    ),
    (
        "Toys & Retro Gaming",
        frozenset({"toy", "gameboy", "game", "retro", "unbox"}),
    ),
)

FRAGMENTED_TITLE_BY_TREND_TYPE: dict[str, str] = {
    "entertainment": "Fragmented Entertainment Buzz",
    "beauty_lifestyle": "Fragmented Fashion & Beauty",
    "technology": "Fragmented Tech Buzz",
    "food": "Fragmented Food Content",
}

DEFAULT_FRAGMENTED_TITLE = "Fragmented Viral Content"

FALLBACK_TITLE_BY_TREND_TYPE: dict[str, str] = {
    "beauty_lifestyle": "Fashion & Lifestyle Trend",
    "technology": "Technology & Innovation",
    "entertainment": "Entertainment Content",
    "food": "Food & Dining Trend",
    "seasonal": "Seasonal Interest",
}

DEFAULT_FALLBACK_TITLE = "General Viral Trend"

THEME_STRONG_MATCH_MIN = 2
