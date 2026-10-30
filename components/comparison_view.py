"""Detailed two-file forensic comparison page with side-by-side code diff and AST breakdowns."""
from __future__ import annotations

import html
import pandas as pd
import streamlit as st

from analyzer.code_comparator import MAX_VIEW_LINES, build_diff, explain_pair, highlight_lines, render_diff_html
from analyzer.similarity_engine import AnalysisResult
from components.charts import pair_breakdown_chart
from components.styles import card, card_row, note, page_header
from utils.helpers import badge_html, fmt_score


def _back() -> None:
    st.session_state["compare_mode"] = False
    st.session_state["matrix_nonce"] += 1  # resets the heatmap selection


def _data(result: AnalysisResult, name_a: str, name_b: str) -> dict:
    key = (result.analysis_id, name_a, name_b)
    cached = st.session_state.get("_cmp_cache")
    if cached and cached["key"] == key:
        return cached["data"]
    a, b = result.file(name_a), result.file(name_b)
    pair = result.pair(name_a, name_b)
    diff = build_diff(a.text, b.text)
    clip = lambda text: "\n".join(text.split("\n")[:MAX_VIEW_LINES])
    data = {
        "pair": pair,
        "diff": diff,
        "explain": explain_pair(a, b, pair, diff),
        "table": render_diff_html(diff.rows, highlight_lines(clip(a.text)), highlight_lines(clip(b.text))),
    }
    st.session_state["_cmp_cache"] = {"key": key, "data": data}
    return data


def render_comparison(result: AnalysisResult) -> None:
    names = [f.name for f in result.analyzed_files]
    page_header("Pairwise Code Forensics", "Detailed syntactic and structural code comparison for two submissions.")
    st.button("← Back to Results Registry", on_click=_back, type="secondary")

    if len(names) < 2:
        st.warning("At least two analyzed files are required for comparison.")
        return

    if st.session_state.get("cmp_a") not in names:
        st.session_state["cmp_a"] = names[0]
    if st.session_state.get("cmp_b") not in names:
        st.session_state["cmp_b"] = names[1]

    c1, c2 = st.columns(2)
    name_a = c1.selectbox("Submission A (Reference)", names, key="cmp_a")
    name_b = c2.selectbox("Submission B (Comparison)", names, key="cmp_b")
    if name_a == name_b:
        st.warning("Select two distinct submissions to compare.")
        return

    data = _data(result, name_a, name_b)
    pair, diff, info = data["pair"], data["diff"], data["explain"]
    cfg = result.config
    esc = html.escape

    # Pair Title Banner
    st.markdown(
        f'<div class="cs-pairhead">'
        f'<span>📄 {esc(name_a)}</span><span class="sep"> ⟷ </span><span>📄 {esc(name_b)}</span>'
        f'{badge_html(pair.classification)}</div>',
        unsafe_allow_html=True,
    )

    off = lambda m, v: fmt_score(v) if m in cfg.enabled_methods() else "Engine Off"
    card_row([
        card("Combined Score", fmt_score(pair.combined), "Multi-engine weighted index", "🎯"),
        card("Token Alignment", off("token", pair.token), "Lexical sequence match", "🔠"),
        card("TF-IDF Vector", off("tfidf", pair.tfidf), "Vocabulary cosine distance", "📊"),
        card("AST Structural", off("ast", pair.ast), "Syntax tree subtree overlap", "🌲"),
        card("Matching Lines", fmt_score(diff.line_similarity), "Exact text without comments", "📝"),
    ])
    st.write("")

    for line in info["notes"]:
        note(line)

    left, right = st.columns([2, 3])
    left.plotly_chart(pair_breakdown_chart(pair, cfg), width="stretch", key="cmp_breakdown")
    with right:
        st.markdown("#### 🔬 Forensic Interpretation")
        st.markdown(
            """
            - **Token & TF-IDF Scores:** Measure vocabulary overlap and word distribution. A high token score indicates identical function signatures and identifier naming.
            - **AST Score:** Compares the underlying syntax tree (loops, conditions, statements, logic trees). A **high AST score paired with a lower text match** is a classic sign of **identifier renaming plagiarism**.
            - **Line Match:** Identifies exact physical lines replicated verbatim.
            """
        )

    st.markdown("### 🖥️ Side-by-Side Synchronized Code Diff")
    st.markdown(
        '<div class="cs-legend">'
        '<span><i style="background:rgba(16,185,129,.7)"></i> Matching Line (Identical Logic)</span>'
        '<span><i style="background:rgba(245,158,11,.7)"></i> Modified / Substituted Line</span>'
        '<span><i style="background:rgba(239,68,68,.7)"></i> Unique to Submission A</span>'
        '<span><i style="background:rgba(6,182,212,.7)"></i> Unique to Submission B</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    h1, h2 = st.columns(2)
    h1.markdown(f"**Submission A:** `{esc(name_a)}`")
    h2.markdown(f"**Submission B:** `{esc(name_b)}`")

    st.markdown(data["table"], unsafe_allow_html=True)
    if diff.truncated:
        st.caption(f"Note: Display capped at the first {MAX_VIEW_LINES} lines per submission in the viewer.")

    st.write("")
    st.markdown("### 🔍 Forensic Deep-Dive Evidence")

    tab1, tab2, tab3, tab4 = st.tabs(["🔤 Lexical Overlaps", "🌲 AST Structural Matches", "🧩 Cloned Fragments", "⚠️ Architectural Differences"])

    with tab1:
        st.markdown(f"**Shared Vocabulary:** `{info['shared_vocabulary_pct']}%` of unique tokens exist in both submissions.")
        if info["common_tokens"]:
            st.dataframe(pd.DataFrame(info["common_tokens"], columns=["Token Keyword/Name", "Shared Frequency"]),
                         hide_index=True, width="stretch")
        else:
            st.info("No significant shared vocabulary found.")

    with tab2:
        if info["structure"]:
            st.dataframe(pd.DataFrame(info["structure"]), hide_index=True, width="stretch")
        else:
            st.info("No structural AST subtree collisions detected.")

    with tab3:
        if not info["fragments"]:
            st.info("No consecutive block of 3+ identical code lines detected.")
        else:
            st.caption(f"Detected **{len(info['fragments'])}** verbatim replicated code block(s).")
            for idx, frag in enumerate(info["fragments"][:10], start=1):
                st.markdown(f"**Block #{idx}:** `{name_a}` line {frag['start_a']} ↔ `{name_b}` line {frag['start_b']} ({frag['line_count']} consecutive lines)")
                st.code(frag["code"], language="python")

    with tab4:
        if info["differences"]:
            for line in info["differences"]:
                st.markdown(f"• {line}")
        else:
            st.write("No major syntactic discrepancies identified.")

        if info["limitations"]:
            st.write("")
            st.caption("**Analysis Limitations:**")
            for line in info["limitations"]:
                st.caption(f"• {line}")
