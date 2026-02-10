import streamlit as st
import pandas as pd
import io
import os
import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
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
        .roadmap-step { border-left: 4px solid #004aad; padding-left: 20px; margin-bottom: 20px; position: relative; }
        .roadmap-step::before { content: '●'; position: absolute; left: -10px; top: 0; color: #004aad; font-size: 18px; background: white; }
        .metric-card { background: #f8f9fa; padding: 10px; border-radius: 10px; border-top: 3px solid #004aad; text-align: center; }
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
# 3. ADVANCED EXAM & ROADMAP LOGIC
# ─────────────────────────────────────────────
def get_strategic_exams(course_name, current_month, current_class):
    # Determine which file to pull from
    file_map = {
        "CS": "STEM-Coding.csv", "AI": "STEM-Coding.csv",
        "BUSINESS": "Business and Entrepreneur.csv",
        "FINANCE": "Finance and Economics.csv", "ECON": "Finance and Economics.csv"
    }
    
    selected_file = "Olympiads.csv" # Default for general profiles
    for key, f_name in file_map.items():
        if key in course_name.upper():
            selected_file = f_name
            break
            
    try:
        df = pd.read_csv(f"Undergrad - Contests_Olympiads for students.xlsx - {selected_file}")
        
        # Filter logic: 
        # 1. Matches Class (assuming CSV has 'Best For Classes' like '9-12' or '11-12')
        # 2. Upcoming (Month of test is after current month)
        
        # Simplification for this logic: pick top 4 high-impact upcoming exams
        exams = []
        for _, row in df.iterrows():
            exams.append({
                "Name": row.get('Contest Name', row.get('Olympiad Name')),
                "Detail": row.get('Prep / Syllabus Focus', row.get('Subjects Covered')),
                "Reg": row.get('Month (Registration)', 'See Website'),
                "Test": row.get('Month (Test)', 'Varies'),
                "Impact": row.get('Impact in Admissions', 'High')
            })
        return exams[:4]
    except:
        return [{"Name": "AP Exams", "Detail": "Subject-specific rigor", "Reg": "Jan-Mar", "Test": "May", "Impact": "High"}]

def calculate_timeline(c_class, c_month, intake_year):
    months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    curr_idx = months_list.index(c_month)
    deadline_year = intake_year - 1
    current_year = datetime.datetime.now().year
    total_months = ((deadline_year - current_year) * 12) + (9 - curr_idx)
    return max(total_months, 0), deadline_year

# ─────────────────────────────────────────────
# 4. PDF GENERATION (Including Exam Details)
# ─────────────────────────────────────────────
def generate_pdf(name, baseline, strategic, bench_df, countries, counsellor, course, roadmap_info, exams):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Title & Profile
    elements.append(Paragraph(f"Admissions Strategy & Roadmap: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Planned Intake:</b> {roadmap_info['intake']} | <b>Months to Deadline:</b> {roadmap_info['months']}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Exam Roadmap Table
    elements.append(Paragraph("Recommended Profile-Building Exams", styles['Heading2']))
    exam_data = [["Exam Name", "Syllabus/Focus", "Registration", "Exam Month"]]
    for ex in exams:
        exam_data.append([ex['Name'], ex['Detail'], ex['Reg'], ex['Test']])
    
    et = Table(exam_data, colWidths=[140, 180, 80, 80])
    et.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#004aad")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    elements.append(et)
    elements.append(Spacer(1, 20))

    # University Targets (Filtered by Strategic Score)
    for country in countries:
        elements.append(Paragraph(f"Target Universities: {country}", styles['Heading2']))
        c_df = bench_df[bench_df["Country"] == country].copy() if "Country" in bench_df.columns else bench_df.copy()
        c_df["diff"] = c_df["Total Benchmark Score"] - strategic
        
        # Table helper
        def add_u_table(df, title, color):
            if not df.empty:
                elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
                u_rows = [["University", "Target Score", "Gap"]]
                for _, r in df.head(5).iterrows():
                    u_rows.append([r["University"], str(round(r["Total Benchmark Score"], 1)), str(round(r["Total Benchmark Score"] - strategic, 1))])
                ut = Table(u_rows, colWidths=[280, 70, 70])
                ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.black)]))
                elements.append(ut); elements.append(Spacer(1, 10))

        add_u_table(c_df[c_df["diff"] <= 0].sort_values("Total Benchmark Score", ascending=False), "Safe to Target", colors.darkgreen)
        add_u_table(c_df[(c_df["diff"] > 0) & (c_df["diff"] <= 15)], "Strengthening Required", colors.orange)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 5. STREAMLIT INTERFACE
# ─────────────────────────────────────────────
apply_styles()
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'baseline_score' not in st.session_state: st.session_state.baseline_score = None

if st.session_state.page == 'intro':
    st.title("🎓 Uppseekers Admit AI")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        name = st.text_input("Student Name")
        countries = st.multiselect("Preferred Countries", ["USA", "UK", "Canada", "Singapore", "Australia"], max_selections=3)
        xls, s_map = load_data()
        course = st.selectbox("Interested Course", list(s_map.keys()))
        if st.button("Start Analysis"):
            if name and countries:
                st.session_state.update({"name": name, "course": course, "countries": countries, "s_map": s_map, "page": 'analysis'})
                st.rerun()

elif st.session_state.page == 'analysis':
    xls, _ = load_data()
    bxls, b_map = load_benchmarking()
    df_q = xls.parse(st.session_state.s_map[st.session_state.course])
    bench_master = bxls.parse(b_map[st.session_state.course])

    st.title(f"Strategic Profile Builder: {st.session_state.name}")
    col_q, col_dash = st.columns([2, 1.2])

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
                sel = q_cols[0].selectbox(row['question_text'], opts, key=f"q{idx}")
                pts = v_map[sel]; current_score += pts
                q_cols[1].markdown(f'<div class="score-box">Points<br><b>{pts}</b></div>', unsafe_allow_html=True)

    with col_dash:
        st.subheader("🎯 Strategy Tracker")
        if st.session_state.baseline_score is None:
            if st.button("🔴 Lock Current Profile"):
                st.session_state.baseline_score = current_score; st.rerun()
        else:
            if st.button("🔄 Reset Baseline"):
                st.session_state.baseline_score = None; st.rerun()

        # Score Metrics
        m1, m2 = st.columns(2)
        if st.session_state.baseline_score is not None:
            m1.metric("Baseline", st.session_state.baseline_score)
            m2.metric("Strategic Score", current_score, delta=current_score - st.session_state.baseline_score)
        else:
            m1.metric("Current Score", current_score)

        st.divider()

        # Roadmap Configuration
        st.subheader("🚀 Roadmap Architect")
        with st.expander("Configure Timeline", expanded=True):
            c_cl = st.number_input("Current Grade", 8, 12, 11)
            c_mo = st.selectbox("Current Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
            i_yr = st.number_input("Intake Year", 2025, 2030, 2027)
            
            if st.button("Generate Roadmap & Exams"):
                months, d_year = calculate_timeline(c_cl, c_mo, i_yr)
                exams = get_strategic_exams(st.session_state.course, c_mo, c_cl)
                st.session_state.roadmap_data = {"months": months, "intake": i_yr, "deadline_year": d_year, "exams": exams}

        if 'roadmap_data' in st.session_state:
            rd = st.session_state.roadmap_data
            st.info(f"📅 **{rd['months']} Months** to Deadline (Oct {rd['deadline_year']})")
            
            st.markdown("### 🏆 Recommended Exams")
            for ex in rd['exams']:
                with st.container():
                    st.markdown(f"**{ex['Name']}**")
                    st.caption(f"📝 Reg: {ex['Reg']} | 📅 Test: {ex['Test']}")

        # Final Export
        if st.session_state.baseline_score is not None:
            st.divider()
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Pin", type="password")
            if st.button("Generate Final PDF"):
                if pin == "304":
                    pdf = generate_pdf(st.session_state.name, st.session_state.baseline_score, current_score, bench_master, st.session_state.countries, c_name, st.session_state.course, st.session_state.roadmap_data, st.session_state.roadmap_data['exams'])
                    st.download_button("📥 Download Strategic Roadmap", data=pdf, file_name=f"{st.session_state.name}_Roadmap.pdf", mime="application/pdf")
                else:
                    st.error("Incorrect Pin")
