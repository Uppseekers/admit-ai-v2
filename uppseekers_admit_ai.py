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
        .score-box { background-color: #f0f2f6; padding: 8px; border-radius: 8px; text-align: center; border: 1px solid #d1d5db; font-size: 1em; }
        .st-emotion-cache-16idsys p { font-size: 1.1rem; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADERS
# ─────────────────────────────────────────────
def load_data():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        idx = xls.parse(xls.sheet_names[0])
        mapping = {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
        return xls, mapping
    except: st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        mapping = {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
        return bxls, mapping
    except: st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATION
# ─────────────────────────────────────────────
def generate_pdf(name, score, bench_df, countries, counsellor, mode_label):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Admit AI {mode_label}: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor} | <b>Total Score:</b> {round(score, 1)}", styles['Normal']))
    elements.append(Spacer(1, 20))

    def add_table(df, title, color, limit):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            u_data = [["University", "Target Score", "Gap Points"]]
            for _, row in df.head(limit).iterrows():
                u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), str(round(row["Total Benchmark Score"] - score, 1))])
            ut = Table(u_data, colWidths=[300, 70, 80])
            ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
            elements.append(ut); elements.append(Spacer(1, 12))

    for country in countries:
        c_df = bench_df[bench_df["Country"] == country].copy() if "Country" in bench_df.columns else bench_df.copy()
        c_df["diff"] = c_df["Total Benchmark Score"] - score
        
        add_table(c_df[c_df["diff"] <= 0].sort_values("Total Benchmark Score", ascending=False), f"Safe to Target - {country}", colors.darkgreen, 5)
        add_table(c_df[(c_df["diff"] > 0) & (c_df["diff"] <= 15)].sort_values("Total Benchmark Score"), f"Strengthening Required - {country}", colors.orange, 10)
        add_table(c_df[(c_df["diff"] > 15) & (c_df["diff"] <= 30)].sort_values("Total Benchmark Score"), f"Significant Gap - {country}", colors.red, 10)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP INTERFACE
# ─────────────────────────────────────────────
apply_styles()
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'calculated' not in st.session_state: st.session_state.calculated = False

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        pref_countries = st.multiselect("Preferred Countries", ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"], max_selections=3)
        xls, s_map = load_data()
        course = st.selectbox("Interested Course", list(s_map.keys()))
        if st.button("Start Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "course": course.strip(), "countries": pref_countries, "s_map": s_map, "page": 'analysis'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'analysis':
    xls, _ = load_data()
    bxls, b_map = load_benchmarking()
    df_questions = xls.parse(st.session_state.s_map[st.session_state.course])
    bench_master = bxls.parse(b_map[st.session_state.course])

    st.title(f"Strategic Profile Analysis: {st.session_state.name}")
    
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📋 Profile Assessment")
        current_total = 0
        for idx, row in df_questions.iterrows():
            with st.markdown('<div class="card">', unsafe_allow_html=True):
                q_col, s_col = st.columns([4, 1])
                opts = ["None / Not Selected"]
                v_map = {"None / Not Selected": 0}
                for c in 'ABCDE':
                    if pd.notna(row.get(f'option_{c}')):
                        label = f"{c}) {str(row[f'option_{c}']).strip()}"
                        opts.append(label); v_map[label] = row[f'score_{c}']
                
                sel = q_col.selectbox(row['question_text'], opts, key=f"q{idx}")
                pts = v_map[sel]
                current_total += pts
                s_col.markdown(f'<div class="score-box">Points<br><b>{pts}</b></div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div style="position: sticky; top: 2rem;">', unsafe_allow_html=True)
        st.subheader("🎯 Strategic Dashboard")
        
        # 1. Base Score
        st.metric("Current Profile Score", current_total)
        
        # 2. Strategic Tuning (Counsellor Only)
        st.divider()
        st.markdown("### 🛠️ Counsellor Tuning")
        tuning_score = st.slider("Additional Points (Improvement Plan)", 0, 30, 0, help="Simulate score improvement through strategic planning")
        
        final_score = current_total + tuning_score
        if tuning_score > 0:
            st.success(f"Strategic Score: **{final_score}** (+{tuning_score} improvement)")
        
        # 3. Dynamic Results
        for country in st.session_state.countries:
            with st.expander(f"📍 {country} Matches", expanded=True):
                c_df = bench_master[bench_master["Country"] == country].copy() if "Country" in bench_master.columns else bench_master.copy()
                c_df["diff"] = c_df["Total Benchmark Score"] - final_score
                
                st_c = len(c_df[c_df["diff"] <= 0])
                sr_c = len(c_df[(c_df["diff"] > 0) & (c_df["diff"] <= 15)])
                sg_c = len(c_df[(c_df["diff"] > 15) & (c_df["diff"] <= 30)])
                
                st.write(f"✅ **Safe to Target:** {st_c}")
                st.write(f"💡 **Strengthening Req:** {sr_c}")
                st.write(f"⚠️ **Significant Gap:** {sg_c}")

        st.divider()
        c_name = st.text_input("Counsellor Name")
        c_pin = st.text_input("Pin", type="password")
        
        if st.button("Generate Strategic Report"):
            if c_pin == "304":
                mode = "Strategic Plan" if tuning_score > 0 else "Current Status"
                pdf = generate_pdf(st.session_state.name, final_score, bench_master, st.session_state.countries, c_name, mode)
                st.download_button("📥 Download PDF Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
            else:
                st.error("Invalid Pin")
        st.markdown('</div>', unsafe_allow_html=True)
