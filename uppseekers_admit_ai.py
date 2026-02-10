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
        .card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eee; margin-bottom: 15px; }
        .score-box { background-color: #f0f2f6; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #d1d5db; }
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
    except Exception as e:
        st.error(f"File Error: University Readiness_new.xlsx ({e})")
        st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        mapping = {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
        return bxls, mapping
    except Exception as e:
        st.error(f"File Error: Benchmarking_USA.xlsx ({e})")
        st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATION
# ─────────────────────────────────────────────
def generate_pdf(name, s_class, course, score, responses, bench_df, countries, counsellor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    logo_path = "Uppseekers Logo.png"
    if os.path.exists(logo_path):
        try: elements.append(Image(logo_path, width=140, height=42))
        except: pass
    
    elements.append(Paragraph(f"Admit AI Analysis: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Course:</b> {course} | <b>Counsellor:</b> {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 15))

    def add_table(df, title, color):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            u_data = [["University", "Target Score", "Gap %"]]
            for _, row in df.sort_values("Score Gap %", ascending=False).head(5).iterrows():
                u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), f"{round(row['Score Gap %'], 1)}%"])
            ut = Table(u_data, colWidths=[300, 70, 80])
            ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
            elements.append(ut); elements.append(Spacer(1, 12))

    for country in countries:
        elements.append(Paragraph(f"Country: {country}", styles['Heading3']))
        c_df = bench_df[bench_df["Country"] == country] if "Country" in bench_df.columns else bench_df
        
        add_table(c_df[c_df["Score Gap %"] >= -2], f"Safe - {country}", colors.darkgreen)
        add_table(c_df[(c_df["Score Gap %"] < -2) & (c_df["Score Gap %"] >= -10)], f"Target - {country}", colors.orange)
        add_table(c_df[(c_df["Score Gap %"] < -10) & (c_df["Score Gap %"] >= -20)], f"Need Strengthening - {country}", colors.blue)
        add_table(c_df[c_df["Score Gap %"] < -20], f"Significant Gap - {country}", colors.red)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP INTERFACE
# ─────────────────────────────────────────────
apply_styles()
if 'page' not in st.session_state: st.session_state.page = 'intro'

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        country_list = ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"]
        pref_countries = st.multiselect("Preferred Countries", country_list, max_selections=3)
        xls, s_map = load_data()
        course = st.selectbox("Interested Course", list(s_map.keys()))
        
        if st.button("Start Analysis"):
            if name and pref_countries:
                st.session_state.update({"name": name, "course": course.strip(), "countries": pref_countries, "s_map": s_map, "page": 'questions'})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'questions':
    xls, _ = load_data()
    bxls, b_map = load_benchmarking()
    df = xls.parse(st.session_state.s_map[st.session_state.course])
    bench_master = bxls.parse(b_map[st.session_state.course])
    
    total_score, responses = 0, []
    
    st.title(f"Analysis for {st.session_state.name}")
    
    # QUESTION FLOW
    for idx, row in df.iterrows():
        with st.container():
            st.markdown(f'<div class="card">', unsafe_allow_html=True)
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"**{row['question_text']}**")
                opts = ["None / Not Selected"]
                v_map = {"None / Not Selected": 0}
                for c in 'ABCDE':
                    if pd.notna(row.get(f'option_{c}')):
                        label = f"{c}) {str(row[f'option_{c}']).strip()}"
                        opts.append(label); v_map[label] = row[f'score_{c}']
                sel = st.selectbox("Select Answer", opts, key=f"q{idx}", label_visibility="collapsed")
                current_q_score = v_map[sel]
                total_score += current_q_score
                responses.append((row['question_text'], sel, current_q_score))
            
            with col2:
                st.markdown(f'<div class="score-box">Score<br><b>{current_q_score}</b></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # SIDEBAR LIVE DASHBOARD
    with st.sidebar:
        st.header("📊 Live Profile Tracker")
        st.metric("Total Score", total_score)
        st.divider()
        
        for country in st.session_state.countries:
            st.subheader(f"📍 {country}")
            c_df = bench_master[bench_master["Country"] == country].copy() if "Country" in bench_master.columns else bench_master.copy()
            c_df["Score Gap %"] = ((total_score - c_df["Total Benchmark Score"]) / c_df["Total Benchmark Score"]) * 100
            
            # Counts
            s = len(c_df[c_df["Score Gap %"] >= -2])
            t = len(c_df[(c_df["Score Gap %"] < -2) & (c_df["Score Gap %"] >= -10)])
            ns = len(c_df[(c_df["Score Gap %"] < -10) & (c_df["Score Gap %"] >= -20)])
            sg = len(c_df[c_df["Score Gap %"] < -20])
            
            cols = st.columns(2)
            cols[0].write(f"✅ Safe: **{s}**")
            cols[1].write(f"🎯 Target: **{t}**")
            cols[0].write(f"💡 Strength: **{ns}**")
            cols[1].write(f"⚠️ Gap: **{sg}**")
            st.divider()

    if st.button("Finalize and Generate Report"):
        bench_master["Score Gap %"] = ((total_score - bench_master["Total Benchmark Score"]) / bench_master["Total Benchmark Score"]) * 100
        st.session_state.update({"total_score": total_score, "responses": responses, "bench_df": bench_master, "page": 'counsellor'})
        st.rerun()

elif st.session_state.page == 'counsellor':
    st.title("🛡️ Authorization")
    c_name = st.text_input("Counsellor Name")
    c_code = st.text_input("Access Pin", type="password")
    
    if st.button("Download 9-List Report"):
        if c_code == "304":
            pdf = generate_pdf(st.session_state.name, "12", st.session_state.course, st.session_state.total_score, st.session_state.responses, st.session_state.bench_df, st.session_state.countries, c_name)
            st.download_button("📥 Get PDF Report", data=pdf, file_name=f"{st.session_state.name}_Report.pdf")
