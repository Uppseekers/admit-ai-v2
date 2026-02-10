import streamlit as st
import pandas as pd
import io
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 1. APP CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #004aad; color: white; font-weight: bold; border: none; }
        .card { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eee; margin-bottom: 10px; }
        .score-box { background-color: #f0f2f6; padding: 8px; border-radius: 8px; text-align: center; border: 1px solid #d1d5db; }
        .baseline-metric { color: #666; font-size: 0.9em; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADERS
# ─────────────────────────────────────────────
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        idx = xls.parse(xls.sheet_names[0])
        return xls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except: st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except: st.stop()

# ─────────────────────────────────────────────
# 3. APP LOGIC & INTERFACE
# ─────────────────────────────────────────────
apply_styles()

if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'baseline_score' not in st.session_state: st.session_state.baseline_score = None

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        countries = st.multiselect("Preferred Countries", ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"], max_selections=3)
        xls, s_map = load_data()
        course = st.selectbox("Interested Course", list(s_map.keys()))
        if st.button("Start Analysis"):
            if name and countries:
                st.session_state.update({"name": name, "course": course, "countries": countries, "s_map": s_map, "page": 'analysis'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'analysis':
    xls, _ = load_data()
    bxls, b_map = load_benchmarking()
    df_q = xls.parse(st.session_state.s_map[st.session_state.course])
    bench_master = bxls.parse(b_map[st.session_state.course])

    st.title(f"Strategic Session: {st.session_state.name}")
    
    col_q, col_dash = st.columns([2, 1])

    # --- LEFT COLUMN: QUESTIONS ---
    with col_q:
        current_score = 0
        for idx, row in df_q.iterrows():
            with st.markdown('<div class="card">', unsafe_allow_html=True):
                q_cols = st.columns([4, 1])
                opts = ["None / Not Selected"]
                v_map = {"None / Not Selected": 0}
                for c in 'ABCDE':
                    if pd.notna(row.get(f'option_{c}')):
                        label = f"{c}) {str(row[f'option_{c}']).strip()}"
                        opts.append(label); v_map[label] = row[f'score_{c}']
                
                # Check if we should disable inputs (optional, but here we keep them open for tuning)
                sel = q_cols[0].selectbox(row['question_text'], opts, key=f"q{idx}")
                pts = v_map[sel]
                current_score += pts
                q_cols[1].markdown(f'<div class="score-box">Points<br><b>{pts}</b></div>', unsafe_allow_html=True)

    # --- RIGHT COLUMN: DASHBOARD ---
    with col_dash:
        st.subheader("📊 Live Strategy Tracker")
        
        # Action Button 1: Save Baseline
        if st.session_state.baseline_score is None:
            if st.button("🔴 Step 1: Lock Current Profile Score"):
                st.session_state.baseline_score = current_score
                st.rerun()
        else:
            if st.button("🔄 Reset Baseline"):
                st.session_state.baseline_score = None
                st.rerun()

        # Display Metrics
        s1, s2 = st.columns(2)
        if st.session_state.baseline_score is not None:
            s1.metric("Baseline Score", st.session_state.baseline_score)
            delta = current_score - st.session_state.baseline_score
            s2.metric("Strategic Score", current_score, delta=delta)
        else:
            s1.metric("Current Score", current_score)

        st.divider()

        # Country Results
        for country in st.session_state.countries:
            with st.expander(f"📍 {country} Targets", expanded=True):
                c_df = bench_master[bench_master["Country"] == country].copy() if "Country" in bench_master.columns else bench_master.copy()
                c_df["diff"] = c_df["Total Benchmark Score"] - current_score
                
                st_count = len(c_df[c_df["diff"] <= 0])
                sr_count = len(c_df[(c_df["diff"] > 0) & (c_df["diff"] <= 15)])
                sg_count = len(c_df[(c_df["diff"] > 15) & (c_df["diff"] <= 30)])
                
                st.markdown(f"✅ **Safe to Target:** {st_count}")
                st.markdown(f"💡 **Strengthening Req:** {sr_count}")
                st.markdown(f"⚠️ **Significant Gap:** {sg_count}")

        # Action Button 2: Generate Report
        if st.session_state.baseline_score is not None:
            st.divider()
            st.subheader("🔒 Finalize Report")
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Access Pin", type="password")
            
            if st.button("Generate & Download PDF"):
                if pin == "304":
                    # (Note: In your actual code, include the generate_pdf function here)
                    st.success("Report Generated! Click below to save.")
                    # Temporary mock for download:
                    st.download_button("📥 Click to Download PDF", data=b"PDF Content", file_name="Report.pdf")
                else:
                    st.error("Incorrect Pin")
