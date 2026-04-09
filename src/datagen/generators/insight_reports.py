"""Generator for communication insight report records."""

from __future__ import annotations

import json

from datagen.generators.base import BaseGenerator


class InsightReportGenerator(BaseGenerator):
    """Generates synthetic communication insight report records."""

    category_name = "insight_reports"
    id_prefix = "RPT"

    def get_count(self) -> int:
        return self.config.categories.insight_reports.count

    def build_prompt(self, batch_index: int, batch_size: int, offset: int) -> str:
        cfg = self.config.categories.insight_reports
        return f"""Generate exactly {batch_size} synthetic communication insight report records
for the {self.context} communications team.

Each record must be a JSON object with these fields:
- "id": string, format "RPT-XXXXX" starting from RPT-{offset + 1:05d}
- "report_type": one of {json.dumps(cfg.report_types)}
- "report_title": string, descriptive title for the report
- "report_date": ISO 8601 date between {self.date_start} and {self.date_end}
- "period_start": ISO 8601 date, start of the reporting period
- "period_end": ISO 8601 date, end of the reporting period
- "executive_summary": string, 2-3 sentence high-level summary
- "trending_topics": list of objects, each with:
  - "topic": string, the topic name
  - "mention_count": integer, number of mentions
  - "trend_direction": one of ["rising", "falling", "stable"]
  - "sentiment_breakdown": object with "positive", "negative", "neutral" as integer percentages
- "sentiment_summary": object with:
  - "overall_sentiment": one of ["positive", "negative", "neutral", "mixed"]
  - "average_score": float between -1.0 and 1.0
  - "total_analyzed": integer, number of items analyzed
  - "positive_pct": float, percentage positive
  - "negative_pct": float, percentage negative
  - "neutral_pct": float, percentage neutral
- "risk_alerts": list of objects, each with:
  - "risk_level": one of ["high", "medium", "low"]
  - "description": string, description of the risk
  - "source": string, where the risk was identified
  - "recommended_action": string, suggested response
- "volume_stats": object with:
  - "total_inquiries": integer
  - "total_social_mentions": integer
  - "total_news_articles": integer
  - "change_from_previous": float, percentage change
- "key_findings": list of strings, 3-5 key findings
- "recommendations": list of strings, 2-4 actionable recommendations
- "generated_by": "AI Communications Insight System"

Requirements:
- Reports should reflect realistic Federal Reserve communications monitoring:
  - Track public sentiment around FOMC decisions
  - Monitor media coverage of rate changes
  - Identify communication risks from conflicting Fed messaging
  - Analyze public concerns about inflation and employment
- Report types should have appropriate scope:
  - daily_summary: narrow focus, current events
  - weekly_analysis: broader trends, week-over-week changes
  - monthly_trend: macro trends, longer-term patterns
  - incident_report: specific communication crisis or issue
  - risk_assessment: forward-looking risk identification
- Trending topics should reference real Fed-related topics
- Risk alerts should identify realistic PR/communication risks
- Volume stats should be proportional to report type scope
- Recommendations should be actionable and specific
- Batch {batch_index + 1}: vary report types and time periods

Return a JSON array of {batch_size} objects. No other text."""

    def get_system_prompt(self) -> str:
        return (
            "You are a synthetic data generator creating realistic communication insight reports "
            f"for the {self.context} communications team. "
            "Generate comprehensive reports that a central bank's communications monitoring system "
            "would produce, including sentiment analysis, trending topics, risk alerts, and "
            "actionable recommendations. Reports should reflect real-world Federal Reserve "
            "communication challenges and public discourse patterns. "
            "Return ONLY a valid JSON array."
        )
