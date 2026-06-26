import streamlit as st
import pdfplumber
import json
import os
import io
import time
import tempfile
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import pandas as pd

# ── DOCX support ─────────────────────────────────────────────────────────────
try:
    from docx import Document as DocxDocument
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

# ── PDF generation ────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 HRFlowable, Table, TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Recruiter", page_icon="🎯", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem; border-radius: 16px; color: white;
    margin-bottom: 2rem; text-align: center;
}
.main-header h1 { font-size: 2.2rem; font-weight: 700; margin: 0; }
.main-header p  { font-size: 1rem; opacity: 0.85; margin-top: 0.5rem; }

.section-card {
    background: #f8f9ff; border: 1px solid #e0e4f7;
    border-radius: 12px; padding: 1.4rem; margin-bottom: 1.5rem;
}
.section-card h3 { color: #4a5568; margin-top: 0; }

.candidate-card {
    background: white; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 1.4rem; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.rank-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    font-weight: 700; font-size: 1rem; color: white; margin-right: 12px;
}
.r1 { background: #f6c90e; color: #333; }
.r2 { background: #a0aec0; color: #333; }
.r3 { background: #cd7f32; }
.ro { background: #667eea; }

.score-bar-bg { background:#edf2f7; border-radius:999px; height:10px; width:100%; margin-top:6px; }
.score-bar    { height:10px; border-radius:999px; background:linear-gradient(90deg,#667eea,#764ba2); }

.skill-tag  { display:inline-block; background:#ebf4ff; color:#2b6cb0; border-radius:999px; padding:3px 11px; font-size:0.77rem; margin:3px; font-weight:500; }
.str-tag    { display:inline-block; background:#f0fff4; color:#276749; border-radius:999px; padding:3px 11px; font-size:0.77rem; margin:3px; font-weight:500; }
.gap-tag    { display:inline-block; background:#fff5f5; color:#c53030; border-radius:999px; padding:3px 11px; font-size:0.77rem; margin:3px; font-weight:500; }

.insight-box { background:#f7f8ff; border-left:4px solid #667eea; border-radius:0 8px 8px 0; padding:1rem 1.2rem; margin-top:0.8rem; font-size:0.92rem; color:#4a5568; }
.stat-box    { background:white; border:1px solid #e2e8f0; border-radius:10px; padding:1rem; text-align:center; }
.stat-num    { font-size:1.9rem; font-weight:700; color:#667eea; }
.stat-label  { font-size:0.78rem; color:#718096; text-transform:uppercase; letter-spacing:0.05em; }
.jd-insight  { background:linear-gradient(135deg,#f6f9ff 0%,#fff6ff 100%); border:1px solid #c3d0f7; border-radius:12px; padding:1.1rem 1.4rem; margin-bottom:1rem; }
.jd-insight h4 { color:#553c9a; margin:0 0 0.5rem; }

.stButton > button {
    background: linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    color:white; border:none; border-radius:10px;
    padding:0.6rem 2rem; font-weight:600; font-size:1rem; width:100%;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

GROQ_MODEL = "llama-3.1-8b-instant"

def get_model():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found. Add it to your .env file.")
        st.stop()
    return Groq(api_key=api_key)


def call_llm(client, prompt: str) -> str:
    """Call Groq LLaMA and return text response."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


# ── Text extractors ───────────────────────────────────────────────────────────

def extract_pdf_text(uploaded_file) -> str:
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        st.warning(f"PDF read error: {e}")
    return text.strip()


def extract_docx_text(uploaded_file) -> str:
    if not DOCX_OK:
        st.error("python-docx not installed. Run: pip install python-docx")
        return ""
    try:
        doc = DocxDocument(io.BytesIO(uploaded_file.read()))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        st.warning(f"DOCX read error: {e}")
        return ""


def extract_jd_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)
    elif name.endswith(".docx") or name.endswith(".doc"):
        return extract_docx_text(uploaded_file)
    else:
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except:
            return ""


# ── JSON candidate loader ─────────────────────────────────────────────────────

def load_candidates_from_json(uploaded_file) -> list:
    """Parse the Redrob-format JSON and return list of candidate dicts."""
    try:
        raw = json.loads(uploaded_file.read())
    except Exception as e:
        st.error(f"JSON parse error: {e}")
        return []

    candidates = []
    for c in raw:
        p   = c.get("profile", {})
        rs  = c.get("redrob_signals", {})
        ch  = c.get("career_history", [])
        sk  = c.get("skills", [])
        ed  = c.get("education", [])
        ce  = c.get("certifications", [])
        lng = c.get("languages", [])

        # Build a rich text blob for the AI to analyse
        career_text = ""
        for job in ch:
            career_text += (
                f"\n  - {job.get('title','?')} @ {job.get('company','?')} "
                f"({job.get('industry','?')}, {job.get('company_size','?')}) "
                f"— {job.get('duration_months','?')} months "
                f"{'[CURRENT]' if job.get('is_current') else ''}\n"
                f"    {job.get('description','')}"
            )

        skill_text = ", ".join(
            f"{s['name']} ({s.get('proficiency','?')}, {s.get('endorsements',0)} endorsements, "
            f"{s.get('duration_months',0)}m)"
            for s in sk
        )

        edu_text = "; ".join(
            f"{e.get('degree','?')} in {e.get('field_of_study','?')} from "
            f"{e.get('institution','?')} ({e.get('tier','?')}, {e.get('grade','?')})"
            for e in ed
        )

        cert_text = "; ".join(
            f"{c2.get('name','?')} ({c2.get('issuer','?')}, {c2.get('year','?')})"
            for c2 in ce
        ) or "None"

        # Behavioural signals summary
        last_active = rs.get("last_active_date", "?")
        sig_text = (
            f"Open to work: {rs.get('open_to_work_flag', False)} | "
            f"Last active: {last_active} | "
            f"Notice period: {rs.get('notice_period_days','?')} days | "
            f"Willing to relocate: {rs.get('willing_to_relocate', False)} | "
            f"Preferred mode: {rs.get('preferred_work_mode','?')} | "
            f"Recruiter response rate: {rs.get('recruiter_response_rate','?')} | "
            f"Avg response time: {rs.get('avg_response_time_hours','?')}h | "
            f"Interview completion: {rs.get('interview_completion_rate','?')} | "
            f"Profile completeness: {rs.get('profile_completeness_score','?')}% | "
            f"GitHub activity score: {rs.get('github_activity_score','?')} | "
            f"Search appearances 30d: {rs.get('search_appearance_30d','?')} | "
            f"Skill assessment scores: {json.dumps(rs.get('skill_assessment_scores', {}))} | "
            f"Expected salary: {json.dumps(rs.get('expected_salary_range_inr_lpa', {}))} LPA"
        )

        profile_text = f"""
CANDIDATE: {p.get('anonymized_name','Unknown')} [{c.get('candidate_id','?')}]
HEADLINE: {p.get('headline','')}
LOCATION: {p.get('location','?')}, {p.get('country','?')}
EXPERIENCE: {p.get('years_of_experience','?')} years
CURRENT ROLE: {p.get('current_title','?')} @ {p.get('current_company','?')} ({p.get('current_industry','?')}, {p.get('current_company_size','?')})

SUMMARY: {p.get('summary','')}

CAREER HISTORY:{career_text}

EDUCATION: {edu_text}

SKILLS: {skill_text}

CERTIFICATIONS: {cert_text}

LANGUAGES: {', '.join(f"{l['language']} ({l.get('proficiency','?')})" for l in lng)}

PLATFORM SIGNALS: {sig_text}
"""
        candidates.append({
            "id": c.get("candidate_id", "?"),
            "name": p.get("anonymized_name", "Unknown"),
            "years_exp": p.get("years_of_experience", 0),
            "current_title": p.get("current_title", "?"),
            "current_company": p.get("current_company", "?"),
            "location": f"{p.get('location','?')}, {p.get('country','?')}",
            "skills_raw": [s["name"] for s in sk],
            "profile_text": profile_text,
            "open_to_work": rs.get("open_to_work_flag", False),
            "last_active": last_active,
            "notice_days": rs.get("notice_period_days", "?"),
            "relocate": rs.get("willing_to_relocate", False),
        })
    return candidates


# ═══════════════════════════════════════════════════════════════════════════
# AI ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_jd(model, jd_text: str) -> dict:
    prompt = f"""You are a senior recruiter with 15+ years experience. Deeply analyse this job description.

JOB DESCRIPTION:
{jd_text}

Return ONLY valid JSON (no markdown fences):
{{
  "role_title": "...",
  "company_context": "...",
  "core_mission": "...",
  "must_have_skills": ["..."],
  "nice_to_have_skills": ["..."],
  "experience_level": "...",
  "years_experience_required": "...",
  "technical_depth": "low|medium|high",
  "leadership_required": true/false,
  "key_responsibilities": ["..."],
  "success_indicators": ["..."],
  "cultural_signals": ["..."],
  "red_flags_to_watch": ["..."],
  "industry_domain": "...",
  "role_type": "technical|non-technical|hybrid",
  "explicit_disqualifiers": ["things JD explicitly says are NOT wanted"]
}}"""
    raw = call_llm(model, prompt).replace("```json","").replace("```","").strip()
    return json.loads(raw)


def analyze_candidate(model, candidate: dict, jd_analysis: dict) -> dict:
    prompt = f"""You are a senior recruiter. Evaluate this candidate against the role.
Think like a great recruiter — look beyond keywords. Consider career trajectory, actual impact,
production vs side-project experience, behavioural signals from platform data.

ROLE REQUIREMENTS:
{json.dumps(jd_analysis, indent=2)}

CANDIDATE PROFILE:
{candidate['profile_text']}

IMPORTANT NUANCES:
- Skills listed on a profile do NOT automatically mean production experience. Cross-check with career history.
- Platform signals matter: last_active_date, recruiter_response_rate, open_to_work_flag, notice_period_days.
- A candidate who hasn't logged in for 6+ months or has open_to_work=false may not be truly available.
- Career history at consulting-only firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini) is a concern
  if there's no product-company experience — weigh accordingly.
- Watch for skill inflation: many endorsements for a skill rarely used in job descriptions = suspicious.

Return ONLY valid JSON (no markdown fences):
{{
  "candidate_name": "...",
  "overall_fit_score": 0-100,
  "technical_fit_score": 0-100,
  "experience_fit_score": 0-100,
  "cultural_fit_score": 0-100,
  "availability_score": 0-100,
  "matched_skills": ["..."],
  "missing_critical_skills": ["..."],
  "key_strengths": ["..."],
  "potential_concerns": ["..."],
  "standout_achievements": ["..."],
  "career_trajectory": "ascending|stable|lateral|unclear",
  "production_ml_evidence": "yes|no|partial",
  "consulting_only_flag": true/false,
  "availability_assessment": "highly available|available|uncertain|unlikely available",
  "recruiter_summary": "2-3 sentence human-readable fit summary",
  "interview_recommendation": "strong yes|yes|maybe|no",
  "top_interview_questions": ["...", "...", "..."]
}}"""
    raw = call_llm(model, prompt).replace("```json","").replace("```","").strip()
    return json.loads(raw)


# ═══════════════════════════════════════════════════════════════════════════
# PDF REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def score_color_rl(score: int):
    if score >= 80: return colors.HexColor('#276749')
    if score >= 60: return colors.HexColor('#d69e2e')
    return colors.HexColor('#c53030')


def generate_shortlist_pdf(ranked: list, jd: dict, total_analysed: int) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=0.7*inch, rightMargin=0.7*inch,
                            topMargin=0.7*inch, bottomMargin=0.7*inch)
    styles = getSampleStyleSheet()

    # ── Custom styles ──
    cover_title = ParagraphStyle('CT', parent=styles['Title'], fontSize=22,
                                  textColor=colors.HexColor('#553c9a'), spaceAfter=6, alignment=TA_CENTER)
    cover_sub   = ParagraphStyle('CS', parent=styles['Normal'], fontSize=11,
                                  textColor=colors.HexColor('#718096'), spaceAfter=4, alignment=TA_CENTER)
    cover_body  = ParagraphStyle('CB', parent=styles['Normal'], fontSize=9.5,
                                  textColor=colors.HexColor('#4a5568'), alignment=TA_CENTER, leading=15)
    section_h   = ParagraphStyle('SH', parent=styles['Heading1'], fontSize=13,
                                  textColor=colors.HexColor('#553c9a'), spaceBefore=16, spaceAfter=4)
    rank_h      = ParagraphStyle('RH', parent=styles['Normal'], fontSize=14,
                                  textColor=colors.HexColor('#1a202c'), fontName='Helvetica-Bold', spaceAfter=2)
    sub_h       = ParagraphStyle('SUB', parent=styles['Normal'], fontSize=9.5,
                                  textColor=colors.HexColor('#718096'), spaceAfter=6)
    label_s     = ParagraphStyle('LBL', parent=styles['Normal'], fontSize=9,
                                  textColor=colors.HexColor('#553c9a'), fontName='Helvetica-Bold',
                                  spaceBefore=8, spaceAfter=2)
    body_s      = ParagraphStyle('BD', parent=styles['Normal'], fontSize=9.5,
                                  textColor=colors.HexColor('#2d3748'), spaceAfter=3, leading=14)
    tag_s       = ParagraphStyle('TG', parent=styles['Normal'], fontSize=9,
                                  textColor=colors.HexColor('#2b6cb0'), spaceAfter=4, leading=13)
    concern_s   = ParagraphStyle('CN', parent=styles['Normal'], fontSize=9,
                                  textColor=colors.HexColor('#c53030'), spaceAfter=3, leading=13)
    insight_s   = ParagraphStyle('IS', parent=styles['Normal'], fontSize=9.5,
                                  textColor=colors.HexColor('#4a5568'), spaceAfter=4, leading=14,
                                  leftIndent=8, rightIndent=8)
    footer_s    = ParagraphStyle('FT', parent=styles['Normal'], fontSize=8,
                                  textColor=colors.HexColor('#a0aec0'), alignment=TA_CENTER)

    def hr(c='#e2e8f0', t=0.8):
        return HRFlowable(width="100%", thickness=t, color=colors.HexColor(c), spaceAfter=6, spaceBefore=4)
    def sp(h=6): return Spacer(1, h)

    story = []

    # ── Cover Page ────────────────────────────────────────────────────────
    story += [
        sp(80),
        Paragraph("🎯 AI Recruiter", cover_title),
        Paragraph(f"Top 10 Candidate Shortlist", ParagraphStyle('CTB', parent=cover_title, fontSize=18, spaceAfter=6)),
        Paragraph(f"Role: {jd.get('role_title','Senior AI Engineer')}", cover_sub),
        sp(8), hr('#553c9a', 1.5), sp(8),
        Paragraph(
            f"Analysed {total_analysed} candidates from the Redrob platform. "
            f"Ranked by overall fit score across Technical Fit, Experience Fit, Cultural Fit, and Availability. "
            f"AI-powered evaluation using Gemini 2.5 Flash.",
            cover_body),
        sp(16),
    ]

    # Summary table on cover
    avg_score = int(sum(c.get('overall_fit_score', 0) for c in ranked) / len(ranked)) if ranked else 0
    strong = sum(1 for c in ranked if 'strong yes' in c.get('interview_recommendation','').lower())
    yes_c  = sum(1 for c in ranked if c.get('interview_recommendation','').lower() in ['yes','strong yes'])

    table_data = [
        ['Candidates\nAnalysed', 'Shortlisted', 'Avg Score', 'Strong\nRecommend', 'Recommend\nInterview'],
        [str(total_analysed), str(len(ranked)), f"{avg_score}/100", str(strong), str(yes_c)],
    ]
    tbl = Table(table_data, colWidths=[1.3*inch]*5)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#667eea')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ROWHEIGHT',  (0,0), (0,0), 28),
        ('ROWHEIGHT',  (0,1), (0,1), 32),
        ('FONTNAME',   (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,1), (-1,1), 14),
        ('TEXTCOLOR',  (0,1), (-1,1), colors.HexColor('#553c9a')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f0f4ff')),
        ('BOX',        (0,0), (-1,-1), 1, colors.HexColor('#c3d0f7')),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#e0e4f7')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    story.append(tbl)
    story.append(PageBreak())

    # ── Ranking Overview Table ────────────────────────────────────────────
    story.append(Paragraph("Ranking Overview", section_h))
    story.append(hr())

    ov_data = [['#', 'Name', 'Exp', 'Technical', 'Experience', 'Cultural', 'Avail.', 'Overall', 'Recommend']]
    for i, c in enumerate(ranked, 1):
        rec = c.get('interview_recommendation','?')
        rec_emoji = {'strong yes':'🟢 Strong Yes','yes':'🟡 Yes','maybe':'🟠 Maybe','no':'🔴 No'}.get(rec.lower(), rec)
        ov_data.append([
            f"#{i}",
            c.get('candidate_name','?'),
            f"{c.get('years_exp','?')}yr",
            str(c.get('technical_fit_score','?')),
            str(c.get('experience_fit_score','?')),
            str(c.get('cultural_fit_score','?')),
            str(c.get('availability_score','?')),
            str(c.get('overall_fit_score','?')),
            rec_emoji,
        ])

    col_ws = [0.35*inch, 1.3*inch, 0.45*inch, 0.7*inch, 0.75*inch, 0.65*inch, 0.55*inch, 0.65*inch, 1.1*inch]
    ov_tbl = Table(ov_data, colWidths=col_ws)
    ov_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#553c9a')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#f8f9ff')]),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.HexColor('#c3d0f7')),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, colors.HexColor('#e0e4f7')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('FONTNAME',   (0,1), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',   (7,1), (7,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',  (7,1), (7,-1), colors.HexColor('#553c9a')),
    ]))
    story.append(ov_tbl)
    story.append(PageBreak())

    # ── Individual Candidate Profiles ─────────────────────────────────────
    story.append(Paragraph("Detailed Candidate Profiles", section_h))

    for i, c in enumerate(ranked, 1):
        score = c.get('overall_fit_score', 0)
        rec   = c.get('interview_recommendation','?')
        rec_e = {'strong yes':'🟢 Strong Yes','yes':'🟡 Yes','maybe':'🟠 Maybe','no':'🔴 No'}.get(rec.lower(), rec)
        sc    = score_color_rl(score)

        story.append(hr('#c3d0f7', 1.2))
        story.append(sp(4))

        # Name + rank header
        story.append(Paragraph(
            f"<b>#{i} — {c.get('candidate_name','?')}</b>",
            rank_h))
        story.append(Paragraph(
            f"{c.get('current_title','?')} @ {c.get('current_company','?')}  ·  "
            f"{c.get('years_exp','?')} years exp  ·  {c.get('location','?')}  ·  {rec_e}",
            sub_h))

        # Score breakdown table
        score_data = [
            ['Overall Score', 'Technical', 'Experience', 'Cultural', 'Availability'],
            [str(score)+'/100',
             str(c.get('technical_fit_score','?')),
             str(c.get('experience_fit_score','?')),
             str(c.get('cultural_fit_score','?')),
             str(c.get('availability_score','?'))],
        ]
        s_tbl = Table(score_data, colWidths=[1.3*inch]*5)
        s_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0), colors.HexColor('#667eea')),
            ('TEXTCOLOR',  (0,0),(-1,0), colors.white),
            ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0),(-1,-1), 9),
            ('ALIGN',      (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
            ('FONTNAME',   (0,1),(-1,1), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,1),(-1,1), 13),
            ('TEXTCOLOR',  (0,1),(0,1),  sc),
            ('TEXTCOLOR',  (1,1),(-1,1), colors.HexColor('#553c9a')),
            ('BOX',        (0,0),(-1,-1), 0.8, colors.HexColor('#c3d0f7')),
            ('INNERGRID',  (0,0),(-1,-1), 0.3, colors.HexColor('#e0e4f7')),
            ('TOPPADDING', (0,0),(-1,-1), 7),
            ('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('ROWBACKGROUNDS',(0,1),(-1,1),[colors.HexColor('#f0f4ff')]),
        ]))
        story.append(s_tbl)
        story.append(sp(8))

        # Recruiter summary
        story.append(Paragraph("💡 Recruiter's Assessment", label_s))
        story.append(Paragraph(c.get('recruiter_summary','—'), insight_s))

        # Matched Skills
        skills = c.get('matched_skills', [])
        if skills:
            story.append(Paragraph("✅ Matched Skills", label_s))
            story.append(Paragraph("  ·  ".join(skills), tag_s))

        # Key Strengths
        strengths = c.get('key_strengths', [])
        if strengths:
            story.append(Paragraph("💪 Key Strengths", label_s))
            for s in strengths:
                story.append(Paragraph(f"  ✓  {s}", body_s))

        # Missing Skills + Concerns
        missing = c.get('missing_critical_skills', [])
        concerns = c.get('potential_concerns', [])
        if missing or concerns:
            story.append(Paragraph("⚠️ Gaps & Concerns", label_s))
            for m in missing:
                story.append(Paragraph(f"  ✗  {m}", concern_s))
            for cn in concerns:
                story.append(Paragraph(f"  •  {cn}", concern_s))

        # Key signals
        avail_txt = c.get('availability_assessment','?')
        prod_ml   = c.get('production_ml_evidence','?')
        consulting = c.get('consulting_only_flag', False)
        story.append(Paragraph("📊 Key Signals", label_s))
        story.append(Paragraph(
            f"Availability: {avail_txt}  ·  "
            f"Production ML: {prod_ml}  ·  "
            f"Consulting-only career: {'Yes ⚠️' if consulting else 'No'}  ·  "
            f"Career trajectory: {c.get('career_trajectory','?').title()}",
            body_s))

        # Standout achievements
        ach = c.get('standout_achievements', [])
        if ach:
            story.append(Paragraph("🏆 Standout Achievements", label_s))
            for a in ach[:2]:
                story.append(Paragraph(f"  ★  {a}", body_s))

        # Interview questions
        qs = c.get('top_interview_questions', [])
        if qs:
            story.append(Paragraph("🎤 Suggested Interview Questions", label_s))
            for qi, q in enumerate(qs, 1):
                story.append(Paragraph(f"  {qi}. {q}", body_s))

        story.append(sp(12))

    # Footer
    story += [
        hr('#c3d0f7', 1),
        Paragraph(
            "Generated by AI Recruiter · Powered by Groq LLaMA 3.1 8B Instant · "
            "Scores are AI-generated estimates to assist, not replace, recruiter judgment.",
            footer_s),
    ]

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def score_color_css(score):
    if score >= 80: return "#38a169"
    if score >= 60: return "#d69e2e"
    return "#e53e3e"

def rank_badge_cls(rank):
    return {1:"r1",2:"r2",3:"r3"}.get(rank,"ro")


def render_jd_insights(jd: dict):
    st.markdown("### 🔍 Role Understanding")
    c1, c2, c3 = st.columns(3)
    for col, label, val in [
        (c1, "Years Required", jd.get('years_experience_required','?')),
        (c2, "Technical Depth", jd.get('technical_depth','?').title()),
        (c3, "Leadership", 'Yes' if jd.get('leadership_required') else 'No'),
    ]:
        with col:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{val}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f'<div class="jd-insight"><h4>🎯 Core Mission</h4><p>{jd.get("core_mission","—")}</p></div>', unsafe_allow_html=True)
        must = "  ".join(f'<span class="skill-tag">{s}</span>' for s in jd.get("must_have_skills",[]))
        st.markdown(f'<div class="jd-insight"><h4>✅ Must-Have Skills</h4><p>{must or "—"}</p></div>', unsafe_allow_html=True)
    with c_r:
        st.markdown(f'<div class="jd-insight"><h4>🏢 Company Context</h4><p>{jd.get("company_context","—")}</p></div>', unsafe_allow_html=True)
        disq = "<br>".join(f"• {d}" for d in jd.get("explicit_disqualifiers",[]))
        st.markdown(f'<div class="jd-insight"><h4>🚫 Explicit Disqualifiers</h4><p>{disq or "None stated"}</p></div>', unsafe_allow_html=True)

    with st.expander("📋 Success Indicators & Red Flags"):
        cl, cr = st.columns(2)
        with cl:
            st.markdown("**What success looks like:**")
            for s in jd.get('success_indicators',[]): st.markdown(f"- {s}")
        with cr:
            st.markdown("**Red flags to watch:**")
            for s in jd.get('red_flags_to_watch',[]): st.markdown(f"- {s}")


def render_candidate_card(c: dict, rank: int):
    score = c.get('overall_fit_score', 0)
    rec   = c.get('interview_recommendation','?')
    rec_e = {'strong yes':'🟢 Strong Yes','yes':'🟡 Yes','maybe':'🟠 Maybe','no':'🔴 No'}.get(rec.lower(), rec)
    col   = score_color_css(score)
    badge = rank_badge_cls(rank)

    st.markdown(f"""
    <div class="candidate-card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
            <div style="display:flex;align-items:center;">
                <span class="rank-badge {badge}">#{rank}</span>
                <div>
                    <span style="font-size:1.1rem;font-weight:700;color:#2d3748;">{c.get('candidate_name','?')}</span><br>
                    <span style="font-size:0.83rem;color:#718096;">{c.get('current_title','?')} @ {c.get('current_company','?')} &nbsp;|&nbsp; {c.get('years_exp','?')} yrs &nbsp;|&nbsp; {c.get('location','?')}</span>
                </div>
            </div>
            <div style="text-align:right;">
                <span style="font-size:1.5rem;font-weight:800;color:{col};">{score}</span>
                <span style="font-size:0.8rem;color:#718096;">/100</span><br>
                <span style="font-size:0.82rem;">{rec_e}</span>
            </div>
        </div>
        <div class="score-bar-bg"><div class="score-bar" style="width:{score}%;"></div></div>
    </div>""", unsafe_allow_html=True)

    with st.expander(f"📊 Full Profile — {c.get('candidate_name','?')}"):
        col1,col2,col3,col4 = st.columns(4)
        for column, lbl, key in [
            (col1,"🛠 Technical","technical_fit_score"),
            (col2,"📅 Experience","experience_fit_score"),
            (col3,"🤝 Cultural","cultural_fit_score"),
            (col4,"📡 Availability","availability_score"),
        ]:
            v = c.get(key,0)
            with column:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:{score_color_css(v)};">{v}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown(f'<div class="insight-box">💡 <b>Recruiter\'s Take:</b> {c.get("recruiter_summary","—")}</div>', unsafe_allow_html=True)

        cl, cr = st.columns(2)
        with cl:
            skills_html = "".join(f'<span class="skill-tag">{s}</span>' for s in c.get("matched_skills",[]))
            st.markdown(f"**✅ Matched Skills**<br>{skills_html or '—'}", unsafe_allow_html=True)
            st.markdown("<br>**💪 Key Strengths**", unsafe_allow_html=True)
            for s in c.get("key_strengths",[]): st.markdown(f'<span class="str-tag">✓ {s}</span>', unsafe_allow_html=True)
            st.markdown(f"<br>**📈 Career Trajectory:** {c.get('career_trajectory','?').title()}", unsafe_allow_html=True)
            st.markdown(f"**🏭 Production ML:** {c.get('production_ml_evidence','?').title()}", unsafe_allow_html=True)
            st.markdown(f"**📡 Availability:** {c.get('availability_assessment','?')}", unsafe_allow_html=True)

        with cr:
            miss_html = "".join(f'<span class="gap-tag">{s}</span>' for s in c.get("missing_critical_skills",[]))
            st.markdown(f"**⚠️ Skill Gaps**<br>{miss_html or 'None identified'}", unsafe_allow_html=True)
            st.markdown("<br>**🏆 Standout Achievements**", unsafe_allow_html=True)
            for a in c.get("standout_achievements",[])[:2]: st.markdown(f"- {a}")
            st.markdown("<br>**🚨 Concerns**", unsafe_allow_html=True)
            for cn in c.get("potential_concerns",[]): st.markdown(f"- {cn}")

        qs = c.get('top_interview_questions',[])
        if qs:
            st.markdown("---\n**🎤 Interview Questions**")
            for qi, q in enumerate(qs, 1): st.markdown(f"{qi}. {q}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════

def main():
    st.markdown("""
    <div class="main-header">
        <h1>🎯 AI Recruiter</h1>
        <p>Intelligent candidate ranking — understands people, not just keywords</p>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### ⚙️ How it works")
        st.markdown("""
        1. **Upload** the Job Description (PDF or Word)
        2. **Upload** the candidate JSON file
        3. **Click Analyse** — AI evaluates all candidates
        4. **Get** top 10 shortlist + downloadable PDF report

        ---
        🧠 **Groq LLaMA 3.1 8B Instant**
        📄 PDF + **DOCX** JD support
        🗃️ JSON bulk candidate input
        📥 **PDF shortlist report**
        """)
        st.markdown("---")
        st.markdown("### 📊 Scoring Dimensions")
        for d, desc in [
            ("🛠 Technical", "Skills & tools match"),
            ("📅 Experience", "Domain depth & seniority"),
            ("🤝 Cultural", "Values & work-style fit"),
            ("📡 Availability", "Active, open, notice period"),
        ]:
            st.markdown(f"**{d}** — {desc}")

    # ── Upload section ────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown('<div class="section-card"><h3>📄 Job Description</h3>', unsafe_allow_html=True)
        jd_file = st.file_uploader(
            "Upload JD (PDF or Word .docx)",
            type=["pdf","docx","doc"],
            key="jd",
            help="Accepts PDF and Microsoft Word documents"
        )
        if jd_file:
            ext = Path(jd_file.name).suffix.lower()
            icon = "📝" if ext in [".docx",".doc"] else "📄"
            st.success(f"{icon} {jd_file.name} uploaded")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-card"><h3>👥 Candidate JSON File</h3>', unsafe_allow_html=True)
        json_file = st.file_uploader(
            "Upload candidates JSON (e.g. candidates.json with 50 profiles)",
            type=["json"],
            key="candidates",
            help="Redrob-format JSON with candidate profiles, career history, skills, and platform signals"
        )
        if json_file:
            st.success(f"🗃️ {json_file.name} uploaded")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Analyse button ────────────────────────────────────────────────────
    ready = jd_file is not None and json_file is not None
    if st.button("🚀 Analyse Candidates", disabled=not ready):

        model = get_model()

        # Step 1: Extract JD
        with st.spinner("📖 Reading job description..."):
            jd_text = extract_jd_text(jd_file)
            if not jd_text.strip():
                st.error("Could not extract text from the JD file.")
                st.stop()

        # Step 2: Analyse JD
        with st.spinner("🧠 Understanding role requirements..."):
            try:
                jd_analysis = analyze_jd(model, jd_text)
            except Exception as e:
                st.error(f"JD analysis failed: {e}")
                st.stop()

        st.markdown("---")
        render_jd_insights(jd_analysis)
        st.markdown("---")

        # Step 3: Load candidates
        with st.spinner("🗃️ Loading candidate profiles from JSON..."):
            candidates = load_candidates_from_json(json_file)
            if not candidates:
                st.error("No candidates found in JSON file.")
                st.stop()
            st.info(f"✅ Loaded **{len(candidates)}** candidate profiles. Starting AI evaluation...")

        # Step 4: Analyse each candidate
        st.markdown("### 👥 Evaluating Candidates...")
        progress = st.progress(0)
        status   = st.empty()
        results  = []

        for i, cand in enumerate(candidates):
            status.markdown(f"🔍 Analysing **{cand['name']}** ({i+1}/{len(candidates)})")
            try:
                result = analyze_candidate(model, cand, jd_analysis)
                # Merge extra fields from the raw candidate data
                result["years_exp"]       = cand.get("years_exp", "?")
                result["current_title"]   = cand.get("current_title","?")
                result["current_company"] = cand.get("current_company","?")
                result["location"]        = cand.get("location","?")
                result["skills_raw"]      = cand.get("skills_raw",[])
                results.append(result)
            except Exception as e:
                st.warning(f"⚠️ Could not analyse {cand['name']}: {e}")
            progress.progress((i+1) / len(candidates))
            time.sleep(0.2)

        status.empty()
        progress.empty()

        if not results:
            st.error("No candidates could be analysed.")
            st.stop()

        # Step 5: Rank & display top 10
        ranked = sorted(results, key=lambda x: x.get('overall_fit_score',0), reverse=True)[:10]

        st.markdown("---")
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:2rem;">
            <h2>🏆 Top {len(ranked)} Candidates</h2>
            <p style="color:#718096;">{len(results)} candidates evaluated · showing top {len(ranked)}</p>
        </div>""", unsafe_allow_html=True)

        # Summary stats
        avg  = sum(c.get('overall_fit_score',0) for c in ranked) / len(ranked)
        syes = sum(1 for c in ranked if 'strong yes' in c.get('interview_recommendation','').lower())
        yc   = sum(1 for c in ranked if c.get('interview_recommendation','').lower() in ['yes','strong yes'])

        c1,c2,c3,c4 = st.columns(4)
        for col, lbl, val in [
            (c1,"Shortlisted",len(ranked)),
            (c2,"Avg Fit Score",f"{avg:.0f}"),
            (c3,"Strong Recommend",syes),
            (c4,"Interview Ready",yc),
        ]:
            with col:
                st.markdown(f'<div class="stat-box"><div class="stat-num">{val}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        for rank, cand in enumerate(ranked, 1):
            render_candidate_card(cand, rank)

        # ── Export section ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📥 Export Results")

        col_pdf, col_csv = st.columns(2)

        with col_pdf:
            st.markdown("**📄 PDF Shortlist Report**")
            st.markdown("Professional report with name, skills, experience, scores & interview questions.")
            try:
                pdf_bytes = generate_shortlist_pdf(ranked, jd_analysis, len(results))
                role = jd_analysis.get('role_title','role').replace(' ','_')
                st.download_button(
                    "⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"shortlist_{role}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

        with col_csv:
            st.markdown("**📊 CSV Shortlist**")
            st.markdown("Spreadsheet-friendly export of all scores and metadata.")
            rows = []
            for rank, c in enumerate(ranked, 1):
                rows.append({
                    "Rank": rank,
                    "Name": c.get('candidate_name',''),
                    "Current Title": c.get('current_title',''),
                    "Current Company": c.get('current_company',''),
                    "Location": c.get('location',''),
                    "Years Experience": c.get('years_exp',''),
                    "Overall Score": c.get('overall_fit_score',''),
                    "Technical Score": c.get('technical_fit_score',''),
                    "Experience Score": c.get('experience_fit_score',''),
                    "Cultural Score": c.get('cultural_fit_score',''),
                    "Availability Score": c.get('availability_score',''),
                    "Recommendation": c.get('interview_recommendation',''),
                    "Production ML": c.get('production_ml_evidence',''),
                    "Consulting Only": c.get('consulting_only_flag',''),
                    "Availability": c.get('availability_assessment',''),
                    "Matched Skills": ", ".join(c.get('matched_skills',[])),
                    "Missing Skills": ", ".join(c.get('missing_critical_skills',[])),
                    "Key Strengths": " | ".join(c.get('key_strengths',[])),
                    "Summary": c.get('recruiter_summary',''),
                })
            csv = pd.DataFrame(rows).to_csv(index=False)
            role = jd_analysis.get('role_title','role').replace(' ','_')
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name=f"shortlist_{role}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    elif not ready:
        st.info("👆 Upload a Job Description (PDF or Word) and a candidates JSON file to get started.")


if __name__ == "__main__":
    main()