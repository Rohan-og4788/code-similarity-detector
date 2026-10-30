"""CodeSimilarity - Python code similarity & plagiarism analysis tool.

B.Tech Final Year Capstone Project.
Run with: streamlit run app.py
"""
import streamlit as st

from analyzer.similarity_engine import run_analysis
from components.comparison_view import render_comparison
from components.dashboard import render_about, render_dashboard, render_history, render_results
from components.sidebar import apply_pending_navigation, init_state, render_sidebar, request_navigation
from components.styles import inject_css, page_header
from components.upload_section import render_upload
from utils.sample_data import get_demo_files

st.set_page_config(
    page_title="CodeSimilarity · AST & Plagiarism Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
init_state()
apply_pending_navigation()
config, limits, settings_errors = render_sidebar()

page = st.session_state["nav_page"]

if page == "Dashboard":
    render_dashboard()
elif page == "New Analysis":
    render_upload(config, limits, settings_errors)
elif page == "Comparison Results":
    current = st.session_state["current"]
    if current is None:
        page_header("Forensic Similarity Results", "Comprehensive pairwise comparisons and AST structural metrics.")
        st.markdown(
            """
            <div style="background: rgba(17, 24, 39, 0.7); border: 1px dashed rgba(99,102,241,0.4); border-radius: 16px; padding: 36px; text-align: center; margin: 1.5rem 0;">
                <div style="font-size: 2.5rem; margin-bottom: 12px;">🔍</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size: 1.35rem; font-weight: 700; color: #FFFFFF; margin-bottom: 8px;">
                    No Active Analysis Loaded
                </div>
                <div style="color: #94A3B8; max-width: 500px; margin: 0 auto 24px auto; font-size: 0.92rem; line-height: 1.5;">
                    Upload Python submissions to run the pairwise similarity engine, or load the academic demo suite to preview results immediately.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("⚡ Run Showcase Demo Dataset (4 Files)", type="primary", width="stretch"):
                demo_files = get_demo_files()
                with st.spinner("Analyzing demo files with AST + TF-IDF + Token engines..."):
                    result = run_analysis(demo_files, config)
                st.session_state["current"] = result
                st.session_state["history"].insert(0, result)
                st.session_state["flash"] = "✅ Showcase demo completed: 4 student submissions compared across 6 unique pairs!"
                request_navigation("Comparison Results")
                st.rerun()
        with c2:
            st.button("📁 Go to New Submission Upload", type="secondary", width="stretch",
                      on_click=request_navigation, args=("New Analysis",))
    elif st.session_state["compare_mode"]:
        render_comparison(current)
    else:
        render_results(current)
elif page == "Analysis History":
    render_history()
else:
    render_about(config.thresholds)
