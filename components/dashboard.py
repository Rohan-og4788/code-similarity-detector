"""Dashboard, results overview, forensic reports, history and academic project details."""
from __future__ import annotations

import html
import pandas as pd
import streamlit as st

from analyzer.report_generator import build_csv, build_html, build_json, methods_used
from analyzer.similarity_engine import METHOD_LABELS, AnalysisResult, run_analysis, similarity_matrix
from components.charts import breakdown_chart, distribution_chart, similarity_heatmap
from components.sidebar import request_navigation
from components.styles import card, card_row, hero_banner, info_box, note, page_header
from utils.helpers import CATEGORIES, Thresholds, badge_html, fmt_score, is_high_or_above
from utils.sample_data import get_demo_files

TEMP_NOTICE = "Session Sandbox Active: Analysis results and metrics reside in memory for this session and are never written to external disks."


def _when(iso: str) -> str:
    return iso.replace("T", " ").replace("+00:00", " UTC")


# --------------------------------------------------------------------------- #
# Dashboard (session statistics & project overview)
# --------------------------------------------------------------------------- #
def render_dashboard() -> None:
    page_header("Executive Dashboard", "Academic code plagiarism & syntactic similarity analysis system.")

    history: list[AnalysisResult] = st.session_state["history"]

    if not history:
        # Presentation Showcase & Hero when no analysis has been run yet
        hero_banner(
            title="CodeSimilarity: AST & Lexical Code Plagiarism Detection",
            description=(
                "A multi-engine plagiarism and code similarity forensic system built for academic evaluations. "
                "Combines Python Abstract Syntax Trees (AST), Scikit-Learn TF-IDF cosine embeddings, and "
                "token-level sequence matching to uncover code cloning across renaming, restructuring, and formatting obfuscation."
            ),
            tags=["Python 3.12 AST", "TF-IDF Cosine", "Levenshtein Tokens", "Identifier Masking", "B.Tech Capstone Project"],
        )

        st.markdown("### ⚡ Quick Start Options")
        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.markdown(
                """
                <div style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.3); border-radius: 14px; padding: 20px; height: 100%;">
                    <div style="font-size: 1.25rem; font-weight: 700; color:#FFFFFF; margin-bottom: 6px;">🧪 Instant Showcase Demo</div>
                    <div style="font-size: 0.88rem; color:#94A3B8; margin-bottom: 16px;">
                        Evaluate 4 preloaded student lab submissions (Original algorithm, Obfuscated/Renamed version, Re-formatted version, and Independent alternative).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Fetch config from sidebar session
            if st.button("🚀 Run Showcase Demo Dataset (4 Submissions)", type="primary", width="stretch"):
                from components.sidebar import render_sidebar
                # Using demo files
                demo_files = get_demo_files()
                from analyzer.similarity_engine import AnalysisConfig
                demo_cfg = AnalysisConfig(normalize_identifiers=True)
                with st.spinner("Analyzing demo submissions with AST + TF-IDF + Token engines..."):
                    result = run_analysis(demo_files, demo_cfg)
                st.session_state["current"] = result
                st.session_state["history"].insert(0, result)
                st.session_state["flash"] = "✅ Showcase demo completed: 4 student submissions compared across 6 unique pairs!"
                request_navigation("Comparison Results")
                st.rerun()

        with c_right:
            st.markdown(
                """
                <div style="background: rgba(6,182,212,0.08); border: 1px solid rgba(6,182,212,0.3); border-radius: 14px; padding: 20px; height: 100%;">
                    <div style="font-size: 1.25rem; font-weight: 700; color:#FFFFFF; margin-bottom: 6px;">📁 Upload Custom Submissions</div>
                    <div style="font-size: 0.88rem; color:#94A3B8; margin-bottom: 16px;">
                        Upload two or more <code>.py</code> student source files to perform full pairwise plagiarism scans and generate interactive diff reports.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("📤 Go to Submission Upload", type="secondary", width="stretch"):
                request_navigation("New Analysis")
                st.rerun()

        st.write("")
        st.markdown("### 🏛️ Detection Engine Architecture")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                """
                <div class="cs-feature-card">
                    <span class="cs-feature-icon">🌲</span>
                    <div class="cs-feature-title">AST Structural Tree</div>
                    <div class="cs-feature-desc">Compiles code into syntax trees; detects algorithmic logic and control flow even when variable names and functions are renamed.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                """
                <div class="cs-feature-card">
                    <span class="cs-feature-icon">📊</span>
                    <div class="cs-feature-title">TF-IDF Vector Space</div>
                    <div class="cs-feature-desc">Computes term frequencies and inverse document frequencies to measure vector cosine similarity across lexical vocabularies.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                """
                <div class="cs-feature-card">
                    <span class="cs-feature-icon">🔠</span>
                    <div class="cs-feature-title">Token Levenshtein</div>
                    <div class="cs-feature-desc">Tokenizes the lexical stream ignoring comments, blank lines, and docstrings to measure exact sequential code overlaps.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                """
                <div class="cs-feature-card">
                    <span class="cs-feature-icon">🛡️</span>
                    <div class="cs-feature-title">Identifier Masking</div>
                    <div class="cs-feature-desc">Replaces user-defined variables and arguments with canonical registers (v0, v1...) to defeat variable-renaming evasion.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")
        st.markdown("### 🔄 Detection Pipeline Workflow")
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 18px 24px; font-family:'JetBrains Mono',monospace; font-size: 0.85rem; color:#94A3B8; overflow-x: auto;">
                <div style="display: flex; align-items: center; justify-content: space-between; min-width: 760px; gap: 12px;">
                    <div style="text-align: center; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.4); padding: 10px 14px; border-radius: 8px; color: #FFFFFF;">
                        📥 1. Ingestion<br><span style="font-size:0.75rem; color:#A5B4FC;">UTF-8 Sanitizer</span>
                    </div>
                    <span style="color:#6366F1; font-weight:bold;">➔</span>
                    <div style="text-align: center; background: rgba(6,182,212,0.15); border: 1px solid rgba(6,182,212,0.4); padding: 10px 14px; border-radius: 8px; color: #FFFFFF;">
                        🌳 2. AST Parse<br><span style="font-size:0.75rem; color:#67E8F9;">Normalized Nodes</span>
                    </div>
                    <span style="color:#06B6D4; font-weight:bold;">➔</span>
                    <div style="text-align: center; background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4); padding: 10px 14px; border-radius: 8px; color: #FFFFFF;">
                        🔬 3. Feature Extraction<br><span style="font-size:0.75rem; color:#6EE7B7;">TF-IDF + Tokens</span>
                    </div>
                    <span style="color:#10B981; font-weight:bold;">➔</span>
                    <div style="text-align: center; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4); padding: 10px 14px; border-radius: 8px; color: #FFFFFF;">
                        ⚖️ 4. Ensemble Scoring<br><span style="font-size:0.75rem; color:#FCD34D;">Weighted Matrix</span>
                    </div>
                    <span style="color:#F59E0B; font-weight:bold;">➔</span>
                    <div style="text-align: center; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4); padding: 10px 14px; border-radius: 8px; color: #FFFFFF;">
                        📄 5. Forensic Report<br><span style="font-size:0.75rem; color:#FCA5A5;">Side-by-side Diff</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # When history exists: Render live operational dashboard
    scored = [p for r in history for p in r.scored_pairs]
    scores = [p.combined for p in scored]
    high_count = sum(1 for p in scored if is_high_or_above(p.classification))

    card_row([
        card("Files Analyzed", str(sum(len(r.analyzed_files) for r in history)), f"Across {len(history)} session run(s)", "📂"),
        card("Pairs Evaluated", str(len(scored)), "Pairwise comparisons", "🔬"),
        card("Flagged High Similarity", str(high_count), "High or Very High clone risk", "🚨"),
        card("Mean Similarity Index", fmt_score(sum(scores) / len(scores)) if scores else "n/a", "Average session score", "📈"),
    ])
    st.write("")

    left, right = st.columns([3, 2])
    with left:
        if scores:
            st.plotly_chart(
                distribution_chart(scores, history[0].config.thresholds, "Similarity Score Distribution (Session Cumulative)"),
                width="stretch", key="dash_dist",
            )
        else:
            st.info("No complete scores recorded yet.")

    with right:
        st.markdown("#### 🕒 Recent Pairwise Comparisons")
        rows = []
        for r in history[:5]:
            for p in sorted(r.scored_pairs, key=lambda x: x.combined, reverse=True)[:3]:
                rows.append({
                    "Time": _when(r.created_at),
                    "File A": p.file_a,
                    "File B": p.file_b,
                    "Combined (%)": p.combined,
                    "Classification": p.classification,
                })
        if rows:
            st.dataframe(pd.DataFrame(rows[:10]), hide_index=True, width="stretch")
        st.button("🔍 Open Latest Results", type="primary", on_click=request_navigation, args=("Comparison Results", None, history[0]))


# --------------------------------------------------------------------------- #
# Results overview
# --------------------------------------------------------------------------- #
def render_results(result: AnalysisResult) -> None:
    page_header("Forensic Similarity Results", f"Analysis ID: {result.analysis_id} · Timestamp: {_when(result.created_at)} · Execution: {result.duration_s}s")
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    cfg = result.config
    scored = result.scored_pairs
    highest = max((p.combined for p in scored), default=None)

    # Forensic Verdict Alert Banner
    if highest is not None:
        if highest >= cfg.thresholds.very_high:
            st.markdown(
                f"""
                <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); border-left: 6px solid #EF4444; border-radius: 12px; padding: 14px 20px; margin-bottom: 1.25rem;">
                    <div style="display:flex; align-items:center; gap: 8px; font-weight:700; color:#EF4444; font-size: 1.05rem;">
                        <span>🚨</span> CRITICAL SIMILARITY DETECTED (Peak: {highest:.1f}%)
                    </div>
                    <div style="color:#CBD5E1; font-size:0.88rem; margin-top:4px;">
                        One or more file pairs exceed the Very High similarity threshold ({cfg.thresholds.very_high:g}%). 
                        High probability of structural plagiarism or direct code cloning. Detailed code inspection required.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif highest >= cfg.thresholds.high:
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.4); border-left: 6px solid #F59E0B; border-radius: 12px; padding: 14px 20px; margin-bottom: 1.25rem;">
                    <div style="display:flex; align-items:center; gap: 8px; font-weight:700; color:#F59E0B; font-size: 1.05rem;">
                        <span>⚠️</span> MODERATE-TO-HIGH SIMILARITY (Peak: {highest:.1f}%)
                    </div>
                    <div style="color:#CBD5E1; font-size:0.88rem; margin-top:4px;">
                        Notable similarity detected. Review shared algorithms, common boilerplates, or potential code derivation.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.4); border-left: 6px solid #10B981; border-radius: 12px; padding: 14px 20px; margin-bottom: 1.25rem;">
                    <div style="display:flex; align-items:center; gap: 8px; font-weight:700; color:#10B981; font-size: 1.05rem;">
                        <span>✅</span> ACCEPTABLE ORIGINALITY (All Pairs Below High Threshold)
                    </div>
                    <div style="color:#CBD5E1; font-size:0.88rem; margin-top:4px;">
                        Submissions demonstrate independent structural implementations with no critical plagiarism flags.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    card_row([
        card("Submissions Analyzed", str(len(result.analyzed_files)), f"of {len(result.files)} uploaded", "📄"),
        card("Unique Pairs Evaluated", str(len(scored)), f"{len(result.pairs)} possible combinations", "🔬"),
        card("Peak Similarity", fmt_score(highest), "Highest recorded pair match", "🎯"),
        card("Flagged Clones", str(sum(1 for p in scored if is_high_or_above(p.classification))), "High or Very High pairs", "🚩"),
    ])

    st.caption(
        "Active Engines: " + ", ".join(methods_used(result))
        + f" · Identifier Normalization: {'Enabled' if cfg.normalize_identifiers else 'Disabled'}"
        + " · Weights: " + ", ".join(f"{METHOD_LABELS[m].split()[0]} {w:.0f}%" for m, w in cfg.effective_weights().items())
    )
    note("Quantitative similarity scores are forensic indicators, not automated proof of plagiarism. Shared templates or standard textbook algorithms can legitimately yield structural matches.")

    for warning in result.warnings:
        st.warning(warning)
    _render_failures(result)

    if not scored:
        st.info("No pair has a complete score, so there are no charts to show.")
        return

    left, right = st.columns(2)
    left.plotly_chart(distribution_chart([p.combined for p in scored], cfg.thresholds), width="stretch", key="res_dist")
    right.plotly_chart(breakdown_chart(scored, cfg), width="stretch", key="res_breakdown")

    names, matrix = similarity_matrix(result)
    key = f"matrix_{result.analysis_id}_{st.session_state['matrix_nonce']}"
    event = st.plotly_chart(
        similarity_heatmap(result, names, matrix),
        width="stretch", key=key, on_select="rerun", selection_mode="points",
    )
    points = (event.selection.points if event and event.selection else []) or []
    if points:
        x, y = points[0].get("x"), points[0].get("y")
        if x in names and y in names and x != y:
            request_navigation("Comparison Results", (y, x))
            st.rerun()
    st.caption("💡 Interactive Matrix: Click any colored cell to jump directly into the side-by-side code diff.")

    _render_table(result)
    _render_downloads(result)


def _render_failures(result: AnalysisResult) -> None:
    skipped = [p for p in result.pairs if p.status != "ok"]
    if result.failed_files:
        st.error(f"{len(result.failed_files)} file(s) encountered syntax or parsing errors and were excluded from comparisons.")
        st.dataframe(pd.DataFrame([{"File": f.name, "Reason": f.error} for f in result.failed_files]),
                     hide_index=True, width="stretch")
    if skipped:
        with st.expander(f"⚠️ Skipped or Incomplete Comparisons ({len(skipped)})"):
            st.dataframe(pd.DataFrame([{"File A": p.file_a, "File B": p.file_b, "Status": p.status, "Reason": p.note}
                                       for p in skipped]), hide_index=True, width="stretch")


def _render_table(result: AnalysisResult) -> None:
    st.markdown("#### 📋 Detailed Pairwise Score Registry")
    df = pd.DataFrame([{
        "File A": p.file_a,
        "File B": p.file_b,
        "Token (%)": p.token,
        "TF-IDF (%)": p.tfidf,
        "AST (%)": p.ast,
        "Combined (%)": p.combined,
        "Classification": p.classification,
    } for p in result.scored_pairs])

    c1, c2, c3, c4 = st.columns(4)
    query = c1.text_input("Filter by filename", key="flt_name", placeholder="Search filename...")
    cats = c2.multiselect("Classification Level", list(CATEGORIES), default=list(CATEGORIES), key="flt_cat")
    minimum = c3.slider("Minimum Combined (%)", 0, 100, 0, key="flt_min")
    sort_col = c4.selectbox("Sort Metric", ["Combined (%)", "AST (%)", "Token (%)", "TF-IDF (%)", "File A", "File B"], key="flt_sort")
    ascending = st.radio("Order", ["Highest first", "Lowest first"], horizontal=True, key="flt_order") == "Lowest first"

    mask = df["Classification"].isin(cats) & (df["Combined (%)"] >= minimum)
    if query:
        mask &= df["File A"].str.contains(query, case=False, regex=False) | df["File B"].str.contains(query, case=False, regex=False)
    view = df[mask].sort_values(sort_col, ascending=ascending, na_position="last").reset_index(drop=True)
    st.caption(f"Showing {len(view)} of {len(df)} pairs. Select a row to inspect side-by-side diff.")

    config = {c: st.column_config.NumberColumn(c, format="%.1f") for c in ("Token (%)", "TF-IDF (%)", "AST (%)")}
    config["Combined (%)"] = st.column_config.ProgressColumn("Combined (%)", min_value=0, max_value=100, format="%.1f")
    event = st.dataframe(view, hide_index=True, width="stretch", column_config=config, key=f"pairs_{result.analysis_id}",
                         on_select="rerun", selection_mode="single-row")
    rows = event.selection.rows if event and event.selection else []
    if rows and rows[0] < len(view):
        row = view.iloc[rows[0]]
        st.button(f"🔍 Inspect Comparison: {row['File A']} ↔ {row['File B']}", type="primary",
                  on_click=request_navigation, args=("Comparison Results", (row["File A"], row["File B"])))


def _render_downloads(result: AnalysisResult) -> None:
    st.markdown("#### 📥 Export Forensic Reports")
    st.caption("Exports structured comparison tables and algorithmic breakdown metadata. Uploaded code remains private in-memory.")
    stem = f"codesimilarity_report_{result.analysis_id}"
    c1, c2, c3 = st.columns(3)
    c1.download_button("📊 Download CSV Report", build_csv(result), f"{stem}.csv", "text/csv", width="stretch")
    c2.download_button("🗄️ Download JSON Report", build_json(result), f"{stem}.json", "application/json", width="stretch")
    c3.download_button("🌐 Download HTML Forensic Dossier", build_html(result), f"{stem}.html", "text/html", width="stretch")


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #
def _clear_history() -> None:
    st.session_state["history"] = []
    st.session_state["current"] = None
    st.session_state["compare_mode"] = False


def render_history() -> None:
    page_header("Analysis History", "Audit trail of all similarity checks executed during this browser session.")
    note(TEMP_NOTICE)
    history: list[AnalysisResult] = st.session_state["history"]
    if not history:
        st.info("No prior analyses in this session. Execute a check in 'New Analysis' or launch the demo.")
        return

    st.button("🗑️ Clear Session History", on_click=_clear_history)
    for r in history:
        best = max((p.combined for p in r.scored_pairs), default=None)
        with st.expander(f"Run {_when(r.created_at)} · {len(r.files)} files · Peak Similarity: {fmt_score(best)}"):
            st.write("Included Submissions: " + ", ".join(f.name for f in r.files))
            st.caption("Active Engines: " + ", ".join(methods_used(r)))
            st.dataframe(pd.DataFrame([{
                "File A": p.file_a,
                "File B": p.file_b,
                "Combined (%)": p.combined,
                "Classification": p.classification,
                "Status": p.status,
            } for p in sorted(r.pairs, key=lambda x: x.combined or -1, reverse=True)]),
                hide_index=True, width="stretch")
            st.button("📂 Re-open This Analysis", key=f"reopen_{r.analysis_id}", on_click=request_navigation,
                      args=("Comparison Results", None, r))


# --------------------------------------------------------------------------- #
# About & Academic Capstone Presentation
# --------------------------------------------------------------------------- #
def render_about(thresholds: Thresholds) -> None:
    page_header("Academic Capstone Project", "B.Tech Computer Science & Engineering Final Year Capstone Project.")

    st.markdown(
        """
        ### 📖 Project Abstract
        **CodeSimilarity** is an intelligent source code similarity and automated plagiarism detection platform 
        engineered to assist academic evaluators and students. Unlike rudimentary character-matching tools 
        that can be easily bypassed by variable renaming, comment tampering, or statement reordering, 
        this system incorporates **Abstract Syntax Tree (AST)** structural matching, **TF-IDF lexical frequency vectors**, 
        and **token sequence alignment**.
        """
    )

    st.markdown("### 🔬 Multi-Engine Mathematical Model")
    st.latex(r"Score_{combined} = w_{token} \cdot S_{token} + w_{tfidf} \cdot S_{tfidf} + w_{ast} \cdot S_{ast}")
    st.caption(r"Where weights are normalized such that $\sum w_i = 1.0$. If an individual engine is disabled, remaining weights dynamically rescale to 100%.")

    st.write("")
    st.markdown("### 🛡️ Obfuscation Resistance Matrix")
    st.markdown(
        """
        | Evasion Technique | Naive Text Diff | Token Levenshtein | TF-IDF Cosine | AST Structural Tree |
        | :--- | :---: | :---: | :---: | :---: |
        | **Variable / Function Renaming** | ❌ Fails (0% match) | ❌ Weak | ⚠️ Partial | ✅ **100% Resistant** (Masked) |
        | **Comments & Docstrings Tampering**| ❌ Fails | ✅ **Resistant** | ✅ **Resistant** | ✅ **100% Resistant** |
        | **Whitespace & Indentation Shifts**| ❌ Fails | ✅ **Resistant** | ✅ **Resistant** | ✅ **100% Resistant** |
        | **Dead Code / Statement Reordering**| ❌ Fails | ⚠️ Partial | ✅ **Resistant** | ✅ **Resistant** |
        | **Algorithm Paradigm Change** | ✅ Distinct | ✅ Distinct | ✅ Distinct | ✅ **Distinct (Low Score)** |
        """
    )

    st.write("")
    st.markdown("### 🎯 Classification Thresholds")
    rows = [f"{badge_html(label)} &nbsp; <b>{lo:g}%</b> to <b>{hi:g}%</b>" if hi < 100 else f"{badge_html(label)} &nbsp; <b>{lo:g}%</b> to <b>100%</b>"
            for label, lo, hi in thresholds.ranges()]
    st.markdown("<br>".join(rows), unsafe_allow_html=True)

    note("Classification bands serve as forensic advisory flags. The final determination of academic dishonesty requires human evaluation of pedagogical context.")

    st.write("")
    st.markdown("### 🛠️ Technical Stack & Frameworks")
    c1, c2, c3 = st.columns(3)
    c1.markdown("- **Core Logic:** Python 3.12, `ast` module\n- **Vector Space:** `scikit-learn`, `scipy`\n- **Lexer:** Python standard `tokenize`")
    c2.markdown("- **Interactive UI:** Streamlit Web Framework\n- **Visualizations:** Plotly Interactive Graphs\n- **Syntax Styler:** Pygments Highlighting")
    c3.markdown("- **Testing:** Pytest Test Suite\n- **Data Structure:** NumPy, Pandas\n- **Security:** In-memory AST sandbox")

    st.markdown(
        """
        <div style="margin-top: 2rem; padding: 18px 24px; background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.3); border-radius: 14px;">
            <div style="font-weight: 700; color: #FFFFFF; font-size: 1.05rem; margin-bottom: 4px;">🎓 Capstone Presentation Credits</div>
            <div style="color: #94A3B8; font-size: 0.88rem; line-height: 1.6;">
                <b>Degree:</b> Bachelor of Technology (B.Tech) in Computer Science & Engineering<br>
                <b>Domain:</b> Program Analysis, Natural Language Processing & Software Engineering Forensics<br>
                <b>System Version:</b> 2.4-PRO (Ensemble AST Architecture)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
