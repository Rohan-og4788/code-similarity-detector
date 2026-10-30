"""Modern, high-performance UI design system and components for CodeSimilarity.

Tailored for a professional B.Tech Computer Science Final Year Capstone Project.
Features glassmorphic dark theme, Google Fonts, glowing accent tokens,
and robust spacing that prevents any text collisions or icon ligature breaking.
"""
from __future__ import annotations

import html
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-base: #0B0F19;
    --bg-surface: #111827;
    --bg-card: rgba(17, 24, 39, 0.75);
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-accent: rgba(99, 102, 241, 0.4);
    --line: #1F2937;
    
    --primary: #6366F1;
    --primary-glow: rgba(99, 102, 241, 0.25);
    --cyan: #06B6D4;
    --cyan-glow: rgba(6, 182, 212, 0.25);
    --emerald: #10B981;
    --emerald-glow: rgba(16, 185, 129, 0.25);
    --amber: #F59E0B;
    --amber-glow: rgba(245, 158, 11, 0.25);
    --rose: #EF4444;
    --rose-glow: rgba(239, 68, 68, 0.25);
    
    --text-title: #FFFFFF;
    --text-body: #E2E8F0;
    --text-muted: #94A3B8;
    --text-faint: #64748B;
}

/* Apply Inter font ONLY to standard text containers, NEVER to internal icon classes */
html, body, p, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText, .stCaption, input, textarea, button, select {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--text-body);
}

/* CRITICAL: Protect Streamlit and Material icons from having font overridden into plain text ligatures */
[data-testid="stIconMaterial"], 
.material-symbols-rounded, 
.material-icons,
[class*="material-symbols"],
span[data-testid="stIconMaterial"],
i[class*="st-"] {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    font-feature-settings: 'liga' 1 !important;
    font-style: normal !important;
    display: inline-block !important;
    line-height: 1 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    word-wrap: normal !important;
    white-space: nowrap !important;
    direction: ltr !important;
}

.stApp {
    background-color: var(--bg-base);
    background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.07) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.04) 0px, transparent 50%);
}

.block-container {
    padding-top: 1.8rem;
    padding-bottom: 3.5rem;
    max-width: 1320px;
}

/* Academic Project Tag */
.cs-academic-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.35);
    color: #A5B4FC;
    padding: 3px 12px;
    border-radius: 9999px;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
    box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);
}

/* Page Headers */
.cs-header-wrap {
    margin-bottom: 1.4rem;
    position: relative;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

h1.cs-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: clamp(1.6rem, 2.5vw, 2.1rem);
    font-weight: 800;
    margin: 0;
    line-height: 1.25;
    letter-spacing: -0.02em;
    color: #FFFFFF;
}

p.cs-sub {
    color: var(--text-muted);
    font-size: 0.92rem;
    margin: 0.35rem 0 0 0;
    line-height: 1.5;
}

/* Modern Glass Metric Cards */
.cs-card {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle);
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 14px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 104px;
    height: 100%;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.35);
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.cs-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--primary), var(--cyan));
    opacity: 0.6;
    transition: opacity 0.25s ease;
}

.cs-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-2px);
    box-shadow: 0 10px 24px -4px rgba(0, 0, 0, 0.5), 0 0 14px var(--primary-glow);
}

.cs-card:hover::before {
    opacity: 1;
}

.cs-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}

.cs-label {
    color: var(--text-muted);
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    line-height: 1.3;
}

.cs-icon {
    font-size: 1.05rem;
    opacity: 0.9;
    flex-shrink: 0;
}

.cs-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: clamp(1.4rem, 2.2vw, 1.85rem);
    font-weight: 800;
    margin: 2px 0;
    color: #FFFFFF;
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.cs-hint {
    color: var(--text-faint);
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.3;
}

/* Feature & Architecture Card */
.cs-feature-card {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px 18px;
    transition: all 0.2s ease;
    height: 100%;
}

.cs-feature-card:hover {
    border-color: rgba(99, 102, 241, 0.4);
    background: rgba(22, 31, 50, 0.85);
    transform: translateY(-2px);
}

.cs-feature-icon {
    font-size: 1.5rem;
    margin-bottom: 8px;
    display: inline-block;
}

.cs-feature-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 6px;
    line-height: 1.3;
}

.cs-feature-desc {
    color: var(--text-muted);
    font-size: 0.84rem;
    line-height: 1.5;
}

/* Hero Showcase Banner */
.cs-hero {
    background: linear-gradient(135deg, rgba(30, 27, 75, 0.5) 0%, rgba(15, 23, 42, 0.85) 60%, rgba(6, 78, 59, 0.2) 100%);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 18px;
    padding: 24px 28px;
    margin-bottom: 1.75rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.cs-hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    background: rgba(99, 102, 241, 0.18);
    border: 1px solid rgba(99, 102, 241, 0.4);
    color: #C7D2FE;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 600;
    margin-bottom: 10px;
}

.cs-hero-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: clamp(1.4rem, 2.2vw, 1.8rem);
    font-weight: 800;
    color: #FFFFFF;
    margin: 0 0 8px 0;
    line-height: 1.3;
    letter-spacing: -0.02em;
}

.cs-hero-desc {
    color: #CBD5E1;
    font-size: 0.94rem;
    max-width: 820px;
    line-height: 1.55;
    margin: 0 0 14px 0;
}

.cs-tag-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.cs-tag {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94A3B8;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.76rem;
    font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
}

/* Classification Badges */
.cs-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--c);
    border: 1px solid var(--c);
    background: color-mix(in srgb, var(--c) 14%, transparent);
    box-shadow: 0 0 10px color-mix(in srgb, var(--c) 20%, transparent);
    white-space: nowrap;
}

.cs-badge::before {
    content: '';
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: var(--c);
    box-shadow: 0 0 6px var(--c);
}

/* Callouts / Notes */
.cs-note {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-left: 4px solid var(--amber);
    border-radius: 10px;
    padding: 10px 16px;
    color: #E2E8F0;
    font-size: 0.86rem;
    line-height: 1.5;
    margin: 0.65rem 0 1rem 0;
}

.cs-info-box {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-left: 4px solid var(--primary);
    border-radius: 10px;
    padding: 10px 16px;
    color: #E2E8F0;
    font-size: 0.86rem;
    line-height: 1.5;
    margin: 0.65rem 0 1rem 0;
}

/* Pair Header */
.cs-pairhead {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0.75rem 0 1rem 0;
    padding: 10px 16px;
    background: rgba(17, 24, 39, 0.6);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
}

.cs-pairhead span.sep {
    color: var(--cyan);
    font-weight: 800;
}

/* Diff Viewer */
.cs-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 8px;
    background: rgba(15, 23, 42, 0.6);
    padding: 8px 14px;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
}

.cs-legend span {
    display: inline-flex;
    align-items: center;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-muted);
}

.cs-legend i {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 3px;
    margin-right: 6px;
}

.cs-diff-wrap {
    max-height: 640px;
    overflow: auto;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    background: #0A0F1D;
    box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.5);
}

table.cs-diff {
    border-collapse: collapse;
    width: 100%;
    min-width: 1100px;
    table-layout: fixed;
    font-family: "JetBrains Mono", Consolas, monospace;
    font-size: 12.5px;
    line-height: 1.6;
}

table.cs-diff td {
    padding: 1px 10px;
    vertical-align: top;
    border: 0;
}

table.cs-diff td.no {
    width: 50px;
    text-align: right;
    color: #64748B;
    user-select: none;
    background: rgba(0, 0, 0, 0.25);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

table.cs-diff td.code {
    white-space: pre;
    overflow: hidden;
    text-overflow: clip;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

table.cs-diff tr.match td.code {
    background: rgba(16, 185, 129, 0.16);
    color: #A7F3D0;
}

table.cs-diff tr.changed td.code {
    background: rgba(245, 158, 11, 0.18);
    color: #FDE68A;
}

table.cs-diff tr.left_only td.code {
    background: rgba(239, 68, 68, 0.18);
    color: #FECDD3;
}

table.cs-diff tr.right_only td.code {
    background: rgba(6, 182, 212, 0.18);
    color: #CFFAFE;
}

table.cs-diff tr.left_only td:nth-child(3), table.cs-diff tr.left_only td:nth-child(4),
table.cs-diff tr.right_only td:nth-child(1), table.cs-diff tr.right_only td:nth-child(2) {
    background: transparent;
}

/* Custom Streamlit Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
}

/* Custom Scrollbars */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #0B0F19;
}
::-webkit-scrollbar-thumb {
    background: #1F2937;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #374151;
}
</style>
"""


def inject_css() -> None:
    """Inject custom styles into Streamlit page."""
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, tag: str = "Capstone Project · CSE") -> None:
    """Standardized professional page header with academic project tag."""
    tag_html = f'<div class="cs-academic-tag">🎓 {html.escape(tag)}</div>' if tag else ""
    st.markdown(
        f'<div class="cs-header-wrap">{tag_html}'
        f'<h1 class="cs-title">{html.escape(title)}</h1>'
        f'<p class="cs-sub">{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def card(label: str, value: str, hint: str = "", icon: str = "") -> str:
    """One metric card as an HTML string with optional icon and hint."""
    icon_html = f'<span class="cs-icon">{icon}</span>' if icon else ""
    hint_html = f'<div class="cs-hint">{html.escape(hint)}</div>' if hint else ""
    return (
        f'<div class="cs-card">'
        f'<div class="cs-card-header">'
        f'<div class="cs-label">{html.escape(label)}</div>{icon_html}</div>'
        f'<div class="cs-value">{html.escape(value)}</div>{hint_html}</div>'
    )


def card_row(cards: list[str]) -> None:
    """Render a row of metric cards evenly across columns."""
    columns = st.columns(len(cards))
    for column, content in zip(columns, cards):
        column.markdown(content, unsafe_allow_html=True)


def note(text: str) -> None:
    """Review note / caveat alert box."""
    st.markdown(f'<div class="cs-note">💡 <b>Forensic Caveat:</b> {html.escape(text)}</div>', unsafe_allow_html=True)


def info_box(text: str) -> None:
    """Informational box."""
    st.markdown(f'<div class="cs-info-box">ℹ️ {html.escape(text)}</div>', unsafe_allow_html=True)


def hero_banner(title: str, description: str, tags: list[str] | None = None) -> None:
    """Showcase hero container for presentations and main dashboard."""
    tags = tags or ["Python 3.12 AST", "TF-IDF Vectorizer", "Token Levenshtein", "Identifier Masking"]
    tag_html = "".join(f'<span class="cs-tag">{html.escape(t)}</span>' for t in tags)
    st.markdown(
        f'<div class="cs-hero">'
        f'<div class="cs-hero-badge">⚡ Advanced Multi-Engine Plagiarism Detection System</div>'
        f'<h2 class="cs-hero-title">{html.escape(title)}</h2>'
        f'<p class="cs-hero-desc">{html.escape(description)}</p>'
        f'<div class="cs-tag-group">{tag_html}</div></div>',
        unsafe_allow_html=True,
    )
