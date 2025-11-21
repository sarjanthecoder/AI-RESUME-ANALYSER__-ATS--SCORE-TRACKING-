import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import PyPDF2
import docx
import io
import json
import hashlib

app = Flask(__name__)
CORS(app)

# -------------------------------------------------------
# GEMINI CONFIGURATION
# -------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # replace with real API key
genai.configure(api_key=GEMINI_API_KEY)

# Deterministic Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")

# Cache to ensure same resume = same output
analysis_cache = {}


# -------------------------------------------------------
# PDF / DOCX TEXT EXTRACTION
# -------------------------------------------------------
def extract_text_from_pdf(file):
    pdf = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(file):
    document = docx.Document(file)
    text = ""
    for para in document.paragraphs:
        text += para.text + "\n"
    return text


# -------------------------------------------------------
# NORMALIZATION → ensures same hash even if spacing differs
# -------------------------------------------------------
def normalize_text(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


# -------------------------------------------------------
# GEMINI RESUME ANALYSIS (FULLY DETERMINISTIC)
# -------------------------------------------------------
def analyze_resume_with_gemini(resume_text):
    # Normalize before hashing
    normalized_text = normalize_text(resume_text)

    resume_hash = hashlib.md5(normalized_text.encode()).hexdigest()

    # Return cached version (same resume → same score)
    if resume_hash in analysis_cache:
        print("Returning cached result:", resume_hash)
        return analysis_cache[resume_hash]

    prompt = f"""
    You are an expert ATS resume analyzer. 
    You must return STRICT deterministic scoring based ONLY on text. 
    No randomness.

    Resume:
    {normalized_text}

    Return ONLY valid JSON:
    {{
        "overall_score": <0-100>,
        "sections": [
            {{
                "name": "Contact Information",
                "score": <0-100>,
                "recommendations": ["..."]
            }},
            {{
                "name": "Professional Summary",
                "score": <0-100>,
                "recommendations": ["..."]
            }},
            {{
                "name": "Work Experience",
                "score": <0-100>,
                "recommendations": ["..."]
            }},
            {{
                "name": "Skills",
                "score": <0-100>,
                "recommendations": ["..."]
            }},
            {{
                "name": "Education",
                "score": <0-100>,
                "recommendations": ["..."]
            }},
            {{
                "name": "Formatting & ATS Compatibility",
                "score": <0-100>,
                "recommendations": ["..."]
            }}
        ]
    }}
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "top_p": 0,
                "top_k": 1,
                "candidate_count": 1
            }
        )

        result_text = response.text.strip()

        # Remove code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        result = json.loads(result_text)

        # Store in cache
        analysis_cache[resume_hash] = result

        return result

    except Exception as e:
        print("Gemini error:", e)
        return {
            "overall_score": 50,
            "sections": [
                {
                    "name": "Error",
                    "score": 50,
                    "recommendations": [
                        "Analysis failed.",
                        str(e)
                    ]
                }
            ]
        }


# -------------------------------------------------------
# RENDER index.html
# -------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")   # /templates/index.html must exist


# -------------------------------------------------------
# RESUME ANALYSIS API
# -------------------------------------------------------
@app.route("/analyze", methods=["POST"])
def analyze_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["resume"]
        filename = file.filename.lower()

        file_bytes = file.read()
        file.seek(0)

        # File type detection
        if filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(io.BytesIO(file_bytes))
        elif filename.endswith(".docx"):
            resume_text = extract_text_from_docx(io.BytesIO(file_bytes))
        else:
            return jsonify({"error": "Upload only PDF or DOCX"}), 400

        if not resume_text.strip():
            return jsonify({"error": "Could not extract text"}), 400

        # Analyze
        result = analyze_resume_with_gemini(resume_text)

        return jsonify(result)

    except Exception as e:
        print("Server error:", e)
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# -------------------------------------------------------
# RUN SERVER
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
