"""Sidebar: academic branding, navigation, quick demo triggers, and engine tuning."""
from __future__ import annotations

import streamlit as st

from analyzer.similarity_engine import (
    DEFAULT_WEIGHTS,
    METHOD_LABELS,
    AnalysisConfig,
    AnalysisResult,
    run_analysis,
)
from utils.helpers import Thresholds
from utils.sample_data import get_demo_files
from utils.validators import (
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_FILES,
    HARD_MAX_FILE_BYTES,
    HARD_MAX_FILES,
    MIN_FILES,
    UploadLimits,
)

PAGES = ["Dashboard", "New Analysis", "Comparison Results", "Analysis History", "About Project"]


def init_state() -> None:
    defaults = {
        "nav_page": "Dashboard",
        "history": [],
        "current": None,
        "uploader_key": 0,
        "removed_ids": set(),
        "compare_mode": False,
        "matrix_nonce": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def request_navigation(page: str, pair: tuple[str, str] | None = None, reopen: AnalysisResult | None = None) -> None:
    """Ask for a page change on next run."""
    st.session_state["_pending"] = {"page": page, "pair": pair, "reopen": reopen}


def apply_pending_navigation() -> None:
    """Apply queued navigation before widgets render."""
    pending = st.session_state.pop("_pending", None)
    if not pending:
        return
    st.session_state["nav_page"] = pending["page"]
    if pending["reopen"] is not None:
        st.session_state["current"] = pending["reopen"]
    if pending["pair"]:
        st.session_state["cmp_a"], st.session_state["cmp_b"] = pending["pair"]
        st.session_state["compare_mode"] = True
    else:
        st.session_state["compare_mode"] = False


def _trigger_quick_demo(config: AnalysisConfig) -> None:
    """Instantly analyze the pre-loaded academic demo suite."""
    demo_files = get_demo_files()
    with st.spinner("Executing multi-engine analysis on 4 sample lab files..."):
        result = run_analysis(demo_files, config)
    st.session_state["current"] = result
    st.session_state["history"].insert(0, result)
    st.session_state["flash"] = "✅ Academic demo suite loaded: 4 student files analyzed across 6 unique pairs!"
    request_navigation("Comparison Results")
    st.rerun()


def render_sidebar() -> tuple[AnalysisConfig, UploadLimits, list[str]]:
    """Draw the professional sidebar and return active settings plus validation errors."""
    with st.sidebar:
        # Project Brand Header
        st.markdown(
            """
            <div style="padding: 6px 0 14px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 14px;">
                <div style="display:flex; align-items:center; gap: 8px; margin-bottom: 6px;">
                    <div style="background: linear-gradient(135deg, #6366F1, #06B6D4); width: 34px; height: 34px; border-radius: 9px; display:flex; align-items:center; justify-content:center; font-size: 1.1rem; box-shadow: 0 0 14px rgba(99,102,241,0.4);">
                        🔍
                    </div>
                    <div>
                        <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size: 1.25rem; font-weight: 800; color:#FFFFFF; letter-spacing: -0.02em;">CodeSimilarity</div>
                        <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 500;">Plagiarism & AST Engine v2.4</div>
                    </div>
                </div>
                <div style="display:inline-block; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); color:#A5B4FC; font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; text-transform:uppercase; letter-spacing:0.04em;">
                    Final Year Capstone Project
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("MAIN NAVIGATION")
        st.radio("Navigate", PAGES, key="nav_page", label_visibility="collapsed")
        st.write("")

        # Settings Drawer
        with st.expander("⚙️ Engine Hyperparameters", expanded=False):
            st.markdown("##### 🔬 Detection Engines")
            use_token = st.checkbox("Token N-gram Similarity", True, key="set_token",
                                    help="Lexical token stream comparison ignoring formatting and whitespace.")
            use_tfidf = st.checkbox("TF-IDF Vector Space", True, key="set_tfidf",
                                    help="Term frequency-inverse document frequency cosine distance.")
            use_ast = st.checkbox("AST Structural Tree", True, key="set_ast",
                                  help="Abstract Syntax Tree subtree hash matching. Highly resistant to renaming.")
            normalize = st.checkbox(
                "Mask User Identifiers", True, key="set_norm",
                help="Heuristic replacement of variable/function names with canonical tokens to catch renamed plagiarism.",
            )

            st.markdown("##### ⚖️ Ensemble Weights (%)")
            weights = {
                "token": st.number_input("Token Weight", 0.0, 100.0, DEFAULT_WEIGHTS["token"], 5.0, key="w_token", disabled=not use_token),
                "tfidf": st.number_input("TF-IDF Weight", 0.0, 100.0, DEFAULT_WEIGHTS["tfidf"], 5.0, key="w_tfidf", disabled=not use_tfidf),
                "ast": st.number_input("AST Weight", 0.0, 100.0, DEFAULT_WEIGHTS["ast"], 5.0, key="w_ast", disabled=not use_ast),
            }

            st.markdown("##### 🎯 Classification Thresholds (%)")
            moderate = st.number_input("Moderate Threshold", 1.0, 100.0, 25.0, 1.0, key="th_mod")
            high = st.number_input("High Threshold", 1.0, 100.0, 50.0, 1.0, key="th_high")
            very_high = st.number_input("Very High Threshold", 1.0, 100.0, 75.0, 1.0, key="th_vh")

            st.markdown("##### 📁 Quota & Buffer Limits")
            max_files = st.number_input("Max Submissions", MIN_FILES, HARD_MAX_FILES, DEFAULT_MAX_FILES, 1, key="max_files")
            max_kb = st.number_input("Max Size Per File (KB)", 1, HARD_MAX_FILE_BYTES // 1024,
                                     DEFAULT_MAX_FILE_BYTES // 1024, 64, key="max_kb")

        config = AnalysisConfig(
            use_token=use_token,
            use_tfidf=use_tfidf,
            use_ast=use_ast,
            normalize_identifiers=normalize,
            weights=weights,
            thresholds=Thresholds(moderate, high, very_high),
        )
        limits = UploadLimits(max_files=int(max_files), max_file_bytes=int(max_kb) * 1024)
        errors = config.validate() + limits.validate()
        if errors:
            for message in errors:
                st.warning(message)
        else:
            shown = config.effective_weights()
            summary_str = " · ".join(f"{METHOD_LABELS[m].split()[0]} {w:.0f}%" for m, w in shown.items())
            st.caption(f"Active Ensemble: {summary_str}")

        st.write("")
        # One-Click Demo Button
        if st.button("⚡ Run Demo Showcase (4 Files)", width="stretch", type="secondary",
                     help="Instantly test the engine with pre-packaged student lab submissions."):
            _trigger_quick_demo(config)

        st.divider()
        # Academic & Engine Status Footer
        st.markdown(
            """
            <div style="font-size: 0.74rem; color: #64748B; line-height: 1.5;">
                <div style="display:flex; align-items:center; gap: 6px; margin-bottom: 4px; color: #10B981; font-weight:600;">
                    <span style="display:inline-block; width:7px; height:7px; background:#10B981; border-radius:50%; box-shadow:0 0 8px #10B981;"></span>
                    Python 3.12 Engine Active
                </div>
                <div>Department of Computer Science</div>
                <div>B.Tech Final Year Project</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return config, limits, errors
