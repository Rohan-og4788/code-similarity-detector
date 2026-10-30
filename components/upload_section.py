"""New Analysis page: upload, validate, inspect, and run similarity checks on Python files."""
from __future__ import annotations

import logging
import streamlit as st

from analyzer.file_processor import ProcessedUploads, SourceFile, process_uploads
from analyzer.similarity_engine import AnalysisConfig, run_analysis
from components.sidebar import request_navigation
from components.styles import card, card_row, info_box, note, page_header
from utils.helpers import format_size
from utils.sample_data import get_demo_files
from utils.validators import MAX_TOTAL_BYTES, UploadLimits

logger = logging.getLogger(__name__)


def _clear_all() -> None:
    """Clear all staged and uploaded files."""
    st.session_state["uploader_key"] += 1
    st.session_state["removed_ids"] = set()
    st.session_state["_use_demo_files"] = False


def render_upload(config: AnalysisConfig, limits: UploadLimits, settings_errors: list[str]) -> None:
    page_header("New Similarity Analysis", "Upload student Python source files (.py) to execute multi-engine plagiarism analysis.")
    note(
        f"Memory Sandbox: Files are parsed in-memory and never written to disk or executed. "
        f"Limits: .py files only · Up to {limits.max_files} files · {format_size(limits.max_file_bytes)} per file · "
        f"{format_size(MAX_TOTAL_BYTES)} max batch."
    )

    # Mode Selector Tabs
    tab_upload, tab_demo = st.tabs(["📤 Upload Python Files (.py)", "🧪 Academic Demo Suite (4 Lab Files)"])

    accepted_files: list[SourceFile] = []
    rejected_items = []

    with tab_upload:
        st.markdown("##### 📁 Select or Drag & Drop Python Files")
        raw_uploads = st.file_uploader(
            "Choose .py files",
            type=["py"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state['uploader_key']}",
            help="Select 2 or more .py files to compare.",
            label_visibility="collapsed",
        )

        if raw_uploads:
            # When user uploads files, ensure custom upload mode is active
            st.session_state["_use_demo_files"] = False
            items = [(u.name, u.getvalue()) for u in raw_uploads]
            processed = process_uploads(items, limits)
            accepted_files = processed.accepted
            rejected_items = processed.rejected

    with tab_demo:
        st.markdown("##### 🧪 Pre-packaged Student Lab Submissions")
        st.caption("Demonstrates how the engine identifies structural cloning, identifier renaming, and separate algorithm paradigms.")
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            if st.button("⚡ Stage 4 Academic Demo Submissions", type="secondary", width="stretch"):
                st.session_state["_use_demo_files"] = True
                st.rerun()
        with col_d2:
            if st.session_state.get("_use_demo_files", False):
                if st.button("↩️ Switch Back to Upload Mode", type="secondary", width="stretch"):
                    st.session_state["_use_demo_files"] = False
                    st.rerun()

        if st.session_state.get("_use_demo_files", False):
            info_box("Academic demo suite currently staged for analysis (4 student implementations).")
            accepted_files = get_demo_files()

    # Metric summary row
    st.write("")
    card_row([
        card("Submissions Staged", str(len(accepted_files) + len(rejected_items)), "Total files submitted", "📂"),
        card("Ready for Analysis", str(len(accepted_files)), "Valid Python source", "✅"),
        card("Rejected / Invalid", str(len(rejected_items)), "Exceeded size or invalid", "⚠️"),
    ])
    st.write("")

    # Display any rejected files
    if rejected_items:
        st.markdown("##### ⚠️ Rejected Files")
        for item in rejected_items:
            st.error(f"**{item.name}** was rejected: {item.reason}")

    # Display staged accepted files with preview inspector
    if accepted_files:
        st.markdown("##### 📄 Submissions Ready for Evaluation")
        n = len(accepted_files)
        num_pairs = n * (n - 1) // 2
        st.caption(f"**{n} submissions staged** → **{num_pairs} unique pair(s)** will be evaluated across Token, TF-IDF, and AST engines.")

        for source in accepted_files:
            with st.expander(f"📄 {source.name} · {format_size(source.size)} · {source.line_count} lines", expanded=False):
                st.caption(f"UTF-8 encoded · {source.line_count} physical lines · {format_size(source.size)}")
                st.code(source.text, language="python")

    # Validation checks
    problems = list(settings_errors)
    if len(accepted_files) < 2:
        problems.append("Please stage at least two valid Python (.py) files to begin pairwise comparison.")
    for message in problems:
        st.warning(message)

    st.write("")
    left, right = st.columns([2, 1])
    run = left.button("🚀 Run Similarity Analysis", type="primary", disabled=bool(problems), width="stretch")
    right.button("🗑️ Reset Staged Files", on_click=_clear_all, width="stretch")

    if run:
        try:
            with st.spinner("Executing AST parsing, TF-IDF vectorization, and token alignment..."):
                result = run_analysis(accepted_files, config)
        except ValueError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            logger.warning("Analysis failed with %s", type(exc).__name__)
            st.error(f"The analysis could not be completed: {exc}")
            return

        st.session_state["current"] = result
        st.session_state["history"].insert(0, result)
        st.session_state["flash"] = (
            f"Analysis complete: {len(result.analyzed_files)} files analyzed, {len(result.pairs)} unique pairs compared."
        )
        request_navigation("Comparison Results")
        st.rerun()
