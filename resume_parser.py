import streamlit as st
import os
import json
from groq import Groq
from PyPDF2 import PdfReader
import pdfplumber
from dotenv import load_dotenv
from experience import calculate_total_experience_unique,format_experience

# It's good practice to load .env file if it exists, for local development
load_dotenv()

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="AI Resume Parser",
    page_icon="📄",
    layout="wide"
)



# --- Core Resume Parsing Functions ---

def get_resume_details_from_groq(api_key, resume_text):
    """Sends the resume text to the Groq API and returns the parsed JSON."""
    # --- MODIFIED PROMPT ---
    prompt = f"""
    You are an expert resume parsing AI that strictly follows instructions. Your only output must be a single, valid JSON object based on the provided schema.

    From the provided resume text, extract the information and populate the following JSON structure. Do not add any text or markdown before or after the JSON. If a field is not found, use an appropriate empty value (e.g., "" or []).The Below Languages refers to the spoken languages.Suggested_Resume_Category refers to suggest a role based on the skills and experience.Recommended_Job_Roles refers you to recommend few job roles based on the candidate's skills and experience.

    Resume Text:
    ---
    {resume_text}
    ---

    Desired JSON Schema to Populate:
    {{
      "Full_Name": "",
      "Contact_Number": "",
      "Email_Address": "",
      "Location": "",
      "LinkedIn_Profile":"",
      "GitHub_Profile":"",
      "Skills": {{
        "Technical": [],
        "Non-Technical": []
      }},
      "Education": [
        {{
          "Degree": "",
          "Institution": "",
          "Years": ""
        }}
      ],
      "Work_Experience": [
        {{
          "Company_Name": "",
          "Job_Title": "",
          "start_date": "MM/YYYY",
          "end_date": "MM/YYYY or Present",
          "Responsibilities": []
        }}
      ],
      "Projects": [
        {{
          "Project_Name": "",
          "Technologies_Used": [],
          "Description": ""
        }}
      ],
      "Certifications": [],
      "Languages_Spoken": [],
      "Suggested_Resume_Category": "",
      "Recommended_Job_Roles": []
    }}
    """

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are a resume parsing assistant that outputs only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)

    except Exception as e:
        st.error(f"An error occurred during API call: {e}")
        return None

def parse_resume_from_pdf(api_key, pdf_file):
    """Main orchestrator function for Streamlit."""
    text = ""
    try:
        # +++ NEW CODE using pdfplumber for better text extraction +++
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if page_text:
                    text += page_text + "\n"
        # +++ END OF NEW CODE +++
    except Exception as e:
        return {"error": f"Error reading PDF with pdfplumber: {e}"}

    if not text.strip():
        return {"error": "Could not extract any meaningful text from the PDF. The file might be image-based or have an unusual format."}
    # The rest of the function continues as before
    json_data = get_resume_details_from_groq(api_key, text)

    if not json_data:
        return {"error": "Failed to get details from AI model."}
    # --- NEW: Calculate experience using the new function ---
    calculated_experience_float = calculate_total_experience_unique(json_data.get("Work_Experience", []))
    formatted_experience = format_experience(calculated_experience_float)

    # Structure the data for the form
    registration_data = {
        "personal_info": json_data.get("personal_info", {
            "full_name": json_data.get("Full_Name", ""), "contact_number": json_data.get("Contact_Number", ""),
            "email_address": json_data.get("Email_Address", ""), "location": json_data.get("Location", ""),
            "linkedin_profile":json_data.get("LinkedIn_Profile",""),'github':json_data.get("GitHub_Profile","")
        }),
        "skills": {
            "technical": json_data.get("Skills", {}).get("Technical", []),
            "non_technical": json_data.get("Skills", {}).get("Non-Technical", [])
        },
        "education": json_data.get("Education", []),
        "total_experience": formatted_experience, # Use the calculated value
        "work_experience": json_data.get("Work_Experience", []),
        "projects": json_data.get("Projects", []), # NEW: Add projects
        "certifications": json_data.get("Certifications", []),
        "languages": json_data.get("Languages_Spoken", []),
        "suggested_category": json_data.get("Suggested_Resume_Category", ""),
        "recommended_roles": json_data.get("Recommended_Job_Roles", [])
    }
    return registration_data

# --- Streamlit Application UI ---

st.title("📄 AI-Powered Resume Parser & Editor")
st.markdown("Upload a resume, and the AI will populate the form. You can then review, edit, and save the details.")

if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None
if 'form_key' not in st.session_state:
    st.session_state.form_key = 'initial'

with st.sidebar:
    api_key = st.secrets["GROQ_API_KEY"]
    uploaded_file = st.file_uploader("Upload your Resume (PDF)", type="pdf")
    if st.button("Process Resume"):
        if uploaded_file is None:
            st.error("Please upload a resume PDF.")
        else:
            with st.spinner("Analyzing resume... This may take a moment."):
                parsed_result = parse_resume_from_pdf(api_key, uploaded_file)
                if "error" in parsed_result:
                    st.error(parsed_result["error"])
                    st.session_state.parsed_data = None
                else:
                    st.session_state.parsed_data = parsed_result
                    st.session_state.form_key = f'form_{uploaded_file.file_id}'
                    st.success("Resume processed! You can now edit the details.")

if st.session_state.parsed_data:
    data = st.session_state.parsed_data
    
    st.header("📝 Review and Edit Extracted Information")
    
    with st.form(key=st.session_state.form_key):
        st.subheader("Personal Information")
        p_info = data.get("personal_info", {})
        col1, col2 = st.columns(2)
        full_name = col1.text_input("Full Name", value=p_info.get("full_name", ""))
        contact_number = col1.text_input("Contact Number", value=p_info.get("contact_number", ""))
        email_address = col2.text_input("Email Address", value=p_info.get("email_address", ""))
        location = col2.text_input("Location", value=p_info.get("location", ""))
        linkedin = col1.text_input("LinkedIn", value=p_info.get("linkedin_profile", ""))
        github = col2.text_input("GitHub", value=p_info.get("github", ""))

        st.subheader("Professional Summary")
        col1, col2 = st.columns(2)
        total_exp = col1.text_input("Total Experience (Calculated)", value=data.get("total_experience", ""))
        sugg_cat = col1.text_input("Suggested Category", value=data.get("suggested_category", ""))
        reco_roles = col2.text_area("Recommended Roles", value=', '.join(data.get("recommended_roles", [])), help="Comma-separated roles")

        st.subheader("Skills")
        skills_info = data.get("skills", {})
        col1, col2 = st.columns(2)
        with col1:
            tech_skills = st.text_area("Technical Skills", value=', '.join(skills_info.get("technical", [])), help="Comma-separated skills")
        with col2:
            non_tech_skills = st.text_area("Non-Technical Skills", value=', '.join(skills_info.get("non_technical", [])), help="Comma-separated skills")

        st.subheader("Work Experience")
        work_exp_list = data.get("work_experience", [])
        for i, job in enumerate(work_exp_list):
            with st.expander(f"{job.get('Job_Title', 'N/A')} at {job.get('Company_Name', 'N/A')}", expanded=True):
                c1, c2 = st.columns(2)
                job['Job_Title'] = c1.text_input("Job Title", value=job.get('Job_Title', ''), key=f"job_title_{i}")
                job['Company_Name'] = c2.text_input("Company Name", value=job.get('Company_Name', ''), key=f"company_{i}")
                job['start_date'] = c1.text_input("Start Date (MM/YYYY)", value=job.get('start_date', ''), key=f"start_date_{i}")
                job['end_date'] = c2.text_input("End Date (MM/YYYY or Present)", value=job.get('end_date', ''), key=f"end_date_{i}")
                # --- MODIFIED: Responsibility display ---
                job['Responsibilities'] = st.text_area("Responsibilities", value='\n'.join(job.get('Responsibilities', [])), key=f"resp_{i}", help="One responsibility per line")
        
        # --- NEW: Projects Section ---
        st.subheader("Projects")
        projects_list = data.get("projects", [])
        for i, project in enumerate(projects_list):
            with st.expander(f"Project: {project.get('Project_Name', 'N/A')}", expanded=True):
                project['Project_Name'] = st.text_input("Project Name", value=project.get('Project_Name', ''), key=f"proj_name_{i}")
                project['Technologies_Used'] = st.text_area("Technologies Used", value=', '.join(project.get('Technologies_Used', [])), key=f"proj_tech_{i}", help="Comma-separated technologies.")
                project['Description'] = st.text_area("Description", value=project.get('Description', ''), key=f"proj_desc_{i}")

        st.subheader("Education")
        edu_list = data.get("education", [])
        for i, edu in enumerate(edu_list):
            with st.expander(f"{edu.get('Degree', 'N/A')} from {edu.get('Institution', 'N/A')}", expanded=True):
                c1, c2 = st.columns(2)
                edu['Degree'] = c1.text_input("Degree", value=edu.get('Degree', ''), key=f"degree_{i}")
                edu['Institution'] = c2.text_input("Institution", value=edu.get('Institution', ''), key=f"inst_{i}")
                edu['Years'] = st.text_input("Years", value=edu.get('Years', ''), key=f"years_{i}")

        st.subheader("Certifications & Languages")
        certs = st.text_area("Certifications", value='\n'.join(data.get("certifications", [])), help="One certification per line.")
        langs = st.text_area("Languages", value=', '.join(data.get("languages", [])), help="Comma-separated languages.")

        st.markdown("---")
        submitted = st.form_submit_button("Save Changes")
        
        if submitted:
            final_data = {
                "personal_info": {"full_name": full_name, "contact_number": contact_number, "email_address": email_address, "location": location},
                "total_experience": total_exp, "suggested_category": sugg_cat,
                "recommended_roles": [r.strip() for r in reco_roles.split(',')],
                "skills": {"technical": [s.strip() for s in tech_skills.split(',')], "non_technical": [s.strip() for s in non_tech_skills.split(',')],},
                "work_experience": work_exp_list, "projects": projects_list, "education": edu_list,
                "certifications": [c.strip() for c in certs.split('\n') if c.strip()], "languages": [l.strip() for l in langs.split(',')],
            }
            st.success("Data saved successfully!")
            st.json(final_data)
else:
    st.info("Upload a resume and click 'Process Resume' to begin.")
