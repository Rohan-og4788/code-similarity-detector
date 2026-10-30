"""Plotly figures with modern dark aesthetics, smooth fonts, and glowing accents."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from analyzer.similarity_engine import METHOD_LABELS, AnalysisConfig, AnalysisResult, PairResult
from utils.helpers import Thresholds, fmt_score

METHOD_COLORS = {
    "token": "#6366F1",     # Indigo
    "tfidf": "#06B6D4",     # Cyan
    "ast": "#10B981",       # Emerald
    "combined": "#F59E0B",  # Amber
}

HEAT_SCALE = [
    [0.0, "#0B1020"],
    [0.2, "#1E1B4B"],
    [0.45, "#4338CA"],
    [0.7, "#6366F1"],
    [0.85, "#06B6D4"],
    [1.0, "#FDE68A"],
]


def _style(fig: go.Figure, height: int, title: str | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        title=dict(
            text=title or "",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=15, color="#F8FAFC", weight=700),
            x=0.01,
            y=0.96,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        font=dict(family="Inter, sans-serif", color="#CBD5E1", size=12),
        margin=dict(l=15, r=15, t=55 if title else 25, b=20),
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="rgba(99, 102, 241, 0.6)",
            font=dict(family="JetBrains Mono, monospace", size=12, color="#F8FAFC"),
        ),
    )
    return fig


def distribution_chart(scores: list[float], thresholds: Thresholds, title: str = "Similarity Distribution") -> go.Figure:
    fig = go.Figure(go.Histogram(
        x=scores,
        xbins=dict(start=0, end=100, size=5),
        marker=dict(
            color="#6366F1",
            line=dict(color="#818CF8", width=1),
        ),
        hovertemplate="Score Range: <b>%{x}%</b><br>Pairs: <b>%{y}</b><extra></extra>",
    ))
    
    # Clean dashed threshold lines without overlapping text annotations
    for val, color in [(thresholds.moderate, "#F59E0B"), (thresholds.high, "#F97316"), (thresholds.very_high, "#EF4444")]:
        fig.add_vline(
            x=val,
            line=dict(color=color, dash="dot", width=1.5),
        )
        
    fig.update_xaxes(
        range=[0, 100],
        title=dict(text="Combined Similarity Score (%)", font=dict(size=12, color="#94A3B8")),
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.1)",
    )
    fig.update_yaxes(
        title=dict(text="Number of File Pairs", font=dict(size=12, color="#94A3B8")),
        gridcolor="rgba(255, 255, 255, 0.06)",
        dtick=1 if scores and len(scores) < 10 else None,
    )
    return _style(fig, 340, title)


def similarity_heatmap(result: AnalysisResult, names: list[str], matrix: np.ndarray) -> go.Figure:
    """Symmetric matrix heatmap with an invisible click layer for pair selection."""
    n = len(names)
    text, hover = [], []
    for i in range(n):
        text_row, hover_row = [], []
        for j in range(n):
            value = matrix[i, j]
            text_row.append("" if np.isnan(value) else f"{value:.0f}%")
            if i == j:
                hover_row.append("Same File")
            else:
                p = result.pair(names[i], names[j])
                hover_row.append(" · ".join(
                    f"{METHOD_LABELS[m].split()[0]} {fmt_score(p.component(m))}" for m in result.config.enabled_methods()
                ) if p else "")
        text.append(text_row)
        hover.append(hover_row)
    z = np.where(np.isnan(matrix), None, matrix).tolist()

    fig = go.Figure(go.Heatmap(
        z=z,
        x=names,
        y=names,
        text=text,
        texttemplate="%{text}",
        textfont=dict(family="JetBrains Mono", size=12, color="#FFFFFF"),
        zmin=0,
        zmax=100,
        colorscale=HEAT_SCALE,
        customdata=hover,
        xgap=3,
        ygap=3,
        colorbar=dict(
            title="Similarity %",
            thickness=14,
            len=0.9,
            tickfont=dict(family="JetBrains Mono", size=10),
        ),
        hovertemplate="<b>%{y}</b> ↔ <b>%{x}</b><br>Combined: <b>%{z:.1f}%</b><br><span style='font-size:11px;color:#94A3B8'>%{customdata}</span><extra></extra>",
    ))
    
    xs = [names[j] for i in range(n) for j in range(n) if i != j and not np.isnan(matrix[i, j])]
    ys = [names[i] for i in range(n) for j in range(n) if i != j and not np.isnan(matrix[i, j])]
    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="markers",
        hoverinfo="skip",
        showlegend=False,
        marker=dict(size=max(14, min(48, 420 // max(n, 1))), opacity=0.001, color="#ffffff"),
    ))
    
    fig.update_yaxes(
        autorange="reversed",
        type="category",
        tickfont=dict(family="JetBrains Mono", size=11, color="#E2E8F0"),
    )
    fig.update_xaxes(
        type="category",
        side="top",
        tickfont=dict(family="JetBrains Mono", size=11, color="#E2E8F0"),
    )
    return _style(fig, max(380, 100 + 64 * n), "Pairwise Similarity Heatmap (Click any cell to inspect)")


def _labels(pair: PairResult, limit: int = 20) -> str:
    cut = lambda s: s if len(s) <= limit else s[: limit - 1] + "…"
    return f"{cut(pair.file_a)} ↔ {cut(pair.file_b)}"


def breakdown_chart(pairs: list[PairResult], config: AnalysisConfig, top_n: int = 8) -> go.Figure:
    """Grouped bars of every score component for highest-scoring pairs."""
    top = sorted((p for p in pairs if p.combined is not None), key=lambda p: p.combined, reverse=True)[:top_n]
    fig = go.Figure()
    for method in config.enabled_methods() + ["combined"]:
        name = "Combined" if method == "combined" else METHOD_LABELS[method]
        fig.add_trace(go.Bar(
            y=[_labels(p) for p in top],
            x=[getattr(p, method) for p in top],
            orientation="h",
            name=name,
            marker_color=METHOD_COLORS[method],
            hovertemplate="<b>%{y}</b><br>" + name + ": <b>%{x:.1f}%</b><extra></extra>",
        ))
    fig.update_xaxes(
        range=[0, 100],
        title=dict(text="Score Component (%)", font=dict(size=12, color="#94A3B8")),
        gridcolor="rgba(255, 255, 255, 0.06)",
    )
    fig.update_yaxes(
        autorange="reversed",
        tickfont=dict(family="JetBrains Mono", size=11, color="#E2E8F0"),
    )
    fig.update_layout(
        barmode="group",
        legend=dict(
            orientation="h",
            y=-0.22,
            font=dict(size=11, color="#CBD5E1"),
        ),
    )
    return _style(fig, max(340, 130 + 45 * len(top)), f"Multi-Engine Score Breakdown (Top {len(top)} Pairs)")


def pair_breakdown_chart(pair: PairResult, config: AnalysisConfig) -> go.Figure:
    weights = config.effective_weights()
    labels, values, colors = [], [], []
    for method in config.enabled_methods():
        labels.append(f"{METHOD_LABELS[method].replace(' similarity', '')} ({weights[method]:.0f}% wt)")
        values.append(pair.component(method))
        colors.append(METHOD_COLORS[method])
    labels.append("Combined Score")
    values.append(pair.combined)
    colors.append(METHOD_COLORS["combined"])
    
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[fmt_score(v) for v in values],
        textposition="inside",
        textfont=dict(family="JetBrains Mono", size=11, color="#FFFFFF"),
        hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(
        range=[0, 100],
        gridcolor="rgba(255, 255, 255, 0.06)",
        title=dict(text="Calculated Similarity (%)", font=dict(size=11, color="#94A3B8")),
    )
    fig.update_yaxes(
        autorange="reversed",
        tickfont=dict(family="JetBrains Mono", size=11, color="#E2E8F0"),
    )
    return _style(fig, 260, "Engine Metric Breakdown")
