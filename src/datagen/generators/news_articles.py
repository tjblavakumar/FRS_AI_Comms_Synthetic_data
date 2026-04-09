"""Generator for news article records."""

from __future__ import annotations

import json

from datagen.generators.base import BaseGenerator


class NewsArticleGenerator(BaseGenerator):
    """Generates synthetic news article records."""

    category_name = "news_articles"
    id_prefix = "NEWS"

    def get_count(self) -> int:
        return self.config.categories.news_articles.count

    def build_prompt(self, batch_index: int, batch_size: int, offset: int) -> str:
        cfg = self.config.categories.news_articles
        return f"""Generate exactly {batch_size} synthetic news article records about the
{self.context} and its monetary policy decisions.

Each record must be a JSON object with these fields:
- "id": string, format "NEWS-XXXXX" starting from NEWS-{offset + 1:05d}
- "source": one of {json.dumps(cfg.sources)}
- "headline": string, a realistic news headline
- "snippet": string, a 1-2 sentence article summary/lead paragraph
- "full_text": string, the full article body (3-6 paragraphs of realistic financial journalism)
- "author": string, a realistic journalist name
- "sentiment": one of {json.dumps(cfg.sentiments)}
- "sentiment_score": float between -1.0 and 1.0
- "topics": list of strings from {json.dumps(cfg.topics)}, 1-3 topics per article
- "entities_mentioned": list of strings, key entities mentioned (people, institutions, economic indicators)
- "risk_flag": boolean, true if the article identifies potential communication risks
- "risk_description": string or null, description of the risk if risk_flag is true
- "published_date": ISO 8601 datetime between {self.date_start} and {self.date_end}
- "word_count": integer, approximate word count of full_text

Requirements:
- Headlines should follow real financial journalism conventions
- Articles should reference real Federal Reserve topics:
  - FOMC meeting outcomes and forward guidance
  - Federal funds rate changes (hikes during 2022-2023, potential cuts in 2024-2025)
  - Inflation data (CPI, PCE) and the Fed's 2% target
  - Employment reports and the dual mandate
  - Quantitative tightening and balance sheet reduction
  - Banking supervision and financial stability
  - Fed chair speeches and congressional testimony
  - FRBSF research and regional economic analysis
- Risk-flagged articles should identify potential PR challenges:
  - Contradictory messaging from Fed officials
  - Public backlash against rate decisions
  - Controversial policy positions
  - Misinformation about Fed operations
- Source-appropriate writing styles (Bloomberg: data-heavy; WSJ: analytical; Reuters: factual)
- Batch {batch_index + 1}: diversify topics and time periods

Return a JSON array of {batch_size} objects. No other text."""

    def get_system_prompt(self) -> str:
        return (
            "You are a synthetic data generator creating realistic financial news articles about "
            f"the {self.context}. "
            "Generate articles that mirror real financial journalism covering Federal Reserve "
            "monetary policy, interest rates, inflation, and economic conditions between 2022-2025. "
            "Articles should be source-appropriate in style and tone. "
            "Include realistic risk flags for articles that could pose communication challenges. "
            "Return ONLY a valid JSON array."
        )
