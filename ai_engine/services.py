import fitz  # PyMuPDF
from docx import Document
from sklearn.metrics.pairwise import cosine_similarity
import re
import json
import os
import time
from google import genai
from google.genai import types
from django.conf import settings

# =========================================
# 1. CLIENT INITIALIZATION (With Auto-Retry)
# =========================================
# This solves the 503 UNAVAILABLE error by retrying automatically.
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        api_version='v1',
        retry_options=types.HttpRetryOptions(
            attempts=4,
            initial_delay=2.0,
            http_status_codes=[503, 429, 500]
        )
    )
)

# =========================================
# 2. FILE EXTRACTION UTILS
# =========================================
def extract_text_from_file(file_path):
    """Exactly like your Colab extract_text."""
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
    """Cleans AI response and converts to Dictionary."""
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group(0))
    except:
        return {"skills": [], "experience": []}

# =========================================
# 3. HELPER FUNCTIONS (Your Colab Logic)
# =========================================
def safe_generate(prompt):
    """Uses the 2026 Stable Flash model."""
    return client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )

def get_embedding(text):
    """Generates vectors for semantic matching."""
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text[:5000] # Limit to 5k chars for stability
    )
    return response.embeddings[0].values

def convert_to_months(duration):
    duration = duration.lower()
    years = re.findall(r'(\d+)\s*year', duration)
    months = re.findall(r'(\d+)\s*month', duration)
    total = 0
    if years: total += int(years[0]) * 12
    if months: total += int(months[0])
    return total

# =========================================
# 4. MAIN ATS ENGINE
# =========================================
def analyze_application_ats(resume_text, job_description):
    print("--- ATS Engine Started ---")
    
    try:
        # 1️⃣ Extract Skills & Experience from Resume
        resume_data_raw = safe_generate(f"""
        Extract technical skills and work experience. Return ONLY JSON:
        {{ "skills": ["..."], "experience": [{{"duration": "1 year"}}] }}
        Text: {resume_text}
        """)
        resume_data = parse_json(resume_data_raw.text)

        # 2️⃣ Extract Skills from JD
        jd_data_raw = safe_generate(f"""
        Extract ONLY technical skills from this Job Description. Return JSON:
        {{ "skills": ["java", "spring boot"] }}
        Text: {job_description}
        """)
        jd_data = parse_json(jd_data_raw.text)

        # 3️⃣ Semantic Skill Matching
        resume_skills = set([s.lower() for s in resume_data.get("skills", [])])
        jd_skills = set([s.lower() for s in jd_data.get("skills", [])])
        
        skill_prompt = f"""
        You are an expert recruiter.
        Candidate Skills: {", ".join(resume_skills)}
        Job Requirements: {", ".join(jd_skills)}
        Return JSON: {{ "matched_jd_skills": [] }}
        """
        skill_match_res = safe_generate(skill_prompt)
        matched_data = parse_json(skill_match_res.text)
        
        matched_count = len(matched_data.get("matched_jd_skills", []))
        skill_score = (matched_count / len(jd_skills)) * 100 if jd_skills else 0

        # 4️⃣ Experience Scoring
        resume_months = sum(convert_to_months(job.get("duration", "0")) for job in resume_data.get("experience", []))
        jd_years_match = re.findall(r'(\d+)\s*(year|years)', job_description.lower())
        jd_exp_years = int(jd_years_match[0][0]) if jd_years_match else 0
        
        if jd_exp_years == 0: exp_score = 100
        else: exp_score = min(((resume_months / 12) / jd_exp_years) * 100, 100)

        # 5️⃣ Embedding Score (Cosine Similarity)
        resume_emb = get_embedding(resume_text)
        jd_emb = get_embedding(job_description)
        embedding_score = cosine_similarity([resume_emb], [jd_emb])[0][0] * 100

        # 6️⃣ Final Weighted Score
        final_score = round((embedding_score * 0.5 + skill_score * 0.3 + exp_score * 0.2), 2)

        # 7️⃣ YOUR EXACT COLAB FEEDBACK PROMPT
        feedback_prompt = f"""
        Job Description:
        {job_description}

        Resume:
        {resume_text}

        Score: {final_score}%

        Explain:
        - Why rejected
        - Missing skills
        - Improvements
        """
        feedback_res = safe_generate(feedback_prompt)

        print(f"✅ AI Success! Score: {final_score}")
        return {
            "match_score": final_score,
            "status": "shortlisted" if final_score >= 65 else "rejected",
            "suggestions": feedback_res.text,
            "is_shortlisted": final_score >= 65
        }

    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        return {
            "match_score": 0,
            "status": "rejected",
            "suggestions": f"Technical Issue: {str(e)}. Please try again."
        }