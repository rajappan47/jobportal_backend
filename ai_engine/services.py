import fitz  # PyMuPDF
from docx import Document
import re
import json
import os
import time
from google import genai
from django.conf import settings

# ✅ Step 1: Initialize Client ONCE at the top
# Make sure GEMINI_API_KEY is in your .env file
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1'} 
)

def extract_text_from_file(file_path):
    """Automatically extracts text from PDF or DOCX."""
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

def safe_json_parse(text):
    """Cleans AI response and converts to Python Dictionary."""
    try:
        # Removes markdown blocks like ```json ... ```
        clean_text = re.sub(r'```json|```', '', text).strip()
        # Find the first { and last } to ignore any text outside the JSON
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        return {
            "match_score": 0,
            "is_shortlisted": False,
            "suggestions": "AI analysis format error."
        }

def analyze_application_ats(resume_text, job_description):
    print("--- ATS Engine Started ---")
    
    # Improved prompt to avoid conversational filler
    prompt = f"""
    You are an ATS system. Analyze the following Resume against the Job Description.
    Return ONLY a JSON object with no preamble or explanation.
    
    JD: {job_description}
    Resume: {resume_text}

    Format:
    {{
      "match_score": <int>,
      "is_shortlisted": <bool>,
      "suggestions": "<detailed string explaining why or how to improve>"
    }}
    """

    for attempt in range(3):
        try:
            print(f"Attempting AI Call {attempt + 1}...")
            
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")

            # Use our robust parser
            result = safe_json_parse(response.text)
            
            # ✅ Crucial: Ensure the status field exists for your React Frontend
            result['status'] = 'shortlisted' if result.get('is_shortlisted') else 'rejected'
            
            print("✅ AI Success!")
            return result

        except Exception as e:
            print(f"❌ Attempt {attempt+1} Error: {str(e)}")
            # Handle Quota limits
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("Quota reached. Sleeping for 40s...")
                time.sleep(40)
                continue
            break

    return {
        "match_score": 0,
        "status": "rejected",
        "suggestions": "The AI service is currently unavailable. Please try again in a few minutes."
    }