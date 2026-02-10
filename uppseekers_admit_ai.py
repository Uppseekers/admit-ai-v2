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
        .score-box { background-color: #f0f2f6; padding: 8px; border-radius: 8px; text-align: center; border: 1px solid #d1d5db; }
        .roadmap-step { border-left: 4px solid #004aad; padding-left: 20px; margin-bottom: 20px; position: relative; }
        .roadmap-step::before { content: '●'; position: absolute; left: -10px; top: 0; color: #004aad; font-size: 18px; background: white; }
        .improvement-text { color: #2e7d32; font-weight: bold; font-size: 0.9em; }
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
    except Exception as e:
        st.error(f"Error loading Readiness file: {e}")
        st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except Exception as e:
        st.error(f"Error loading Benchmarking file: {e}")
        st.stop()

# ─────────────────────────────────────────────
# 3. ROADMAP LOGIC ENGINE
# ─────────────────────────────────────────────
def get_roadmap_data(current_class, current_month, intake_year, course_name):
    months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    curr_m_idx = months_list.index(current_month)
    
    # Deadlines are usually Oct/Nov of the year BEFORE intake
    deadline_year = intake_year - 1
    current_year = datetime.datetime.now().year
    total_months = ((deadline_year - current_year) * 12) + (9 - curr_m_idx)
    
    # Rules
    num_internships = 2 if (deadline_year - current_year) >= 2 else 1
    moocs = 1 if current_class in [10, 12] else 2
    
    # Contest mapping based on uploaded files
    file_map = {
        "CS": "STEM-Coding.csv", "AI": "STEM-Coding.csv", "TECH": "STEM-Coding.csv",
        "BUSINESS": "Business and Entrepreneur.csv", "ENTREPRENEUR": "Business and Entrepreneur.csv",
        "FINANCE": "Finance and Economics.csv", "ECON": "Finance and Economics.csv"
    }
    
    selected_file = "Olympiads.csv" # Default
    for key, f_name in file_map.items():
        if key in course_name.upper():
            selected_file = f_name
            break
            
    full_path = f"Undergrad - Contests_Olympiads for students.xlsx - {selected_file}"
    try:
        df_c = pd.read_csv(full_path)
        contests = df_c.head(3)['Contest Name'].tolist()
    except:
        contests = ["Major International Olympiad", "Summer Research Program", "Global Essay Contest"]

    return {
        "months": max(total_months, 0),
        "internships": num_internships,
        "moocs": moocs,
        "contests": contests,
        "deadline": f"October {deadline_year}",
        "class": current_class
    }

# ─────────────────────────────────────────────
# 4. PDF GENERATION ENGINE
# ─────────────────────────────────────────────
def generate_pdf(name, baseline, strategic, bench_df, countries, counsellor, course_name, roadmap=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Logo
    if os.path.exists("Uppseekers Logo.png"):
        try: elements.append(Image("Uppseekers Logo.png", width=120, height=36))
        except: pass
    
    elements.append(Paragraph(f"Admit AI Strategic Report: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Course:</b> {course_name} | <b>Counsellor:</b> {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # 1. Score Summary
    elements.append(Paragraph("Profile Performance Summary", styles['Heading3']))
    summary_data = [
        ["Phase", "Total Score", "Status"],
        ["Baseline (Initial)", str(baseline), "Current"],
        ["Strategic (After Planning)", str(strategic), f"+{strategic - baseline} Points"]
    ]
    st_table = Table(summary_data, colWidths=[150, 100, 150])
    st_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#004aad")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey), ('PADDING', (0,0), (-1,-1), 6)]))
    elements.append(st_table)
    elements.append(Spacer(1, 20))

    # 2. Roadmap Section
    if roadmap:
        elements.append(Paragraph("Admissions Strategic Roadmap", styles['Heading2']))
        elements.append(Paragraph(f"Timeline: {roadmap['months']} months remaining until {roadmap['deadline']}", styles['Normal']))
        elements.append(Spacer(1, 10))
        
        rd_data = [
            ["Activity", "Requirement", "Focus Area"],
            ["Internships", f"{roadmap['internships']} Projects", "Industry Exposure"],
            ["Research Paper", "1 Paper", "Academic Depth"],
            ["MOOCs", f"{roadmap['moocs']} per year", "Skill Acquisition"],
            ["Top Contests", ", ".join(roadmap['contests'][:2]), "Global Recognition"],
            ["Admissions Stretch", "Final 6 Months", "SOP, LOR & Application"]
        ]
        rd_table = Table(rd_data, colWidths=[100, 120, 200])
        rd_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.grey), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.black)]))
        elements.append(rd_table)
        elements.append(Spacer(1, 20))

    # 3. University Lists (Strategic)
    for country in countries:
        elements.append(Paragraph(f"University Targets: {country}", styles['Heading2']))
        c_df = bench_df[bench_df["Country"] == country].copy() if "Country" in bench_df.columns else bench_df.copy()
        c_df["diff"] = c_df["Total Benchmark Score"] - strategic
        
        def add_u_table(df, title, color, limit):
            if not df.empty:
                elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
                u_data = [["University", "Target Score", "Gap Points"]]
                for _, row in df.head(limit).iterrows():
                    u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), str(round(row["Total Benchmark Score"] - strategic, 1))])
                ut = Table(u_data, colWidths=[300, 70, 80])
                ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
                elements.append(ut); elements.append(Spacer(1, 12))

        add_u_table(c_df[c_df["diff"] <= 0].sort_values("Total Benchmark Score", ascending=False), "Safe to Target", colors.darkgreen, 5)
        add_u_table(c_df[(c_df["diff"] > 0) & (c_df["diff"] <= 15)].sort_values("Total Benchmark Score"), "Strengthening Required", colors.orange, 10)
        add_u_table(c_df[(c_df["diff"] > 15) & (c_df["diff"] <= 30)].sort_values("Total Benchmark Score"), "Significant Gap", colors.red, 10)

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
        countries = st.multiselect("Preferred Countries", ["USA", "UK", "Canada", "Singapore", "Australia", "Europe"], max_selections=3)
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
                pts = v_map[sel]
                current_score += pts
                q_cols[1].markdown(f'<div class="score-box">Points<br><b>{pts}</b></div>', unsafe_allow_html=True)

    with col_dash:
        # --- SCORE TRACKER ---
        st.subheader("📊 Profile Tracker")
        if st.session_state.baseline_score is None:
            if st.button("🔴 Step 1: Lock Current Profile"):
                st.session_state.baseline_score = current_score
                st.rerun()
        else:
            if st.button("🔄 Reset Baseline"):
                st.session_state.baseline_score = None
                st.rerun()

        m1, m2 = st.columns(2)
        if st.session_state.baseline_score is not None:
            m1.metric("Baseline", st.session_state.baseline_score)
            m2.metric("Strategic", current_score, delta=current_score - st.session_state.baseline_score)
        else:
            m1.metric("Current Score", current_score)

        st.divider()

        # --- ROADMAP ARCHITECT ---
        st.subheader("🚀 Roadmap Architect")
        with st.expander("Configure Strategic Timeline", expanded=False):
            c_cl = st.number_input("Current Grade", 8, 12, 10)
            c_mo = st.selectbox("Current Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
            i_yr = st.number_input("Intake Year", 2025, 2030, 2027)
            if st.button("Generate Roadmap"):
                st.session_state.roadmap = get_roadmap_data(c_cl, c_mo, i_yr, st.session_state.course)

        if 'roadmap' in st.session_state:
            rd = st.session_state.roadmap
            st.info(f"📅 **{rd['months']} Months** until {rd['deadline']} deadline.")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card">Internships<br><b>{rd["internships"]}</b></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card">MOOCs/yr<br><b>{rd["moocs"]}</b></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card">Research<br><b>1</b></div>', unsafe_allow_html=True)
            
            st.markdown("### 🏆 Top Contests")
            for ct in rd['contests']: st.markdown(f"⭐ {ct}")
        
        st.divider()

        # --- COUNTRY COMPARISON ---
        for country in st.session_state.countries:
            with st.expander(f"📍 {country} Targets", expanded=True):
                c_df = bench_master[bench_master["Country"] == country].copy() if "Country" in bench_master.columns else bench_master.copy()
                
                # Current/Strategic logic
                c_df["diff_s"] = c_df["Total Benchmark Score"] - current_score
                st_now = len(c_df[c_df['diff_s'] <= 0])
                
                # Baseline comparison logic
                if st.session_state.baseline_score is not None:
                    c_df["diff_b"] = c_df["Total Benchmark Score"] - st.session_state.baseline_score
                    st_base = len(c_df[c_df['diff_b'] <= 0])
                    st.write(f"✅ **Safe to Target:** {st_now} " + (f"*(Was {st_base})*" if st_now > st_base else ""))
                    if st_now > st_base:
                        st.markdown(f'<span class="improvement-text">⬆ Strategic planning added {st_now - st_base} universities</span>', unsafe_allow_html=True)
                else:
                    st.write(f"✅ **Safe to Target:** {st_now}")
                
                st.write(f"💡 **Strengthening Req:** {len(c_df[(c_df['diff_s'] > 0) & (c_df['diff_s'] <= 15)])}")
                st.write(f"⚠️ **Significant Gap:** {len(c_df[(c_df['diff_s'] > 15) & (c_df['diff_s'] <= 30)])}")

        # --- EXPORT ---
        if st.session_state.baseline_score is not None:
            st.divider()
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Access Pin", type="password")
            if st.button("Step 2: Generate Strategic Report"):
                if pin == "304":
                    rd_data = st.session_state.get('roadmap', None)
                    pdf = generate_pdf(st.session_state.name, st.session_state.baseline_score, current_score, bench_master, st.session_state.countries, c_name, st.session_state.course, rd_data)
                    st.download_button("📥 Download Final Report", data=pdf, file_name=f"{st.session_state.name}_Strategy.pdf", mime="application/pdf")
                else:
                    st.error("Incorrect Pin")
