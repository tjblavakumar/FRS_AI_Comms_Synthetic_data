"""Generator for response template records."""

from __future__ import annotations

import json

from datagen.generators.base import BaseGenerator


class ResponseTemplateGenerator(BaseGenerator):
    """Generates synthetic response template records."""

    category_name = "response_templates"
    id_prefix = "RT"

    def get_count(self) -> int:
        return self.config.categories.response_templates.count

    def build_prompt(self, batch_index: int, batch_size: int, offset: int) -> str:
        cfg = self.config.categories.response_templates
        return f"""Generate exactly {batch_size} synthetic response template records for the
{self.context} communications team.

Each record must be a JSON object with these fields:
- "id": string, format "RT-XXXXX" starting from RT-{offset + 1:05d}
- "inquiry_category": one of {json.dumps(cfg.inquiry_categories)}
- "inquiry_example": string, a brief example of the type of inquiry this template responds to
- "template_subject": string, the subject line for the response
- "template_body": string, the full response template text (2-4 paragraphs, professional tone)
- "tone": one of {json.dumps(cfg.tones)}
- "placeholders": list of strings, template variables like "{{sender_name}}", "{{date}}", "{{specific_topic}}"
- "approval_status": one of ["approved", "pending_review", "draft"]
- "last_updated": ISO 8601 datetime between {self.date_start} and {self.date_end}
- "usage_count": integer, how many times this template has been used
- "category_tags": list of strings, relevant tags for searchability
- "target_audience": one of ["media", "public", "stakeholder", "congressional", "general"]

Requirements:
- Templates should reflect actual Federal Reserve communication standards:
  - Formal, precise language avoiding market-moving statements
  - Appropriate disclaimers about forward-looking statements
  - References to official Fed resources and publications
  - Compliance with FOIA requirements where applicable
- Template types should include:
  - Standard acknowledgment of receipt
  - Detailed policy explanations (interest rates, inflation targets)
  - Media inquiry responses with approved talking points
  - Congressional inquiry responses (formal, detailed)
  - Public concern responses (empathetic but factual)
  - FOIA request handling templates
  - Speaking engagement request responses
- Use realistic placeholders: {{{{sender_name}}}}, {{{{inquiry_date}}}}, {{{{specific_topic}}}},
  {{{{relevant_publication}}}}, {{{{contact_person}}}}, {{{{reference_number}}}}
- Vary approval statuses realistically (most approved, some in review)
- Higher usage_count for common template types
- Batch {batch_index + 1}: ensure variety across inquiry categories and tones

Return a JSON array of {batch_size} objects. No other text."""

    def get_system_prompt(self) -> str:
        return (
            "You are a synthetic data generator creating realistic response templates for the "
            f"{self.context} communications team. "
            "Generate professional, policy-appropriate response templates that reflect how a "
            "central bank communications department would respond to various types of inquiries. "
            "Templates should be formal, accurate, and avoid language that could be interpreted "
            "as forward guidance or market-moving signals. "
            "Return ONLY a valid JSON array."
        )
