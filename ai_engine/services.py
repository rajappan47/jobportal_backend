import fitz  # PyMuPDF
from docx import Document
from sklearn.metrics.pairwise import cosine_similarity
import re
import json
import os
import time
from google import genai
from google.genai import types

# =========================================
# 1. CLIENT INITIALIZATION
# =========================================
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        api_version='v1',
        retry_options=types.HttpRetryOptions(
            attempts=3,
            initial_delay=5.0,
            http_status_codes=[503, 429, 500]
        )
    )
)

# =========================================
# 2. FILE EXTRACTION UTILS
# =========================================
def extract_text_from_file(file_path):
    text = ""
    try:
        if file_path.endswith(".pdf"):
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        print(f"File extraction error: {e}")
    return text

def parse_json(text):
    try:
        # JSON-ஐ மட்டும் பிரித்தெடுக்க இது உதவும்
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            # தேவையற்ற நியூலைன் கேரக்டர்களை நீக்க
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            return json.loads(json_str)
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
    return None

# =========================================
# 3. EMBEDDING
# =========================================
def get_embedding(text):
    try:
        response = client.models.embed_content(
            model="embedding-001",
            contents=text[:4000]
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Embedding Error: {e}")
        return [0] * 768

# =========================================
# 4. MAIN ATS ENGINE
# =========================================
def analyze_application_ats(resume_text, job_description):
    print("--- ATS Engine Started (Batch Mode) ---")
    
    combined_prompt = f"""
You are an expert ATS evaluator.

Your task is to analyze ANY resume against ANY job description dynamically.

STRICT RULES:
- Use ONLY the information present in the Resume and Job Description.
- DO NOT invent or assume any skills.
- DO NOT match unrelated technologies.
- DO NOT include soft skills unless explicitly required in the JD.
- Output must be valid JSON only.

SKILL EXTRACTION RULES:
1. Extract important technical and role-relevant skills only.
2. Avoid generic words like "development", "coding", "project".
3. Normalize similar terms (e.g., REST API = RESTful API).

SMART MATCHING RULE:
4. Match skills using meaning, not exact words only.
5. A match is valid if:
   - exact match
   - synonym or abbreviation (OOP = Object-Oriented Programming)
   - same technology ecosystem (Spring Boot = Spring Framework)
   - same category (MySQL, PostgreSQL = SQL databases)
   - tool/framework proves the skill (Spring Boot project = Spring Boot familiarity)

6. DO NOT match:
   - different technologies (Java ≠ JavaScript)
   - unrelated categories (SQL ≠ MongoDB unless clearly required)
   - weak or unclear relationships

EXPERIENCE CALCULATION RULES:
7. "experience_months" means ONLY real work experience.
8. Count ONLY if clearly mentioned:
   - full-time job
   - part-time job
   - internship
   - freelance work
   - contract work
   - company role with dates

9. DO NOT count:
   - education duration
   - degree timeline
   - academic projects
   - personal projects
   - self-learning
   - certifications
   - coding practice

10. Only count months when start and end dates are clearly present.
11. If real work experience is not clearly present, return 0.
12. Never estimate from education timeline.

TASK:
- Extract resume skills
- Extract JD skills
- Perform semantic matching
- Calculate real experience

RETURN ONLY THIS JSON:

{{
  "skills_data": {{
    "resume_skills": [],
    "jd_skills": [],
    "matched_skills": []
  }},
  "experience_months": 0,
  "ai_feedback": ""
}}

FEEDBACK RULES:
- Use very simple English
- Clearly explain:
  - Why rejected / low score
  - Missing skills
  - Strong skills in resume
  - How to improve
- Keep it short and direct
- No markdown, no extra formatting

Now analyze:

Job Description:
{job_description}

Resume:
{resume_text}

"""

    try:
        # Step 1: Call Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=combined_prompt
        )
        
        data = parse_json(response.text)
        if not data:
            raise ValueError("AI returned invalid format")

        # Step 2: UPDATED EXPERIENCE LOGIC (Fresher Friendly)
        resume_months = data.get("experience_months", 0)
        jd_years_match = re.findall(r'(\d+)\s*(year|years)', job_description.lower())
        jd_exp_years = int(jd_years_match[0][0]) if jd_years_match else 0
        
        if jd_exp_years == 0: 
            # If the job is for freshers, give a base score for having projects/skills
            # This prevents 0/0 error or rejecting top students
            exp_score = 80 if len(data['skills_data'].get('resume_skills', [])) > 5 else 50
        else: 
            exp_score = min(((resume_months / 12) / jd_exp_years) * 100, 100)

        # Step 3: Skill Score
        jd_skills_list = data['skills_data'].get("jd_skills", [])
        matched_skills_list = data['skills_data'].get("matched_skills", [])
        skill_score = (len(matched_skills_list) / len(jd_skills_list) * 100) if jd_skills_list else 0

        # Step 4: Embedding Score
        resume_emb = get_embedding(resume_text)
        jd_emb = get_embedding(job_description)
        embedding_score = cosine_similarity([resume_emb], [jd_emb])[0][0] * 100

        # Step 5: Final Weighted Score
        final_score = round((embedding_score * 0.5 + skill_score * 0.3 + exp_score * 0.2), 2)

        print(f"✅ Success! Score: {final_score}")
        return {
            "match_score": final_score,
            "status": "shortlisted" if final_score >= 65 else "rejected",
            "suggestions": data.get("ai_feedback", "No feedback generated."),
            "is_shortlisted": final_score >= 65
        }

    except Exception as e:
        error_str = str(e)
        print(f"❌ Error: {error_str}")
        msg = "AI Server is busy. Please wait 60 seconds." if "429" in error_str else f"Error: {error_str}"
        return {
            "match_score": 0,
            "status": "rejected",
            "suggestions": msg,
            "is_shortlisted": False
        }