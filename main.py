from dotenv import load_dotenv

from src.config.settings import Settings
from src.pipeline.trend_engine import TrendPipelineEngine


def main() -> None:
    load_dotenv()

    settings = Settings()
    engine = TrendPipelineEngine(settings)

    _, topic_insights_df = engine.run()

    print("\nTop Trends\n" + "=" * 60)

    for _, row in topic_insights_df.head(settings.top_n_topics_to_show).iterrows():
        suggestion = row["campaign_copy"]

        print("\n" + "=" * 60)
        print(f"Trend: {row['topic_label']}")
        print(f"Trend Score: {row['trend_score']:.2f}")
        print(f"Volume: {int(row['volume'])}")
        print(f"Avg Views: {int(row['avg_views']):,}")
        print(f"Avg Likes: {int(row['avg_likes']):,}")
        print(f"Momentum: {row['momentum']:.2f}")

        print("\nSummary:")
        print(row["summary"])

        print("\nCampaign copy:")
        print(f"  Suggested Subject: {suggestion['suggested_subject']}")
        print(f"  Campaign Angle: {suggestion['campaign_angle']}")
        print(f"  Email Hook: {suggestion['email_hook']}")


if __name__ == "__main__":
    main()