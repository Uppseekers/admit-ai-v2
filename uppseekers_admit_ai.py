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
        .improvement-text { color: #2e7d32; font-weight: bold; font-size: 0.85em; }
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
    except: st.error("Error loading University Readiness file."); st.stop()

def load_benchmarking():
    try:
        bxls = pd.ExcelFile("Benchmarking_USA.xlsx")
        idx = bxls.parse(bxls.sheet_names[0])
        return bxls, {str(k).strip(): str(v).strip() for k, v in zip(idx.iloc[:,0], idx.iloc[:,1])}
    except: st.error("Error loading Benchmarking file."); st.stop()

# ─────────────────────────────────────────────
# 3. PDF GENERATION ENGINE
# ─────────────────────────────────────────────
def generate_pdf(name, baseline, strategic, bench_df, countries, counsellor, course_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    logo_path = "Uppseekers Logo.png"
    if os.path.exists(logo_path):
        try: elements.append(Image(logo_path, width=120, height=36))
        except: pass
    
    elements.append(Paragraph(f"Strategic Admit AI Report: {name}", styles['Title']))
    elements.append(Paragraph(f"<b>Course:</b> {course_name} | <b>Counsellor:</b> {counsellor}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    summary_data = [
        ["Profile Status", "Total Score", "Improvement"],
        ["Baseline (Current)", str(baseline), "-"],
        ["Strategic (Planned)", str(strategic), f"+{strategic - baseline}"]
    ]
    st_table = Table(summary_data, colWidths=[150, 100, 100])
    st_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#004aad")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
    elements.append(st_table)
    elements.append(Spacer(1, 20))

    def add_table(df, title, color, limit):
        if not df.empty:
            elements.append(Paragraph(title, ParagraphStyle('B', parent=styles['Heading4'], textColor=color)))
            u_data = [["University", "Target Score", "Gap Points"]]
            for _, row in df.head(limit).iterrows():
                gap = round(row["Total Benchmark Score"] - strategic, 1)
                u_data.append([row["University"], str(round(row["Total Benchmark Score"], 1)), str(gap)])
            ut = Table(u_data, colWidths=[300, 70, 80])
            ut.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), color), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
            elements.append(ut); elements.append(Spacer(1, 12))

    for country in countries:
        elements.append(Paragraph(f"Country Targets: {country}", styles['Heading2']))
        c_df = bench_df[bench_df["Country"] == country].copy() if "Country" in bench_df.columns else bench_df.copy()
        c_df["diff"] = c_df["Total Benchmark Score"] - strategic
        
        add_table(c_df[c_df["diff"] <= 0].sort_values("Total Benchmark Score", ascending=False), "Safe to Target", colors.darkgreen, 5)
        add_table(c_df[(c_df["diff"] > 0) & (c_df["diff"] <= 15)].sort_values("Total Benchmark Score"), "Strengthening Required", colors.orange, 10)
        add_table(c_df[(c_df["diff"] > 15) & (c_df["diff"] <= 30)].sort_values("Total Benchmark Score"), "Significant Gap", colors.red, 10)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 4. APP INTERFACE
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
        st.subheader("📊 Live Strategy Tracker")
        if st.session_state.baseline_score is None:
            if st.button("🔴 Step 1: Lock Current Profile Score"):
                st.session_state.baseline_score = current_score
                st.rerun()
        else:
            if st.button("🔄 Reset Baseline"):
                st.session_state.baseline_score = None
                st.rerun()

        s1, s2 = st.columns(2)
        if st.session_state.baseline_score is not None:
            s1.metric("Baseline Score", st.session_state.baseline_score)
            s2.metric("Strategic Score", current_score, delta=current_score - st.session_state.baseline_score)
        else:
            s1.metric("Current Score", current_score)

        st.divider()
        
        for country in st.session_state.countries:
            with st.expander(f"📍 {country} Targets", expanded=True):
                c_df = bench_master[bench_master["Country"] == country].copy() if "Country" in bench_master.columns else bench_master.copy()
                
                # Logic for current (strategic) score
                c_df["diff_strat"] = c_df["Total Benchmark Score"] - current_score
                st_now = len(c_df[c_df['diff_strat'] <= 0])
                sr_now = len(c_df[(c_df['diff_strat'] > 0) & (c_df['diff_strat'] <= 15)])
                sg_now = len(c_df[(c_df['diff_strat'] > 15) & (c_df['diff_strat'] <= 30)])

                # Logic for baseline (if exists)
                if st.session_state.baseline_score is not None:
                    c_df["diff_base"] = c_df["Total Benchmark Score"] - st.session_state.baseline_score
                    st_base = len(c_df[c_df['diff_base'] <= 0])
                    
                    # UI for Improvement
                    st.write(f"✅ **Safe to Target:** {st_now} " + (f"*(Was {st_base})*" if st_now > st_base else ""))
                    if st_now > st_base:
                        st.markdown(f'<span class="improvement-text">⬆ Increased options by {st_now - st_base} universities</span>', unsafe_allow_html=True)
                else:
                    st.write(f"✅ **Safe to Target:** {st_now}")
                
                st.write(f"💡 **Strengthening Req:** {sr_now}")
                st.write(f"⚠️ **Significant Gap:** {sg_now}")
                
                # Visual success bar
                progress = min(max(current_score / 100, 0.0), 1.0)
                st.progress(progress)

        if st.session_state.baseline_score is not None:
            st.divider()
            c_name = st.text_input("Counsellor Name")
            pin = st.text_input("Access Pin", type="password")
            if st.button("Step 2: Authenticate & Prepare Report"):
                if pin == "304":
                    pdf_output = generate_pdf(st.session_state.name, st.session_state.baseline_score, current_score, bench_master, st.session_state.countries, c_name, st.session_state.course)
                    st.download_button(label="📥 Download Strategic Report", data=pdf_output, file_name=f"{st.session_state.name}_Strategy.pdf", mime="application/pdf")
                else:
                    st.error("Incorrect Pin")


import datetime

# ─────────────────────────────────────────────
# 1. NEW ROADMAP LOGIC ENGINE
# ─────────────────────────────────────────────
def generate_roadmap_data(current_class, current_month, interest):
    # Mapping months to numbers for calculation
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    curr_m_idx = months.index(current_month)
    
    # Calculate months remaining until Grade 12 Oct (Application Season)
    target_year = 12
    years_left = target_year - int(current_class)
    total_months_left = (years_left * 12) + (9 - curr_m_idx) # Until Oct of Grade 12
    
    roadmap = []
    
    # 1. Internships Logic
    num_internships = 2 if years_left >= 2 else 1
    
    # 2. Research Paper & Apps
    roadmap.append({"Activity": "Research Paper", "Timeline": "Next 6-8 Months", "Detail": "1 Deep-dive Research Project + Publication"})
    roadmap.append({"Activity": "Application Phase", "Timeline": "Final 6 Months", "Detail": "SOP Writing, LOR Collection, Essay Editing"})

    # 3. Dynamic Contest Selection (from your sheets)
    try:
        if "CS" in interest or "AI" in interest:
            df_c = pd.read_csv("Undergrad - Contests_Olympiads for students.xlsx - STEM-Coding.csv")
        elif "Business" in interest:
            df_c = pd.read_csv("Undergrad - Contests_Olympiads for students.xlsx - Business and Entrepreneur.csv")
        else:
            df_c = pd.read_csv("Undergrad - Contests_Olympiads for students.xlsx - Finance and Economics.csv")
        
        suggested_contests = df_c.head(3)['Contest Name'].tolist()
    except:
        suggested_contests = ["Relevant International Olympiad", "Major Subject Contest"]

    return {
        "months_left": total_months_left,
        "internships": num_internships,
        "contests": suggested_contests,
        "years_left": years_left
    }

# ─────────────────────────────────────────────
# 2. UPDATED INTERFACE (Add to 'analysis' page)
# ─────────────────────────────────────────────

# Inside the 'analysis' page elif block, add a new tab or expander:
with col_dash:
    st.divider()
    st.subheader("🚀 Roadmap Architect")
    
    with st.expander("Generate Admissions Roadmap", expanded=False):
        c_class = st.selectbox("Current Class", [8, 9, 10, 11], index=2)
        c_month = st.selectbox("Current Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        
        if st.button("Build My Roadmap"):
            data = generate_roadmap_data(c_class, c_month, st.session_state.course)
            
            st.markdown("---")
            st.info(f"📅 **Timeline:** {data['months_left']} months until applications.")
            
            # Use columns for a superb design layout
            r1, r2 = st.columns(2)
            r1.metric("Internships", data['internships'])
            r2.metric("Research Papers", "1")
            
            st.markdown("### 🏆 Suggested Contests")
            for c in data['contests']:
                st.markdown(f"⭐ {c}")
                
            st.markdown("### 📚 Academic Growth")
            mooc_count = 1 if c_class in [10, 12] else 2
            st.write(f"• **MOOCs:** Complete {mooc_count} certifications this year.")
            
            st.markdown("### ✍️ The Final Stretch")
            st.warning("Last 6 Months: Strictly for SOPs, LORs, and Application Portals.")

# ─────────────────────────────────────────────
# 3. PDF UPDATES
# ─────────────────────────────────────────────
# Ensure your generate_pdf function now accepts these roadmap parameters 
# so they appear in the final printed document.
