"""Streamlit UI for the FRS Synthetic Data Generator.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Make the datagen package importable when running from the project root
# ---------------------------------------------------------------------------
_SRC = Path(__file__).parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from datagen.config import (  # noqa: E402
    AppConfig,
    BedrockConfig,
    CategoriesConfig,
    DataConfig,
    DateRangeConfig,
    InsightReportsConfig,
    InquiriesConfig,
    NewsArticlesConfig,
    OutputConfig,
    ResponseTemplatesConfig,
    SocialMediaConfig,
    load_config,
)
from datagen.generators.inquiries import InquiryGenerator  # noqa: E402
from datagen.generators.insight_reports import InsightReportGenerator  # noqa: E402
from datagen.generators.news_articles import NewsArticleGenerator  # noqa: E402
from datagen.generators.response_templates import ResponseTemplateGenerator  # noqa: E402
from datagen.generators.social_media import SocialMediaGenerator  # noqa: E402
from datagen.llm_client import auto_detect_client, detect_ollama  # noqa: E402
from datagen.utils import save_json  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GENERATOR_MAP = {
    "inquiries": InquiryGenerator,
    "social_media": SocialMediaGenerator,
    "news_articles": NewsArticleGenerator,
    "response_templates": ResponseTemplateGenerator,
    "insight_reports": InsightReportGenerator,
}

CATEGORY_LABELS = {
    "inquiries": "Inquiries",
    "social_media": "Social Media",
    "news_articles": "News Articles",
    "response_templates": "Response Templates",
    "insight_reports": "Insight Reports",
}

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"

DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")
DEFAULT_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
DEFAULT_AWS_PROFILE = os.getenv("AWS_PROFILE", "")
DEFAULT_AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DEFAULT_BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"
)

BACKEND_COLORS = {
    "Local Ollama": "🟢",
    "OpenAI": "🔵",
    "AWS Bedrock": "🟠",
    None: "🔴",
}

# ---------------------------------------------------------------------------
# Custom logging handler that feeds into a queue for live UI display
# ---------------------------------------------------------------------------

class QueueLogHandler(logging.Handler):
    """Routes log records into a queue so the UI can display them in real time."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put(self.format(record))


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="FRS Synthetic Data Generator",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    defaults: dict = {
        "llm_backend": None,      # "Local Ollama" | "OpenAI" | "AWS Bedrock" | None
        "llm_detail": "",         # human-readable detail string
        "llm_client": None,       # the active client object
        "ollama_models": [],      # list of model names from /api/tags
        "generation_running": False,
        "generation_logs": [],
        "output_files": [],
        "detection_error": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session_state()

# ---------------------------------------------------------------------------
# LLM backend detection
# ---------------------------------------------------------------------------

def _run_detection(
    ollama_host: str,
    ollama_model: str | None,
    openai_key: str,
    openai_model: str,
    aws_profile: str,
    aws_region: str,
    aws_model_id: str,
    max_tokens: int,
) -> None:
    """Attempt to connect to an LLM backend and update session state."""
    # Set AWS profile env var if provided
    if aws_profile.strip():
        os.environ["AWS_PROFILE"] = aws_profile.strip()

    bedrock_cfg = BedrockConfig(
        model_id=aws_model_id,
        region=aws_region,
        max_tokens=max_tokens,
        batch_size=5,
    )

    # Check Ollama model list ahead of time for the dropdown
    ollama_models = detect_ollama(ollama_host) or []
    st.session_state.ollama_models = ollama_models

    try:
        client, backend, detail = auto_detect_client(
            ollama_host=ollama_host,
            ollama_model=ollama_model or None,
            openai_api_key=openai_key or None,
            openai_model=openai_model,
            bedrock_config=bedrock_cfg,
            max_tokens=max_tokens,
        )
        st.session_state.llm_client = client
        st.session_state.llm_backend = backend
        st.session_state.llm_detail = detail
        st.session_state.detection_error = ""
    except RuntimeError as e:
        st.session_state.llm_client = None
        st.session_state.llm_backend = None
        st.session_state.llm_detail = ""
        st.session_state.detection_error = str(e)


# ---------------------------------------------------------------------------
# Generation worker (runs in a background thread)
# ---------------------------------------------------------------------------

def _generation_worker(
    config: AppConfig,
    client: object,
    categories: list[str],
    log_queue: queue.Queue,
    result_store: dict,
) -> None:
    """Run the generators and push log messages into the queue."""
    handler = QueueLogHandler(log_queue)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    )
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    output_dir = str(Path(__file__).parent / config.output.directory)

    try:
        for cat_name in categories:
            log_queue.put(f"\n{'='*60}")
            log_queue.put(f"  Starting: {CATEGORY_LABELS.get(cat_name, cat_name)}")
            log_queue.put(f"{'='*60}")
            generator_cls = GENERATOR_MAP[cat_name]
            generator = generator_cls(config, client)
            records = generator.generate()
            path = save_json(
                records,
                output_dir,
                cat_name,
                pretty=config.output.pretty,
                add_timestamp=config.output.add_timestamp,
            )
            result_store[cat_name] = {"count": len(records), "path": str(path)}
            log_queue.put(f"  Saved {len(records)} records → {path}")
    except Exception as exc:
        log_queue.put(f"\n[ERROR] Generation failed: {exc}")
        result_store["__error__"] = str(exc)
    finally:
        root_logger.removeHandler(handler)
        log_queue.put("__DONE__")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _sidebar() -> dict:
    """Render the sidebar and return a dict of all user settings."""
    st.sidebar.title("⚙️ Settings")

    # ── LLM Connection ──────────────────────────────────────────────────────
    with st.sidebar.expander("🔌 LLM Connection", expanded=st.session_state.llm_backend is None):
        ollama_host = st.text_input(
            "Ollama Host URL",
            value=DEFAULT_OLLAMA_HOST,
            help="Base URL of your Ollama server. Change to network IP if remote.",
            key="sb_ollama_host",
        )

        # Populate Ollama model dropdown from live API if available
        ollama_models = st.session_state.ollama_models
        if ollama_models:
            ollama_model = st.selectbox(
                "Ollama Model",
                options=ollama_models,
                index=0,
                key="sb_ollama_model",
            )
        else:
            ollama_model = st.text_input(
                "Ollama Model",
                value=DEFAULT_OLLAMA_MODEL,
                help="Model tag (e.g. gemma4, llama3:8b). Populated automatically when Ollama is reachable.",
                key="sb_ollama_model_text",
            )

        st.divider()

        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=DEFAULT_OPENAI_API_KEY,
            placeholder="sk-...",
            help="Used if Ollama is not reachable.",
            key="sb_openai_key",
        )
        openai_model = st.text_input(
            "OpenAI Model",
            value=DEFAULT_OPENAI_MODEL,
            key="sb_openai_model",
        )

        st.divider()

        aws_profile = st.text_input(
            "AWS Profile (SSO)",
            value=DEFAULT_AWS_PROFILE,
            placeholder="e.g. AWSAdministratorAccess-051570254217",
            help="Used as last resort if Ollama and OpenAI are unavailable.",
            key="sb_aws_profile",
        )
        aws_region = st.text_input(
            "AWS Region", value=DEFAULT_AWS_REGION, key="sb_aws_region"
        )
        aws_model_id = st.text_input(
            "Bedrock Model ID",
            value=DEFAULT_BEDROCK_MODEL_ID,
            key="sb_aws_model_id",
        )

        if st.button("🔍 Detect / Re-detect Connection", use_container_width=True):
            with st.spinner("Detecting LLM backend..."):
                _run_detection(
                    ollama_host=ollama_host,
                    ollama_model=ollama_model if isinstance(ollama_model, str) else None,
                    openai_key=openai_key,
                    openai_model=openai_model,
                    aws_profile=aws_profile,
                    aws_region=aws_region,
                    aws_model_id=aws_model_id,
                    max_tokens=4096,
                )
            st.rerun()

    # ── Generation Settings ─────────────────────────────────────────────────
    with st.sidebar.expander("🛠️ Generation Settings", expanded=True):
        batch_size = st.slider("Batch size (records per API call)", 1, 20, 5, key="sb_batch_size")
        max_tokens = st.slider("Max tokens per call", 1024, 8192, 4096, step=256, key="sb_max_tokens")
        context = st.text_area(
            "Context (organisation name)",
            value="Federal Reserve System / Federal Reserve Bank of San Francisco (FRBSF)",
            key="sb_context",
        )
        col1, col2 = st.columns(2)
        with col1:
            date_start = st.date_input("Date From", value=None, key="sb_date_start")
            if date_start is None:
                date_start_str = "2022-01-01"
            else:
                date_start_str = str(date_start)
        with col2:
            date_end = st.date_input("Date To", value=None, key="sb_date_end")
            if date_end is None:
                date_end_str = "2025-12-31"
            else:
                date_end_str = str(date_end)

    # ── Output Settings ─────────────────────────────────────────────────────
    with st.sidebar.expander("📁 Output Settings", expanded=False):
        output_dir = st.text_input("Output directory", value="./output", key="sb_output_dir")
        pretty_json = st.checkbox("Pretty-print JSON", value=True, key="sb_pretty")
        add_timestamp = st.checkbox("Add timestamp to filenames", value=True, key="sb_timestamp")

    return {
        "ollama_host": ollama_host,
        "ollama_model": ollama_model,
        "openai_key": openai_key,
        "openai_model": openai_model,
        "aws_profile": aws_profile,
        "aws_region": aws_region,
        "aws_model_id": aws_model_id,
        "batch_size": batch_size,
        "max_tokens": max_tokens,
        "context": context,
        "date_start": date_start_str,
        "date_end": date_end_str,
        "output_dir": output_dir,
        "pretty_json": pretty_json,
        "add_timestamp": add_timestamp,
    }


# ---------------------------------------------------------------------------
# Connection banner
# ---------------------------------------------------------------------------

def _connection_banner() -> None:
    backend = st.session_state.llm_backend
    detail = st.session_state.llm_detail
    icon = BACKEND_COLORS.get(backend, "🔴")

    if backend:
        st.success(f"{icon} **Connected to: {backend}** — {detail}")
    else:
        err = st.session_state.detection_error
        if err:
            st.error(f"🔴 **Not connected** — {err}")
        else:
            st.warning(
                "🔴 **No LLM backend connected.** "
                "Open the sidebar → LLM Connection and click **Detect**."
            )


# ---------------------------------------------------------------------------
# Category configuration tabs
# ---------------------------------------------------------------------------

def _category_tabs() -> dict:
    """Render per-category configuration tabs. Returns a config dict per category."""
    tabs = st.tabs([CATEGORY_LABELS[c] for c in GENERATOR_MAP])
    cat_settings: dict[str, dict] = {}

    default_topics = {
        "inquiries": [
            "monetary_policy", "interest_rates", "inflation", "employment",
            "banking_regulation", "financial_stability", "quantitative_easing",
            "federal_funds_rate", "economic_outlook", "consumer_protection",
        ],
        "social_media": [
            "fed_rate_decision", "inflation_data", "employment_report", "fomc_meeting",
            "quantitative_tightening", "bank_supervision", "economic_forecast",
            "fed_chair_speech", "treasury_yields", "financial_regulation",
        ],
        "news_articles": [
            "monetary_policy", "interest_rates", "inflation", "employment",
            "banking_regulation", "financial_stability", "fomc_decisions",
            "economic_indicators", "fed_communications", "global_economy",
        ],
        "response_templates": [
            "monetary_policy", "interest_rates", "inflation", "employment",
            "banking_regulation", "financial_stability", "general_inquiry",
            "media_request", "foia_request", "congressional_inquiry",
        ],
        "insight_reports": [
            "daily_summary", "weekly_analysis", "monthly_trend",
            "incident_report", "risk_assessment",
        ],
    }
    default_counts = {
        "inquiries": 20,
        "social_media": 20,
        "news_articles": 20,
        "response_templates": 5,
        "insight_reports": 5,
    }
    topic_labels = {
        "insight_reports": "Report Types",
        "response_templates": "Inquiry Categories",
    }

    for tab, (cat_name, _) in zip(tabs, GENERATOR_MAP.items()):
        with tab:
            col_en, col_cnt = st.columns([1, 2])
            with col_en:
                enabled = st.checkbox("Enabled", value=True, key=f"en_{cat_name}")
            with col_cnt:
                count = st.number_input(
                    "Count",
                    min_value=1,
                    max_value=10000,
                    value=default_counts[cat_name],
                    key=f"cnt_{cat_name}",
                )

            label = topic_labels.get(cat_name, "Topics")
            all_options = default_topics[cat_name]
            selected = st.multiselect(
                label,
                options=all_options,
                default=all_options,
                key=f"topics_{cat_name}",
            )
            cat_settings[cat_name] = {
                "enabled": enabled,
                "count": int(count),
                "topics": selected or all_options,
            }

    return cat_settings


# ---------------------------------------------------------------------------
# Build AppConfig from UI settings
# ---------------------------------------------------------------------------

def _build_config(settings: dict, cat_settings: dict) -> AppConfig:
    cs = cat_settings

    inq = cs["inquiries"]
    sm = cs["social_media"]
    na = cs["news_articles"]
    rt = cs["response_templates"]
    ir = cs["insight_reports"]

    return AppConfig(
        bedrock=BedrockConfig(
            model_id=settings["aws_model_id"],
            region=settings["aws_region"],
            max_tokens=settings["max_tokens"],
            batch_size=settings["batch_size"],
        ),
        data=DataConfig(
            date_range=DateRangeConfig(
                start=settings["date_start"],
                end=settings["date_end"],
            ),
            context=settings["context"],
        ),
        categories=CategoriesConfig(
            inquiries=InquiriesConfig(
                enabled=inq["enabled"],
                count=inq["count"],
                topics=inq["topics"],
            ),
            social_media=SocialMediaConfig(
                enabled=sm["enabled"],
                count=sm["count"],
                topics=sm["topics"],
            ),
            news_articles=NewsArticlesConfig(
                enabled=na["enabled"],
                count=na["count"],
                topics=na["topics"],
            ),
            response_templates=ResponseTemplatesConfig(
                enabled=rt["enabled"],
                count=rt["count"],
                inquiry_categories=rt["topics"],
            ),
            insight_reports=InsightReportsConfig(
                enabled=ir["enabled"],
                count=ir["count"],
                report_types=ir["topics"],
            ),
        ),
        output=OutputConfig(
            format="json",
            directory=settings["output_dir"],
            pretty=settings["pretty_json"],
            add_timestamp=settings["add_timestamp"],
        ),
    )


# ---------------------------------------------------------------------------
# Output file viewer
# ---------------------------------------------------------------------------

def _output_viewer() -> None:
    output_root = Path(__file__).parent / "output"
    if not output_root.exists():
        return

    files = sorted(output_root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return

    st.subheader("📂 Output Files")
    file_names = [f.name for f in files]
    selected_file = st.selectbox("Select file to preview", file_names, key="out_file_select")
    if selected_file:
        path = output_root / selected_file
        size_kb = path.stat().st_size / 1024
        st.caption(f"{path} — {size_kb:.1f} KB")
        with open(path) as fh:
            import json
            data = json.load(fh)
        # Show first 5 records inline; offer full download
        preview = data[:5] if isinstance(data, list) else data
        st.json(preview)
        if isinstance(data, list) and len(data) > 5:
            st.caption(f"Showing 5 of {len(data)} records.")
        with open(path, "rb") as fh:
            st.download_button(
                label=f"⬇ Download {selected_file}",
                data=fh,
                file_name=selected_file,
                mime="application/json",
            )


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("🏦 FRS Synthetic Data Generator")
    st.caption(
        "Generates synthetic communications data for the Federal Reserve System "
        "using your local Ollama, OpenAI, or AWS Bedrock."
    )

    # Sidebar
    settings = _sidebar()

    # Auto-detect on first load
    if st.session_state.llm_backend is None and not st.session_state.detection_error:
        with st.spinner("Auto-detecting LLM backend..."):
            _run_detection(
                ollama_host=settings["ollama_host"],
                ollama_model=settings.get("ollama_model"),
                openai_key=settings["openai_key"],
                openai_model=settings["openai_model"],
                aws_profile=settings["aws_profile"],
                aws_region=settings["aws_region"],
                aws_model_id=settings["aws_model_id"],
                max_tokens=settings["max_tokens"],
            )

    # Connection banner
    _connection_banner()

    st.divider()

    # Category configuration
    st.subheader("📋 Category Configuration")
    cat_settings = _category_tabs()

    st.divider()

    # Generation controls
    st.subheader("🚀 Generate Data")

    client = st.session_state.llm_client
    if not client:
        st.warning("Connect to an LLM backend before generating.")
        _output_viewer()
        return

    # Check which categories are enabled
    enabled_cats = [c for c, s in cat_settings.items() if s["enabled"]]
    total_records = sum(cat_settings[c]["count"] for c in enabled_cats)

    if enabled_cats:
        st.info(
            f"Will generate **{total_records} records** across "
            f"**{len(enabled_cats)} categories**: {', '.join(enabled_cats)}"
        )
    else:
        st.warning("Enable at least one category before generating.")

    col_gen, col_dry = st.columns([2, 1])
    with col_gen:
        generate_btn = st.button(
            "▶ Generate",
            disabled=not enabled_cats or st.session_state.generation_running,
            use_container_width=True,
            type="primary",
        )
    with col_dry:
        dry_run_btn = st.button(
            "👁 Dry Run",
            disabled=not enabled_cats,
            use_container_width=True,
        )

    # Dry run
    if dry_run_btn:
        st.info("**Dry Run — no API calls will be made.**")
        for cat_name in enabled_cats:
            cfg = cat_settings[cat_name]
            st.write(f"- **{CATEGORY_LABELS[cat_name]}**: {cfg['count']} records, "
                     f"topics: {', '.join(cfg['topics'][:3])}{'...' if len(cfg['topics']) > 3 else ''}")

    # Full generation
    if generate_btn and not st.session_state.generation_running:
        config = _build_config(settings, cat_settings)
        st.session_state.generation_running = True
        st.session_state.generation_logs = []

        log_queue: queue.Queue = queue.Queue()
        result_store: dict = {}

        thread = threading.Thread(
            target=_generation_worker,
            args=(config, client, enabled_cats, log_queue, result_store),
            daemon=True,
        )
        thread.start()

        log_box = st.empty()
        status_box = st.empty()
        all_logs: list[str] = []
        status_box.info("⏳ Generation in progress...")

        while thread.is_alive() or not log_queue.empty():
            flushed = False
            while not log_queue.empty():
                msg = log_queue.get()
                if msg == "__DONE__":
                    break
                all_logs.append(msg)
                flushed = True
            if flushed:
                log_box.code("\n".join(all_logs[-80:]), language="")
            time.sleep(0.4)

        thread.join()

        # Flush remaining messages
        while not log_queue.empty():
            msg = log_queue.get()
            if msg != "__DONE__":
                all_logs.append(msg)
        log_box.code("\n".join(all_logs), language="")

        st.session_state.generation_logs = all_logs
        st.session_state.generation_running = False

        if "__error__" in result_store:
            status_box.error(f"Generation failed: {result_store['__error__']}")
        else:
            status_box.success(
                "✅ Generation complete! "
                + "  ".join(
                    f"{CATEGORY_LABELS.get(k, k)}: {v['count']} records"
                    for k, v in result_store.items()
                )
            )

    # Show previous run logs if present
    elif st.session_state.generation_logs:
        with st.expander("Last run log", expanded=False):
            st.code("\n".join(st.session_state.generation_logs), language="")

    st.divider()

    # Output viewer
    _output_viewer()


if __name__ == "__main__":
    main()
