import streamlit as st
import pandas as pd
import io
import os
import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch

# ─────────────────────────────────────────────
# 1. APP CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="Uppseekers Admit AI", page_icon="Uppseekers Logo.png", layout="wide")

def apply_styles():
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #004aad; color: white; font-weight: bold; border: none; }
        .card { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eee; margin-bottom: 10px; }
        .roadmap-month { border-left: 3px solid #004aad; padding-left: 15px; margin-bottom: 10px; }
        .month-name { font-weight: bold; color: #004aad; font-size: 1.1em; }
        .activity-text { font-size: 0.95em; color: #333; }
        .score-box { background-color: #f0f2f6; padding: 8px; border-radius: 8px; text-align: center; border: 1px solid #d1d5db; }
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
    except: st.error("Files missing: Readiness"); st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except: st.error("Files missing: Benchmarking"); st.stop()

# ─────────────────────────────────────────────
# 3. STRATEGIC ROADMAP ENGINE
# ─────────────────────────────────────────────
def get_month_on_month_roadmap(current_class, current_month_name, intake_year, course_name):
    months_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    start_month_idx = months_order.index(current_month_name)
    start_year = datetime.datetime.now().year
    
    # Application deadline is October of the year before intake
    end_year = intake_year - 1
    end_month_idx = 9 # October
    
    # Generate list of all months
    all_months = []
    curr_m, curr_y, curr_c = start_month_idx, start_year, int(current_class)
    
    while (curr_y < end_year) or (curr_y == end_year and curr_m <= end_month_idx):
        all_months.append({
            "month": months_order[curr_m],
            "year": curr_y,
            "class": curr_c,
            "activities": []
        })
        curr_m += 1
        if curr_m > 11:
            curr_m = 0
            curr_y += 1
            curr_c += 1
    
    # Logic for activities
    total_len = len(all_months)
    num_internships = 2 if total_len > 24 else 1
    
    # Distribute Internships (Summer months: June/July)
    int_count = 0
    for m in all_months:
        if m['month'] in ["June", "July"] and int_count < num_internships:
            m['activities'].append(f"Internship Project #{int_count+1}")
            int_count += 1
            if int_count >= num_internships: break

    # Research Paper (Early on)
    if len(all_months) > 3:
        all_months[2]['activities'].append("Commence Research Paper (Topic Selection & Literature Review)")
        all_months[5]['activities'].append("Finalize Research Paper & Submit for Publication")

    # Application Phase (Final 6 Months)
    for i in range(max(0, total_len - 6), total_len):
        all_months[i]['activities'].append("Application Phase: SOP Drafting, LOR Collection, & Portal Filling")

    # Fetch Exams from CSV
    file_map = {"CS": "STEM-Coding.csv", "AI": "STEM-Coding.csv", "BUSINESS": "Business", "FINANCE": "Finance", "ECON": "Finance"}
    selected_file = "Olympiads.csv"
    for k, f in file_map.items():
        if k in course_name.upper():
            selected_file = f"Undergrad - Contests_Olympiads for students.xlsx - {f if 'csv' in f else f + '.csv'}"
            break
    
    try:
        df_exams = pd.read_csv(selected_file)
        for m in all_months:
            # Match Registration
            regs = df_exams[df_exams['Month (Registration)'].str.contains(m['month'], na=False, case=False)]
            for _, r in regs.iterrows(): m['activities'].append(f"📝 Register: {r['Contest Name']}")
            # Match Test
            tests = df_exams[df_exams['Month (Test)'].str.contains(m['month'], na=False, case=False)]
            for _, t in tests.iterrows(): m['activities'].append(f"🏆 Exam Date: {t['Contest Name']}")
    except: pass

    return all_months

# ─────────────────────────────────────────────
# 4. PDF GENERATOR
# ─────────────────────────────────────────────
def generate_pdf(name, baseline, strategic, bench_df, countries, counsellor, course, roadmap):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Strategic Admissions Roadmap: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Counsellor:</b> {counsellor} | <b>Planned Course:</b> {course}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Score Summary
    elements.append(Paragraph("Admissions Probability Summary", styles['Heading2']))
    score_data = [["Metric", "Baseline Score", "Strategic Score"], ["Total Profile Points", str(baseline), str(strategic)]]
    st_table = Table(score_data, colWidths=[200, 100, 100])
    st_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#004aad")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
    elements.append(st_table)
    elements.append(Spacer(1, 20))

    # Roadmap
    elements.append(Paragraph("Month-on-Month Strategic Execution Plan", styles['Heading2']))
    roadmap_data = [["Month/Year", "Grade", "Planned Activities"]]
    for m in roadmap:
        acts = " • " + "\n • ".join(m['activities']) if m['activities'] else "Standard Academic Prep"
        roadmap_data.append([f"{m['month']} {m['year']}", f"Grade {m['class']}", acts])
    
    rt = Table(roadmap_data, colWidths=[90, 60, 310])
    rt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.grey), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.black), ('VALIGN',(0,0),(-1,-1),'TOP'), ('FONTSIZE',(0,0),(-1,-1), 8)]))
    elements.append(rt)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 5. STREAMLIT UI
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
        if st.button("Start Assessment"):
            if name and countries:
                st.session_state.update({"name": name, "course": course, "countries": countries, "s_map": s_map, "page": 'analysis'})
                st.rerun()

elif st.session_state.page == 'analysis':
    xls, _ = load_data()
    bxls, b_map = load_benchmarking()
    df_q = xls.parse(st.session_state.s_map[st.session_state.course])
    bench_master = bxls.parse(b_map[st.session_state.course])

    st.title(f"Strategic Session: {st.session_state.name}")
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
        st.subheader("🎯 Strategy Dashboard")
        if st.session_state.baseline_score is None:
            if st.button("🔴 Step 1: Lock Baseline Profile"):
                st.session_state.baseline_score = current_score; st.rerun()
        else:
            if st.button("🔄 Reset Baseline"):
                st.session_state.baseline_score = None; st.rerun()

        m1, m2 = st.columns(2)
        if st.session_state.baseline_score is not None:
            m1.metric("Baseline", st.session_state.baseline_score)
            m2.metric("Strategic", current_score, delta=current_score - st.session_state.baseline_score)
        else: m1.metric("Current Score", current_score)

        st.divider()
        st.subheader("🚀 Roadmap Architect")
        c_cl = st.number_input("Current Grade", 8, 12, 11)
        c_mo = st.selectbox("Current Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        i_yr = st.number_input("Intake Year", 2025, 2030, 2027)
        
        roadmap = get_month_on_month_roadmap(c_cl, c_mo, i_yr, st.session_state.course)
        
        with st.expander("View Month-by-Month Plan", expanded=False):
            for m in roadmap:
                if m['activities']:
                    st.markdown(f"""<div class="roadmap-month"><span class="month-name">{m['month']} {m['year']} (Grade {m['class']})</span><br>
                                <span class="activity-text">{"<br>".join(m['activities'])}</span></div>""", unsafe_allow_html=True)

        if st.session_state.baseline_score is not None:
            st.divider()
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Pin", type="password")
            if st.button("Step 2: Generate & Download Final Roadmap"):
                if pin == "304":
                    pdf = generate_pdf(st.session_state.name, st.session_state.baseline_score, current_score, bench_master, st.session_state.countries, c_name, st.session_state.course, roadmap)
                    st.download_button("📥 Click to Download PDF", data=pdf, file_name=f"{st.session_state.name}_Strategic_Roadmap.pdf", mime="application/pdf")
                else: st.error("Incorrect Pin")
