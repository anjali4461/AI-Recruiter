# 🎯 AI Recruiter — Intelligent Candidate Ranking System

> **Rank candidates the way a great recruiter would — by understanding people, not just matching keywords.**

Built with Python + Streamlit, powered by **Groq's free LLaMA 3.1 8B Instant** model.

---

## 📌 What Problem Does This Solve?

Traditional ATS (Applicant Tracking Systems) filter candidates by keyword matching. They miss great candidates who describe their skills differently, and they pass through bad fits who've stuffed their resumes with buzzwords.

This system reads job descriptions and candidate profiles the way a senior recruiter would — understanding career trajectory, actual impact, behavioural signals, and genuine fit — then delivers a ranked shortlist you can trust.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Flexible JD Input** | Upload Job Description as **PDF or Word (.docx)** |
| 🗃️ **Bulk JSON Candidates** | Upload one JSON file with **50+ candidate profiles** at once |
| 🧠 **AI-Powered Analysis** | LLaMA 3.1 evaluates career history, skills, trajectory & platform signals |
| 🏆 **Top 10 Shortlist** | Ranked candidates with scores across 4 dimensions |
| 📥 **PDF Report** | Professional downloadable shortlist with name, skills, experience & interview questions |
| 📊 **CSV Export** | Spreadsheet-friendly export for your ATS or team |
| 🔐 **API Key Hidden** | Key stored in `.env` — never visible in code or UI |

---

## 🧠 How the AI Thinks

Unlike keyword filters, the AI evaluates each candidate across **4 dimensions**:

```
Overall Fit Score (0–100)
├── 🛠  Technical Fit      — Skills & tools match vs JD requirements
├── 📅  Experience Fit     — Domain depth, seniority, industry alignment
├── 🤝  Cultural Fit       — Values, work style, communication signals
└── 📡  Availability       — Active on platform, notice period, open to work
```

**What the AI specifically watches for:**
- Career history at **consulting-only firms** (TCS, Infosys, Wipro) with no product company experience
- **Skill inflation** — skills listed with many endorsements but no evidence in job history
- **Behavioural signals** — last login date, recruiter response rate, profile completeness
- **Production ML vs side projects** — actual deployed systems vs Kaggle/tutorials
- Candidates whose profile keywords look perfect but whose career tells a different story

---

## 📁 Project Structure

```
ai_recruiter/
├── app.py                  # Main Streamlit application (900+ lines)
├── requirements.txt        # Python dependencies
├── .env.example            # API key template (rename to .env)
├── .env                    # Your actual key — NOT committed to git
├── .gitignore              # Protects .env from being pushed
├── README.md               # This file
│
├── sample_data/            # (Optional) Test files
│   ├── JD_Senior_AI_Engineer_Redrob.pdf   # Sample job description PDF
│   ├── JD_Senior_Data_Scientist.pdf       # Another sample JD
│   └── candidates.json                    # 50 sample candidate profiles
│
└── sample_resumes/         # (Optional) Individual resume PDFs
    ├── Resume_Aanya_Sharma.pdf
    ├── Resume_Rohan_Mehta.pdf
    ├── Resume_Priya_Nair.pdf
    ├── Resume_Karthik_Rao.pdf
    └── Resume_Sneha_Kulkarni.pdf
```

---

## 🚀 Quick Start

### 1. Clone / Download the project

```bash
git clone <your-repo-url>
cd ai_recruiter
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get a FREE Groq API key

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up (free, no credit card needed)
3. Create an API key

### 4. Set up your API key

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder:

```env
GROQ_API_KEY=your_actual_key_here
```

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`

---

## 📖 How to Use

### Step 1 — Upload the Job Description
- Click **"Upload JD"**
- Accepts **PDF** (`.pdf`) or **Word** (`.docx` / `.doc`)
- The AI will extract role requirements, must-have skills, cultural signals, and explicit disqualifiers

### Step 2 — Upload the Candidate JSON
- Click **"Upload candidates JSON"**
- Upload your `candidates.json` file (Redrob platform format)
- Supports 50+ candidate profiles in a single file

### Step 3 — Click Analyse
- The app reads the JD deeply (not just keywords)
- Evaluates every candidate against the role
- Shows a progress bar as each profile is analysed

### Step 4 — Review the Shortlist
- Top 10 candidates ranked by overall fit score
- Expand any card for the full profile breakdown
- See matched skills, gaps, strengths, concerns, and tailored interview questions

### Step 5 — Export
- **PDF Report** — Professional document with cover page, ranking table, and full candidate profiles
- **CSV** — Spreadsheet export of all scores and metadata

---

## 📂 Candidate JSON Format

The app expects a JSON array where each object follows the Redrob platform schema:

```json
[
  {
    "candidate_id": "CAND_0000001",
    "profile": {
      "anonymized_name": "Jane Doe",
      "headline": "ML Engineer | Search & Retrieval",
      "summary": "...",
      "location": "Bangalore",
      "country": "India",
      "years_of_experience": 6.0,
      "current_title": "ML Engineer",
      "current_company": "Swiggy",
      "current_company_size": "5001-10000",
      "current_industry": "Food Delivery"
    },
    "career_history": [
      {
        "company": "Swiggy",
        "title": "ML Engineer",
        "start_date": "2022-01-01",
        "end_date": null,
        "duration_months": 30,
        "is_current": true,
        "industry": "Food Delivery",
        "company_size": "5001-10000",
        "description": "Built ranking models using XGBoost/LightGBM..."
      }
    ],
    "education": [...],
    "skills": [
      {
        "name": "FAISS",
        "proficiency": "advanced",
        "endorsements": 40,
        "duration_months": 44
      }
    ],
    "certifications": [...],
    "languages": [...],
    "redrob_signals": {
      "profile_completeness_score": 83.4,
      "last_active_date": "2026-05-24",
      "open_to_work_flag": true,
      "recruiter_response_rate": 0.91,
      "notice_period_days": 60,
      "willing_to_relocate": true,
      "github_activity_score": 32.6,
      "skill_assessment_scores": {"FAISS": 68.4}
    }
  }
]
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit |
| **AI Model** | Groq — LLaMA 3.1 8B Instant (free tier) |
| **PDF Reading** | pdfplumber |
| **Word Reading** | python-docx |
| **PDF Generation** | ReportLab |
| **Data** | pandas |
| **Language** | Python 3.9+ |

---

## 🔐 API Key Security

Your Groq API key is protected at every level:

| Layer | How |
|---|---|
| **Storage** | Only in `.env` file on your machine |
| **Code** | Read via `os.getenv()` — never hardcoded |
| **Git** | `.env` listed in `.gitignore` — never pushed |
| **UI** | Never displayed in Streamlit interface |

---

## 📊 Understanding the Scores

| Score | Range | Meaning |
|---|---|---|
| 80–100 | 🟢 Strong | Excellent fit — prioritise for interview |
| 60–79  | 🟡 Good   | Solid fit — worth interviewing |
| 40–59  | 🟠 Partial | Partial fit — consider based on team needs |
| 0–39   | 🔴 Weak   | Poor fit — likely to be a mismatch |

### Interview Recommendation Labels
- 🟢 **Strong Yes** — High fit across all dimensions, available, strong signals
- 🟡 **Yes** — Good fit, minor gaps, worth pursuing
- 🟠 **Maybe** — Has potential but significant gaps or concerns
- 🔴 **No** — Does not meet core requirements

---

## 💡 Tips for Best Results

**For Job Descriptions:**
- Use text-based PDFs (not scanned/image PDFs)
- The more detailed the JD, the better the AI understands the role
- Word documents work great too

**For Candidate JSON:**
- Include full career history with descriptions — the AI uses these to verify skill claims
- Platform signals (last active date, open to work, response rate) significantly affect availability score
- The more complete the profiles, the more accurate the ranking

**For Large Batches:**
- Groq's free tier has rate limits — batches of 50 candidates may take 3–5 minutes
- The progress bar shows real-time status for each candidate

---

## 🔄 Switching AI Models

The model is defined in one place at the top of `app.py`:

```python
GROQ_MODEL = "llama-3.1-8b-instant"
```

Other free Groq models you can swap in:

| Model | Speed | Quality |
|---|---|---|
| `llama-3.1-8b-instant` | ⚡ Fastest | Good |
| `llama-3.3-70b-versatile` | 🐢 Slower | Better |
| `mixtral-8x7b-32768` | ⚡ Fast | Good |
| `gemma2-9b-it` | ⚡ Fast | Good |

---

## 🐛 Troubleshooting

**`GROQ_API_KEY not found`**
→ Make sure you created a `.env` file (not just `.env.example`) and it contains `GROQ_API_KEY=your_key`

**`PDF read error`**
→ The PDF may be scanned/image-based. Try a text-based PDF or copy-paste the JD into a Word document.

**`JSON parse error`**
→ Validate your JSON at [jsonlint.com](https://jsonlint.com/) — the file must be a valid JSON array.

**`Rate limit exceeded`**
→ Groq free tier has per-minute limits. Wait 60 seconds and try again, or reduce batch size.

**`python-docx not installed`**
→ Run `pip install python-docx` separately.

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Acknowledgements

- **Groq** for the blazing-fast free LLM inference
- **Meta** for the LLaMA 3.1 open-source model
- **Streamlit** for making Python UIs painless
- **ReportLab** for PDF generation
- Built as part of the **Redrob Hackathon — Intelligent Candidate Discovery & Ranking Challenge**
