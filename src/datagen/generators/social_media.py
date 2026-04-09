"""Generator for social media posts."""

from __future__ import annotations

import json

from datagen.generators.base import BaseGenerator


class SocialMediaGenerator(BaseGenerator):
    """Generates synthetic social media post records."""

    category_name = "social_media"
    id_prefix = "SM"

    def get_count(self) -> int:
        return self.config.categories.social_media.count

    def build_prompt(self, batch_index: int, batch_size: int, offset: int) -> str:
        cfg = self.config.categories.social_media
        return f"""Generate exactly {batch_size} synthetic social media posts about the
{self.context} and its monetary policy decisions.

Each record must be a JSON object with these fields:
- "id": string, format "SM-XXXXX" starting from SM-{offset + 1:05d}
- "platform": one of {json.dumps(cfg.platforms)}
- "author_type": one of {json.dumps(cfg.author_types)}
- "author_handle": string, a realistic social media handle/username
- "text": string, the post content (platform-appropriate length and style)
- "sentiment": one of {json.dumps(cfg.sentiments)}
- "sentiment_score": float between -1.0 (very negative) and 1.0 (very positive)
- "topic": one of {json.dumps(cfg.topics)}
- "engagement_score": integer, realistic engagement count (likes/upvotes)
- "reply_count": integer, number of replies
- "repost_count": integer, number of reposts/retweets
- "timestamp": ISO 8601 datetime between {self.date_start} and {self.date_end}
- "hashtags": list of strings, relevant hashtags used

Requirements:
- Twitter posts: max 280 chars, use hashtags, casual to professional tone
- Reddit posts: longer, more detailed analysis, subreddit-style (r/economics, r/finance)
- LinkedIn posts: professional tone, longer form, industry perspective
- Journalists: factual, breaking news style
- Financial analysts: data-driven, technical language
- Economists: academic perspective, referencing economic theories
- Public: everyday language, expressing concerns or opinions about the economy
- Sentiment should be realistic and varied:
  - Positive: praising Fed decisions, optimism about economy
  - Negative: criticizing rate hikes, inflation concerns, recession fears
  - Neutral: factual reporting, asking questions
- Reference specific Fed events: FOMC meetings, rate decisions, Fed chair speeches,
  employment reports, CPI data releases
- Batch {batch_index + 1}: ensure diversity in topics and sentiments

Return a JSON array of {batch_size} objects. No other text."""

    def get_system_prompt(self) -> str:
        return (
            "You are a synthetic data generator creating realistic social media posts about "
            f"the {self.context}. "
            "Generate posts that reflect real public discourse about Federal Reserve monetary policy, "
            "interest rate decisions, inflation, and economic conditions. "
            "Posts should vary by platform style, author expertise level, and sentiment. "
            "Include realistic hashtags, engagement metrics, and platform-appropriate formatting. "
            "Return ONLY a valid JSON array."
        )
