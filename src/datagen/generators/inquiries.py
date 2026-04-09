"""Generator for incoming communications / inquiries."""

from __future__ import annotations

import json

from datagen.generators.base import BaseGenerator


class InquiryGenerator(BaseGenerator):
    """Generates synthetic incoming communication/inquiry records."""

    category_name = "inquiries"
    id_prefix = "INQ"

    def get_count(self) -> int:
        return self.config.categories.inquiries.count

    def build_prompt(self, batch_index: int, batch_size: int, offset: int) -> str:
        cfg = self.config.categories.inquiries
        return f"""Generate exactly {batch_size} synthetic incoming communication/inquiry records
for the {self.context}.

Each record must be a JSON object with these fields:
- "id": string, format "INQ-XXXXX" starting from INQ-{offset + 1:05d}
- "source": one of {json.dumps(cfg.sources)}
- "channel": one of {json.dumps(cfg.channels)}
- "subject": string, a realistic subject line for the inquiry
- "body": string, the full text of the inquiry (2-5 sentences, realistic content about Federal Reserve topics)
- "category": one of {json.dumps(cfg.topics)}
- "priority": one of {json.dumps(cfg.priorities)}
- "timestamp": ISO 8601 datetime between {self.date_start} and {self.date_end}
- "sender_name": string, a realistic name
- "sender_organization": string, organization name (if media or stakeholder) or "Individual" for public

Requirements:
- Make the content realistic and diverse, referencing actual Federal Reserve / FRBSF topics
  like FOMC decisions, interest rate changes, inflation reports, employment data, QE/QT policies
- Vary the tone: some formal (media/stakeholder), some casual (public)
- Distribute sources, channels, categories, and priorities realistically
- Media inquiries should reference specific press events or data releases
- Public inquiries should reflect common citizen concerns about the economy
- Stakeholder inquiries should come from banks, financial institutions, or congressional offices
- Each record should be unique and not repetitive
- Batch {batch_index + 1}: generate records with diverse topics, don't repeat patterns from description

Return a JSON array of {batch_size} objects. No other text."""

    def get_system_prompt(self) -> str:
        return (
            "You are a synthetic data generator specializing in central bank communications. "
            f"Generate realistic inquiry data for the {self.context}. "
            "The inquiries should reflect real-world communications received by the Federal Reserve "
            "from journalists, the general public, financial institutions, and government stakeholders. "
            "Reference real Federal Reserve topics: FOMC meetings, federal funds rate decisions, "
            "inflation targets, employment mandates, banking supervision, and financial stability. "
            "Return ONLY a valid JSON array."
        )
