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
        .roadmap-month { border-left: 3px solid #004aad; padding-left: 15px; margin-bottom: 12px; }
        .month-header { font-weight: bold; color: #004aad; font-size: 1.1em; }
        .grade-tag { background: #e8f0fe; color: #1967d2; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 10px; }
        .activity-item { font-size: 0.9em; margin-top: 4px; }
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
# 3. MASTER ROADMAP ENGINE
# ─────────────────────────────────────────────
def get_advanced_roadmap(start_class, start_month_name, intake_year, course_name):
    months_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    curr_m_idx = months_order.index(start_month_name)
    curr_year = datetime.datetime.now().year
    curr_class = int(start_class)
    
    # End goal: October of the year before intake
    end_year = intake_year - 1
    end_month_idx = 9 
    
    # Load Class-wise Flow Sheets
    flows = {}
    for c in [9, 10, 11, 12]:
        try: flows[c] = pd.read_csv(f"Class wise Tentative Flow .xlsx - Class {c}th.csv")
        except: flows[c] = None

    # Load Contest Sheets
    contest_file = "Olympiads.csv"
    if "CS" in course_name.upper() or "AI" in course_name.upper(): contest_file = "STEM-Coding.csv"
    elif "BUSINESS" in course_name.upper(): contest_file = "Business and Entrepreneur.csv"
    elif "FINANCE" in course_name.upper() or "ECON" in course_name.upper(): contest_file = "Finance and Economics.csv"
    
    try: df_exams = pd.read_csv(f"Undergrad - Contests_Olympiads for students.xlsx - {contest_file}")
    except: df_exams = None

    master_plan = []
    
    # Generate Month-by-Month loop
    temp_y, temp_m, temp_c = curr_year, curr_m_idx, curr_class
    while (temp_y < end_year) or (temp_y == end_year and temp_m <= end_month_idx):
        if temp_c > 12: break # Cap at Grade 12
        
        month_label = months_order[temp_m]
        month_data = {"month": month_label, "year": temp_y, "grade": temp_c, "tasks": []}
        
        # 1. Pull from Class-wise Flow
        if temp_c in flows and flows[temp_c] is not None:
            flow_df = flows[temp_c]
            # Match current month in the "Month" column of the CSV
            matches = flow_df[flow_df['Month'].str.contains(month_label[:3], na=False, case=False)]
            for _, row in matches.iterrows():
                task = row.get('Task Name', row.get('Phase', 'Academic Focus'))
                info = row.get('Additional Info', '')
                month_data['tasks'].append(f"📌 {task} {f'({info})' if pd.notna(info) else ''}")

        # 2. Pull Exams from Contest Sheets
        if df_exams is not None:
            regs = df_exams[df_exams['Month (Registration)'].str.contains(month_label[:3], na=False, case=False)]
            for _, r in regs.iterrows(): month_data['tasks'].append(f"📝 Registration: {r.iloc[0]}")
            
            tests = df_exams[df_exams['Month (Test)'].str.contains(month_label[:3], na=False, case=False)]
            for _, t in tests.iterrows(): month_data['tasks'].append(f"🏆 Exam Date: {t.iloc[0]}")

        # 3. Add Hard-coded Logic (Internships/Research)
        if month_label in ["June", "July"]:
            month_data['tasks'].append("💼 Strategic Internship Phase")
        if temp_c == 11 and month_label == "January":
            month_data['tasks'].append("🔬 Finalize Research Paper Topic")

        master_plan.append(month_data)
        
        # Increment
        temp_m += 1
        if temp_m > 11:
            temp_m = 0
            temp_y += 1
            temp_c += 1
            
    return master_plan

# ─────────────────────────────────────────────
# 4. PDF ENGINE
# ─────────────────────────────────────────────
def generate_roadmap_pdf(name, course, roadmap):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Ultimate Admissions Roadmap: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Target Course:</b> {course}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Roadmap Table
    table_data = [["Month / Year", "Grade", "Strategic Actions & Milestones"]]
    for m in roadmap:
        task_list = "\n".join(m['tasks']) if m['tasks'] else "General Profile Building"
        table_data.append([f"{m['month']} {m['year']}", f"Grade {m['grade']}", task_list])

    rt = Table(table_data, colWidths=[90, 60, 380])
    rt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0), colors.HexColor("#004aad")),
        ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
        ('GRID',(0,0),(-1,-1), 0.5, colors.grey),
        ('VALIGN',(0,0),(-1,-1), 'TOP'),
        ('FONTSIZE',(0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(rt)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 5. APP INTERFACE
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
        if st.button("Initialize Strategy"):
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
        # --- SCORE TRACKER ---
        st.subheader("🎯 Live Profile Tracker")
        if st.session_state.baseline_score is None:
            if st.button("🔴 Step 1: Lock Baseline Score"):
                st.session_state.baseline_score = current_score; st.rerun()
        else:
            if st.button("🔄 Reset Baseline"):
                st.session_state.baseline_score = None; st.rerun()

        m1, m2 = st.columns(2)
        if st.session_state.baseline_score is not None:
            m1.metric("Current Baseline", st.session_state.baseline_score)
            m2.metric("Strategic Target", current_score, delta=current_score - st.session_state.baseline_score)
        else:
            m1.metric("Current Score", current_score)

        st.divider()

        # --- ROADMAP ARCHITECT ---
        st.subheader("🚀 Roadmap Architect")
        with st.expander("Generate Strategic Timeline", expanded=True):
            c_cl = st.selectbox("Current Grade", [9, 10, 11, 12], index=2)
            c_mo = st.selectbox("Current Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
            i_yr = st.number_input("Intake Year", 2025, 2032, 2027)
            
            # Generate Roadmap in State
            roadmap = get_advanced_roadmap(c_cl, c_mo, i_yr, st.session_state.course)
            
            # Display Live
            for m in roadmap:
                if m['tasks']:
                    st.markdown(f"""<div class="roadmap-month">
                        <span class="month-header">{m['month']} {m['year']}</span>
                        <span class="grade-tag">Grade {m['grade']}</span>
                        <div class="activity-item">{"<br>".join(m['tasks'])}</div>
                    </div>""", unsafe_allow_html=True)

        # --- EXPORT ---
        if st.session_state.baseline_score is not None:
            st.divider()
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Pin", type="password")
            if st.button("Step 2: Generate & Download Full Roadmap"):
                if pin == "304":
                    pdf = generate_roadmap_pdf(st.session_state.name, st.session_state.course, roadmap)
                    st.download_button("📥 Download PDF Roadmap", data=pdf, file_name=f"{st.session_state.name}_Roadmap.pdf", mime="application/pdf")
                else:
                    st.error("Incorrect Pin")
