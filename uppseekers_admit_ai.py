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
        .activity-item { font-size: 0.9em; margin-top: 4px; color: #444; }
        .gap-jump-box { background: #fff3e0; border: 1px solid #ffb74d; padding: 10px; border-radius: 8px; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA LOADERS
# ─────────────────────────────────────────────
def load_readiness():
    try:
        xls = pd.ExcelFile("University Readiness_new.xlsx")
        idx = xls.parse(xls.sheet_names[0])
        return xls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except: st.error("Readiness File Missing"); st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except: st.error("Benchmarking File Missing"); st.stop()

# ─────────────────────────────────────────────
# 3. POWER ROADMAP ENGINE
# ─────────────────────────────────────────────
def generate_power_roadmap(start_class, start_month, intake_year, course_name):
    months_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    curr_m_idx = months_order.index(start_month)
    curr_year, curr_class = datetime.datetime.now().year, int(start_class)
    end_year, end_month_idx = intake_year - 1, 9 # Oct Deadline
    
    # Load flows and contests
    flows = {c: pd.read_csv(f"Class wise Tentative Flow .xlsx - Class {c}th.csv") for c in [9, 10, 11, 12] if os.path.exists(f"Class wise Tentative Flow .xlsx - Class {c}th.csv")}
    
    c_file = "Olympiads.csv"
    if "CS" in course_name.upper(): c_file = "STEM-Coding.csv"
    elif "BUSINESS" in course_name.upper(): c_file = "Business and Entrepreneur.csv"
    elif "FINANCE" in course_name.upper(): c_file = "Finance and Economics.csv"
    df_exams = pd.read_csv(f"Undergrad - Contests_Olympiads for students.xlsx - {c_file}") if os.path.exists(f"Undergrad - Contests_Olympiads for students.xlsx - {c_file}") else None

    master_plan = []
    temp_y, temp_m, temp_c = curr_year, curr_m_idx, curr_class

    while (temp_y < end_year) or (temp_y == end_year and temp_m <= end_month_idx):
        if temp_c > 12: break
        m_label = months_order[temp_m]
        month_entry = {"month": m_label, "year": temp_y, "grade": temp_c, "tasks": []}
        
        # 1. Integration: Class Flow
        if temp_c in flows:
            match = flows[temp_c][flows[temp_c]['Month'].str.contains(m_label[:3], na=False, case=False)]
            for _, r in match.iterrows():
                month_entry['tasks'].append(f"📍 {r.get('Task Name', 'Academic Focus')} - {r.get('Outcome ', 'Goal')}")

        # 2. Integration: Contests (Strategic Spikes)
        if df_exams is not None:
            tests = df_exams[df_exams['Month (Test)'].str.contains(m_label[:3], na=False, case=False)]
            for _, t in tests.iterrows():
                month_entry['tasks'].append(f"🏆 PRIORITY EXAM: {t.iloc[0]} ({t.get('Impact in Admissions', 'High Impact')})")

        master_plan.append(month_entry)
        temp_m += 1
        if temp_m > 11:
            temp_m, temp_y, temp_c = 0, temp_y + 1, temp_c + 1
            
    return master_plan

# ─────────────────────────────────────────────
# 4. PDF DOWNLOAD ENGINE
# ─────────────────────────────────────────────
def generate_pdf_report(name, baseline, strategic, roadmap, course):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Strategic Roadmap: {name}", styles['Title']))
    elements.append(Paragraph(f"Course: {course} | Strategy Gap Jump: +{strategic - baseline} Points", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Month/Year", "Grade", "Strategic Actions"]]
    for m in roadmap:
        data.append([f"{m['month']} {m['year']}", f"G{m['grade']}", "\n".join(m['tasks']) if m['tasks'] else "Standard Prep"])

    t = Table(data, colWidths=[90, 50, 380])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#004aad")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey), ('VALIGN',(0,0),(-1,-1), 'TOP'), ('FONTSIZE',(0,0),(-1,-1), 7)]))
    elements.append(t)
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
        xls, s_map = load_readiness()
        course = st.selectbox("Interested Course", list(s_map.keys()))
        if st.button("Initialize Powerful Flow"):
            if name and countries:
                st.session_state.update({"name": name, "course": course, "countries": countries, "s_map": s_map, "page": 'analysis'})
                st.rerun()

elif st.session_state.page == 'analysis':
    xls, _ = load_readiness()
    bxls, b_map = load_benchmarking()
    df_q = xls.parse(st.session_state.s_map[st.session_state.course])
    bench_master = bxls.parse(b_map[st.session_state.course])

    st.title(f"Strategic Upward Movement: {st.session_state.name}")
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
        # --- SCORE & GAP JUMP ---
        st.subheader("🎯 Strategic Dashboard")
        if st.session_state.baseline_score is None:
            if st.button("🔴 Step 1: Lock Baseline Status"):
                st.session_state.baseline_score = current_score; st.rerun()
        else:
            if st.button("🔄 Reset Strategy"):
                st.session_state.baseline_score = None; st.rerun()

        if st.session_state.baseline_score is not None:
            gap_jump = current_score - st.session_state.baseline_score
            st.markdown(f'<div class="gap-jump-box"><b>GAP JUMP MOVEMENT</b><br><h2 style="margin:0;color:#e65100;">+{gap_jump} Points</h2></div>', unsafe_allow_html=True)
            st.metric("Strategic Target Score", current_score, delta=f"+{gap_jump}")
        else:
            st.metric("Current Profile Power", current_score)

        st.divider()

        # --- ROADMAP ARCHITECT ---
        st.subheader("🚀 Roadmap Architect")
        with st.expander("Configure Strategic Journey", expanded=True):
            c_cl = st.selectbox("Current Grade", [9, 10, 11, 12], index=2)
            c_mo = st.selectbox("Current Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
            i_yr = st.number_input("Intake Year", 2025, 2032, 2027)
            
            roadmap = generate_power_roadmap(c_cl, c_mo, i_yr, st.session_state.course)
            for m in roadmap:
                if m['tasks']:
                    st.markdown(f"""<div class="roadmap-month"><span class="month-header">{m['month']} {m['year']}</span><span class="grade-tag">G{m['grade']}</span>
                        <div class="activity-item">{"<br>".join(m['tasks'])}</div></div>""", unsafe_allow_html=True)

        # --- EXPORT ---
        if st.session_state.baseline_score is not None:
            st.divider()
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Pin", type="password")
            if st.button("Step 2: Generate Powerful Roadmap PDF"):
                if pin == "304":
                    pdf = generate_pdf_report(st.session_state.name, st.session_state.baseline_score, current_score, roadmap, st.session_state.course)
                    st.download_button("📥 Download PDF", data=pdf, file_name=f"{st.session_state.name}_Strategic_Flow.pdf", mime="application/pdf")
                else: st.error("Incorrect Pin")
