import os
import datetime
import re
import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from google import genai
from dotenv import load_dotenv

# Enviornment & Security Setup
load_dotenv()
try:
    client = genai.Client()
except Exception as e:
    st.error("Failed to authenticate Gemini Client. Check your .env configuration.")

st.set_page_config(page_title="KawanAI Portal", page_icon="🎓", layout="wide")

# styling palette
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stSidebar { background-color: #0f172a; }
    h1 { color: #1e3a8a; font-family: 'Helvetica Neue', sans-serif; }
    .semester-box { 
        background-color: #ffffff; 
        padding: 15px 20px; 
        border-radius: 12px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        border-left: 5px solid #10b981;
    }
    .workload-badge {
        background-color: #ecfdf5;
        color: #047857;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# Dynamic CSV Dataset Ingestion Layer
@st.cache_data
def load_csv_data(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        st.error(f"Critical configuration file database ({filename}) missing.")
        return pd.DataFrame()

df_curriculum = load_csv_data("curriculum.csv")
df_hostels = load_csv_data("hostels.csv")
df_financial = load_csv_data("financial_aid.csv")
df_admin = load_csv_data("admin_rules.csv")

ACADEMIC_YEARS = ["2025/2026", "2026/2027", "2027/2028", "2028/2029", "2029/2030", "2030/2031", "2031/2032"]
SEMESTER_TYPES = ["Semester 1", "Semester 2", "Special Semester"]

# State Management & Parsing Cores
if "planner_semesters" not in st.session_state:
    st.session_state.planner_semesters = [
        {
            "academic_year": "2025/2026",
            "semester_type": "Semester 1",
            "start_date": datetime.date(2025, 10, 13),
            "end_date": datetime.date(2026, 2, 22),
            "selected_courses": []
        }
    ]

if "kawan_chat_history" not in st.session_state:
    st.session_state.kawan_chat_history = []

def ask_kawan_ai(prompt_context):
    try:
        response = client.models.generate_content(model='gemini-3.1-flash-lite', contents=prompt_context)
        return response.text
    except Exception:
        return "System gateway timeout."

def calculate_next_semester(last_sem):
    current_year_str = last_sem["academic_year"]
    current_type = last_sem["semester_type"]
    
    try:
        start_year = int(current_year_str.split("/")[0])
        end_year = int(current_year_str.split("/")[1])
    except Exception:
        start_year, end_year = 2025, 2026
    
    if current_type == "Semester 1":
        next_year = current_year_str
        next_type = "Semester 2"
    elif current_type == "Semester 2":
        next_year = current_year_str
        next_type = "Summer / Special Semester"
    else:
        next_year = f"{start_year + 1}/{end_year + 1}"
        next_type = "Semester 1"
        
    if next_year not in ACADEMIC_YEARS:
        next_year = ACADEMIC_YEARS[-1]
        
    return {
        "academic_year": next_year,
        "semester_type": next_type,
        "start_date": last_sem["end_date"] + datetime.timedelta(days=14),
        "end_date": last_sem["end_date"] + datetime.timedelta(days=120),
        "selected_courses": []
    }

def extract_credits(course_string):
    match = re.search(r'\((\d+)\s*Credits?\)', course_string)
    return int(match.group(1)) if match else 0

# PDF Compilation Blueprint Export Module
def export_blueprint_to_pdf(semester_data, university, major):
    doc = fitz.open()
    page = doc.new_page()
    
    page.insert_text((45, 50), "KawanAI Academic Plan Blueprint", fontsize=22, fontname="hebo", color=(0.06, 0.16, 0.38))
    page.insert_text((45, 75), f"Institution: {university}", fontsize=11, fontname="helv")
    page.insert_text((45, 90), f"Program Specialization: {major}", fontsize=11, fontname="hebo")
    page.insert_text((45, 105), f"Issued: {datetime.date.today().strftime('%d %B %Y')}", fontsize=9, fontname="heit", color=(0.4, 0.4, 0.4))
    
    shape = page.new_shape()
    shape.draw_line(fitz.Point(45, 120), fitz.Point(550, 120))
    shape.finish(color=(0.7, 0.7, 0.7), width=1)
    shape.commit()
    
    y_cursor = 145
    for idx, sem in enumerate(semester_data):
        if y_cursor > 730:
            page = doc.new_page()
            y_cursor = 50
            
        total_credits = sum(extract_credits(c) for c in sem["selected_courses"])
        page.insert_text((45, y_cursor), f"Term Block #{idx+1}: {sem['academic_year']} — {sem['semester_type']}", fontsize=12, fontname="hebo", color=(0.02, 0.47, 0.34))
        page.insert_text((45, y_cursor + 14), f"Duration Sequence: {sem['start_date']} to {sem['end_date']} | Total Workload: {total_credits} Credits", fontsize=9.5, fontname="heit", color=(0.2, 0.2, 0.2))
        
        y_cursor += 38
        if not sem["selected_courses"]:
            page.insert_text((65, y_cursor), "[No units selected inside this programmatic block]", fontsize=10, fontname="helv", color=(0.6, 0.6, 0.6))
            y_cursor += 18
        else:
            for course in sem["selected_courses"]:
                if y_cursor > 750:
                    page = doc.new_page()
                    y_cursor = 50
                page.insert_text((65, y_cursor), f"• {course}", fontsize=10, fontname="helv")
                y_cursor += 18
        y_cursor += 15
        
    return doc.write()

# Sidebar Navigation Controller
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>🎓 KawanAI</h2>", unsafe_allow_html=True)
    st.write("---")
    navigation_menu = st.radio("Go To Module:", ["📅 Semester Course Planner", "💰 Financial Aid Matrix", "🏠 Hostel Room Finder", "🏛️ Central Admin Assistant"])
    st.write("---")
    st.caption("v0.4.1 — Demo")

# Course Planner
if navigation_menu == "📅 Semester Course Planner":
    st.title("🗓️ Smart Sequential Course Planner")
    st.write("Construct your structural timeline. Academic choices and available semesters are constrained dynamically based on your preceding choices.")
    st.write("---")
    
    col_u, col_f, col_m = st.columns(3)
    with col_u:
        uni_options = list(df_curriculum["university"].dropna().unique()) if not df_curriculum.empty else ["No Data Available"]
        selected_uni = st.selectbox("Choose University", uni_options)
    with col_f:
        fac_df = df_curriculum[df_curriculum["university"] == selected_uni]
        fac_options = list(fac_df["faculty"].dropna().unique()) if not fac_df.empty else ["No Data Available"]
        selected_fac = st.selectbox("Choose Faculty", fac_options)
    with col_m:
        major_df = fac_df[fac_df["faculty"] == selected_fac]
        major_options = list(major_df["major"].dropna().unique()) if not major_df.empty else ["No Data Available"]
        selected_major = st.selectbox("Choose Degree Program / Major", major_options)
        
    filtered_df = major_df[major_df["major"] == selected_major]
    
    AVAILABLE_COURSES_POOL = []
    if not filtered_df.empty:
        for _, row in filtered_df.iterrows():
            prereq_suffix = f" [Prereq: {row['prerequisite']}]" if str(row['prerequisite']).lower() != "none" else ""
            display_str = f"{row['course_code']} - {row['course_name']} ({row['credits']} Credits){prereq_suffix}"
            AVAILABLE_COURSES_POOL.append(display_str)
            
    st.write("### 🕒 Your Academic Timeline Construction")
    
    for idx, sem in enumerate(st.session_state.planner_semesters):
        
        # Cache Interception
        if f"ay_{idx}" in st.session_state:
            sem["academic_year"] = st.session_state[f"ay_{idx}"]
        if f"st_{idx}" in st.session_state:
            sem["semester_type"] = st.session_state[f"st_{idx}"]
        if f"courses_{idx}" in st.session_state:
            sem["selected_courses"] = st.session_state[f"courses_{idx}"]
        if f"sd_{idx}" in st.session_state:
            sem["start_date"] = st.session_state[f"sd_{idx}"]
        if f"ed_{idx}" in st.session_state:
            sem["end_date"] = st.session_state[f"ed_{idx}"]

        total_credits = sum(extract_credits(c) for c in sem["selected_courses"])
        
        if idx == 0:
            allowed_academic_years = ACADEMIC_YEARS
            allowed_semester_types = SEMESTER_TYPES
        else:
            prev_sem = st.session_state.planner_semesters[idx - 1]
            prev_ay = prev_sem["academic_year"]
            prev_st = prev_sem["semester_type"]
            prev_ay_idx = ACADEMIC_YEARS.index(prev_ay)
            
            if prev_st == "Special Semester":
                allowed_academic_years = ACADEMIC_YEARS[prev_ay_idx + 1:]
            else:
                allowed_academic_years = ACADEMIC_YEARS[prev_ay_idx:]
                
            if not allowed_academic_years:
                allowed_academic_years = [ACADEMIC_YEARS[-1]]
                
        st.markdown(f"""
        <div class='semester-box'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-size: 16px; font-weight: bold; color: #1e293b;'>Term Block #{idx+1}</span>
                <span class='workload-badge'>⚡ Load Total: {total_credits} Credit Hours</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            try:
                ay_default_idx = allowed_academic_years.index(sem["academic_year"])
            except ValueError:
                sem["academic_year"] = allowed_academic_years[0]
                st.session_state[f"ay_{idx}"] = allowed_academic_years[0]
                ay_default_idx = 0
                
            sem["academic_year"] = st.selectbox(f"Academic Year", allowed_academic_years, index=ay_default_idx, key=f"ay_{idx}")
            
        with c2:
            if idx > 0 and sem["academic_year"] == prev_ay:
                prev_st_idx = SEMESTER_TYPES.index(prev_st)
                allowed_semester_types = SEMESTER_TYPES[prev_st_idx + 1:]
            else:
                allowed_semester_types = SEMESTER_TYPES
                
            if not allowed_semester_types:
                allowed_semester_types = ["Semester 1"]
                
            try:
                st_default_idx = allowed_semester_types.index(sem["semester_type"])
            except ValueError:
                sem["semester_type"] = allowed_semester_types[0]
                st.session_state[f"st_{idx}"] = allowed_semester_types[0]
                st_default_idx = 0
                
            sem["semester_type"] = st.selectbox(f"Term Type", allowed_semester_types, index=st_default_idx, key=f"st_{idx}")
            
        with c3:
            sem["selected_courses"] = st.multiselect("Enroll In Available Courses Only:", AVAILABLE_COURSES_POOL, default=sem["selected_courses"], key=f"courses_{idx}")
            
        c_date1, c_date2 = st.columns(2)
        with c_date1:
            sem["start_date"] = st.date_input("Semester Start Date", value=sem["start_date"], key=f"sd_{idx}")
        with c_date2:
            sem["end_date"] = st.date_input("Semester End Date", value=sem["end_date"], key=f"ed_{idx}")
        st.write("---")
        
    if st.button("➕ Add Next Semester Block"):
        last_semester_node = st.session_state.planner_semesters[-1]
        new_semester_node = calculate_next_semester(last_semester_node)
        st.session_state.planner_semesters.append(new_semester_node)
        st.rerun()

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🚀 Analyze and Optimize Entire Timeline Plan", type="primary", width='stretch'):
            with st.spinner("Passing weights and dynamic dates to Cognitive Processing engine..."):
                summary_blocks = []
                for s in st.session_state.planner_semesters:
                    courses_listed = ", ".join(s["selected_courses"]) if s["selected_courses"] else "No courses selected yet"
                    sem_load = sum(extract_credits(c) for c in s["selected_courses"])
                    summary_blocks.append(f"- {s['academic_year']} {s['semester_type']} ({s['start_date']} to {s['end_date']}) Load: {sem_load} Credits. Mapped Units: [{courses_listed}]")
                compiled_timeline_string = "\\n".join(summary_blocks)
                
                evaluation_prompt = f"""
                You are the Chief Academic Systems Counselor at {selected_uni}.
                Review the following custom schedule timeline structured for the {selected_major} program:
                {compiled_timeline_string}
                Provide an intelligent markdown analysis reviewing workload balancing, chronology, and specific course advice.
                """
                st.session_state.analysis_output = ask_kawan_ai(evaluation_prompt)
                
        if "analysis_output" in st.session_state:
            st.markdown(st.session_state.analysis_output)
            
    with c_btn2:
        try:
            pdf_binary_data = export_blueprint_to_pdf(st.session_state.planner_semesters, selected_uni, selected_major)
            st.download_button(
                label="📥 Export Blueprint to Official PDF",
                data=pdf_binary_data,
                file_name=f"KawanAI_Academic_Plan_{selected_major.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF compilation handler halted: {e}")

# Financial Aid Matrix & Micro-Financing Pipeline
elif navigation_menu == "💰 Financial Aid Matrix":
    st.title("💰 Smart Financial Aid & Neo-Banking Engine")
    st.write("Access institutional grants, simulate Shariah-compliant student financing lines, and model your repayment trajectories.")
    st.write("---")
    
    fin_tab1, fin_tab2 = st.tabs(["🔍 Institutional Registry Search", "🧮 KawanFlex Micro-Financing Simulator"])
    
    with fin_tab1:
        st.subheader("Campus Financial Registry")
        financial_query = st.text_input(
            "What financial assistance or scholarship programs are you tracking today?", 
            placeholder="e.g., 'What are the rules for Yayasan Bank Islam?' or 'Is there an upfront fee for PTPTN?'"
        )
        if financial_query:
            with st.spinner("Searching institutional registry datasets..."):
                finance_prompt = f"""
                You are an expert Financial Aid Advisor. Resolve the query using strictly the CSV data registry below:
                {df_financial.to_string(index=False)}
                
                USER INQUIRY: "{financial_query}"
                """
                result = ask_kawan_ai(finance_prompt)
                st.info(result)
                
    with fin_tab2:
        st.subheader("⚡ KawanFlex: Shariah-Compliant Micro-Financing Line")
        st.write("Need to fund a hostel room deposit, tuition fees, or textbook purchases? Simulate your Bank Islam flexible installment program instantly.")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            funding_needed = st.number_input("Enter Required Funding Amount (RM)", min_value=100, max_value=5000, value=1200, step=50)
            tenure_months = st.slider("Select Repayment Tenure (Months)", min_value=2, max_value=12, value=4)
            financing_type = st.selectbox("Select Shariah Structure", ["Qard Hasan (Benevolent Loan - 0% Admin Fee)", "Murabahah (Cost-Plus Margin)"])
        
        admin_fee_rate = 0.01 if financing_type == "Murabahah (Cost-Plus Margin)" else 0.00
        total_admin_fee = funding_needed * admin_fee_rate
        total_repayment = funding_needed + total_admin_fee
        monthly_installment = total_repayment / tenure_months
        
        with col_f2:
            st.markdown(f"""
            <div style='background-color: #0f172a; padding: 25px; border-radius: 12px; color: white;'>
                <h4 style='color: #10b981; margin-top:0;'>🏦 Be U Financing Summary</h4>
                <p>Principal Amount: <b>RM {funding_needed:.2f}</b></p>
                <p>Shariah Framework: <b>{financing_type}</b></p>
                <p>Calculated Profit/Admin Margin: <b>RM {total_admin_fee:.2f}</b></p>
                <hr style='border-color: #334155;'>
                <h3 style='color: #10b981; margin: 5px 0;'>RM {monthly_installment:.2f} / month</h3>
                <p style='font-size: 13px; color: #94a3b8;'>Estimated installment over {tenure_months} months</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("🚀 Submit KawanFlex Application via Be U Gateway", use_container_width=True):
                with st.spinner("Encrypting payload and transmitting to Bank Islam credit scoring gateway..."):
                    ai_analysis_prompt = f"""
                    You are a Bank Islam Credit Officer. Review this student micro-financing application:
                    Requested Amount: RM {funding_needed}
                    Tenure: {tenure_months} months
                    Structure: {financing_type}
                    
                    Provide a concise, friendly 3-sentence markdown evaluation confirming pre-approval, validating their budgeting choice, and advising on smart cash management for a uni student.
                    """
                    decision_response = ask_kawan_ai(ai_analysis_prompt)
                    st.success("✅ Application Pre-Approved Natively!")
                    st.markdown(decision_response)

# Hostel Room Finder
elif navigation_menu == "🏠 Hostel Room Finder":
    st.title("🏠 Real-Time College Accommodation Finder")
    st.write("Instantly evaluate vacant hostel rooms based on pricing, layout constraints, and climate utilities.")
    st.write("---")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        cooling = st.radio("Room Ventilation Preference", ["Air Conditioning (AC)", "Standard Fan Only"])
    with col_h2:
        sharing = st.radio("Occupancy Mode", ["Single Room Private", "Twin Sharing Base"])
        
    if st.button("Query Vacant Campus Housing Ledger"):
        with st.spinner("Polling Kolej housing metrics..."):
            hostel_prompt = f"""
            You are the Campus Accommodations Warden assistant. Filter the following ledger to find configurations matching:
            VENTILATION PREFERENCE: {cooling}
            OCCUPANCY MODE: {sharing}
            
            LEDGER DATASET FROM SYSTEM CSV:
            {df_hostels.to_string(index=False)}
            """
            result = ask_kawan_ai(hostel_prompt)
            st.markdown(result)

# Central Admin Assistant
elif navigation_menu == "🏛️ Central Admin Assistant":
    st.title("🏛️ Central University Administration Hub")
    st.write("Bypass long administrative queues. Ask KawanAI regarding drop dates, deadlines, or credit hours rules.")
    st.write("---")
    
    for author, text in st.session_state.kawan_chat_history:
        st.chat_message("user" if author == "Student" else "assistant").write(text)
        
    admin_input = st.chat_input("Ask about policies...")
    if admin_input:
        st.session_state.kawan_chat_history.append(("Student", admin_input))
        st.chat_message("user").write(admin_input)
        
        with st.spinner("Evaluating procedural policies..."):
            admin_prompt = f"""
            You are the Academic Affairs Representative bot. Answer using strictly the guidelines inside the policy database set down here:
            {df_admin.to_string(index=False)}
            
            STUDENT QUERY: "{admin_input}"
            """
            response_text = ask_kawan_ai(admin_prompt)
            st.session_state.kawan_chat_history.append(("KawanAI Admin", response_text))
            st.chat_message("assistant").write(response_text)
            st.rerun()