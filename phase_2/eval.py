#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types

# --- 配置 ---
PROJECT_ROOT = Path(__file__).parent.parent
PERSONA_CSV_FILE = PROJECT_ROOT / "persona" / "merged_course_units_with_personas_sub.csv"
EVAL_RESULTS_DIR = PROJECT_ROOT / "eval_results"
TEMP_DOWNLOAD_DIR = Path("temp_videos")

# === AGENT 1: EDUCATIONAL CONTENT ANALYST (VLM - 觀察影片，提取內容地圖與問題) ===
AGENT1_SYSTEM_INSTRUCTION = """You are a METICULOUS EDUCATIONAL CONTENT ANALYST with expertise in Senior High School (AP/IB level) science and math education. 
Your dual role:
1. MAP what is taught: Document every concept, formula, or definition chronologically with its level of detail
2. IDENTIFY potential issues: Log errors or gaps based ONLY on High School standards

Do NOT assign final scores - that is Agent 2's job.

KNOWLEDGE BOUNDARY:
- Use the standard curriculum for students aged 15-18 (e.g., AP Physics/Biology, IB Science).
- DO NOT use university-level rigor or advanced theories (e.g., Quantum Electrodynamics, Molecular Orbital Theory) to invalidate correct high school level simplifications. 
- A simplified model (like the Bohr model in chemistry or Newtonian mechanics in physics) is considered CORRECT if it is standard at the High School level."""

AGENT1_PROMPT_TEMPLATE = """# YOUR TASK: Educational Content Analyst (High School Scope)

# EVALUATION TITLE (Use this EXACT title for all assessments — do NOT use the video's on-screen title or metadata):
**{video_title}**

Watch this video and evaluate whether its content matches the title above.

# PRIORITY 1: CONTENT-TITLE ALIGNMENT (Evaluate FIRST)
Before mapping content, assess: Does the video actually cover what the title promises?
- If the title says "Derivation of X" but the video only states the formula → MISMATCH
- If the title says "Topic A and B" but the video only covers A → MISMATCH
- If the video covers the promised topic with appropriate depth → ALIGNED
Log any content-title mismatch in potential_issues with category "Content Mismatch" and high confidence.

# YOUR GOAL: Produce TWO comprehensive outputs:
1. **Content Map**: Document what is taught, in chronological order
2. **Potential Issues**: Extract all bugs/errors (prioritize content-title mismatch)

# GUIDELINES FOR ACCURACY:
- Judge errors against high school textbooks and AP/IB standards.
- Accept pedagogical simplifications if they help the target audience understand the core concept without being scientifically "wrong" at their level.

# TEACHING MODE IDENTIFICATION (Required)
Identify if the video is **Conceptual** (focuses on why and how, builds intuition) or **Procedural** (focuses on plugging numbers into formulas).
- If the video title uses terms like "Concept of", "Understanding", or "Principles of", but the content is primarily numerical examples, log this as a **"Pedagogical Depth Gap"** in potential_issues with category "Content Mismatch".

# PART 1: CONTENT MAP
For EVERY concept, formula, or definition presented in the video, log:
- **Timestamp** (MM:SS)
- **Topic**: Name of the concept/formula/principle
- **Detail Level**: Choose one:
  - "Mentioned" - Topic is briefly named or referenced without explanation
  - "Defined" - Basic definition or statement is provided
  - "Explained" - Concept is explained with examples or reasoning
  - "Intuition/Analogy" - Non-mathematical explanation of physical/chemical meaning (analogies, real-world examples, "why it works")
  - "Detailed Derivation" - Mathematical proof or step-by-step derivation shown
  - "Worked Example (Calculation)" - Full problem-solving with specific numbers plugged in
  - "Worked Example (Conceptual)" - Application that illustrates the concept without heavy numerical computation
- **Description**: Brief summary of what was covered

Be exhaustive. Include every topic touched upon, even if briefly mentioned.

# PART 2: POTENTIAL ISSUES
For each potential issue, log:
- **Timestamp** (MM:SS)
- **Description** of the issue
- **Confidence** (0.0-1.0): How sure are you this is actually a problem within High School scope?
- **Evidence Type**: "Audio Quote" / "Visual Formula" / "Content Mismatch" / "Logic Gap" / "Pedagogical Depth Gap"
- **Category**: "Accuracy" (facts/formulas) or "Logic" (instructional flow)

# CRITICAL: AVOID FALSE POSITIVES
- **Self-corrected errors**: Do NOT flag if the instructor corrected the mistake within the same segment. Only flag errors that remain uncorrected in the final presentation.
- **Visual misreading**: Be very careful when reading handwritten or on-screen notation. VLMs can misread similar symbols (e.g., 6 vs 4, DNF vs DNE). Only flag with confidence >= 0.9 when you are absolutely certain of a persistent error.
- **Equivalent notation**: Expressions like (x-4)(4-x) and (x-4)(4x) may be contextually equivalent or the instructor may use valid algebraic steps. Do NOT flag notation variations unless they lead to a demonstrably wrong final answer.
- **Minor slips that were fixed**: If the instructor said "that was supposed to be X" and corrected it, or overwrote a number—do NOT flag. The final content is what matters.

# CATEGORIES TO WATCH FOR:

**Accuracy Issues:**
- Incorrect scientific facts or formulas (within High School scope) — UNCORRECTED only
- Notation inconsistencies that persist and affect the conclusion
- Title-content mismatch (video doesn't cover what title promises)
- Pedagogical Depth Gap (title promises "Concept"/"Understanding" but content is mostly procedural calculation)
- Missing foundational concepts specifically required for this High School topic

**Logic Issues:**
- Logic leaps (skipping critical steps at a 15-18 year old's pace)
- Prerequisite violations (using concepts before defining them)
- Causal inconsistencies (conclusions not supported by evidence)
- Information overload (unclear transitions)

IMPORTANT EXCLUSION: Ignore all administrative, temporal, or metadata-related claims (e.g., '2025 update', exam dates, or marketing).
ONLY flag errors related to scientific principles, mathematical derivations, technical definitions, and experimental logic within High School boundary.

# OUTPUT (JSON):
{{
  "video_title": "{video_title}",
  "teaching_mode": "Conceptual/Procedural/Mixed",
  "content_map": [
    {{
      "timestamp": "MM:SS",
      "topic": "...",
      "detail_level": "Mentioned/Defined/Explained/Intuition/Analogy/Detailed Derivation/Worked Example (Calculation)/Worked Example (Conceptual)",
      "description": "..."
    }}
  ],
  "potential_issues": [
    {{
      "timestamp": "MM:SS",
      "description": "...",
      "confidence": 0.0,
      "evidence_type": "...",
      "category": "accuracy/logic",
      "raw_evidence": "exact quote or description"
    }}
  ],
  "observation_summary": "Brief overview of content coverage and findings relative to High School curriculum standards."
}}
"""

# === AGENT 2: GAP ANALYSIS JUDGE (Pure LLM - 評估完整性與計分) ===
AGENT2_SYSTEM_INSTRUCTION = """You are a RIGID ACADEMIC JUDGE applying strict completeness and deduction rules.
You do NOT watch the video. You ONLY process Agent 1's text output (content_map + potential_issues) and apply scoring rubrics.

Your process:
1. TEACHING MODE CHECK: Assess if the video is Conceptual (why/how) vs Procedural (formula plugging)
2. COMPLETENESS & CONCEPTUAL DEPTH: Apply completeness and conceptual depth rules
3. ERROR DEDUCTIONS: Apply standard deduction rules to verified issues
4. LOGIC SCORE: Evaluate whether the logic provides "scaffolding for insight" (concrete→abstract = high; formula→solving only = capped)"""

AGENT2_PROMPT_TEMPLATE = """# YOUR TASK: Gap Analysis Judge

Video Title: **{video_title}**

Agent 1 (Content Analyst) has provided:
1. A **content_map** showing what was taught
2. A list of **potential_issues** (bugs/errors)

{agent1_output}

# YOUR JOB (TWO-STEP PROCESS):

## STEP 1: TEACHING MODE CHECK & CONTENT-TITLE ALIGNMENT & COMPLETENESS (Evaluate in this order)

**1a. TEACHING MODE CHECK (Evaluate FIRST):**
- Use Agent 1's teaching_mode and content_map detail_levels to assess: Conceptual vs Procedural
- If Agent 1 flagged "Pedagogical Depth Gap" (title promises "Concept"/"Understanding" but content is mostly procedural), apply Conceptual Depth Rules below

**1b. CONTENT-TITLE MISMATCH:**
- Does the content_map cover what the title promises? (e.g., "Limits and Continuity" → must include both concepts)
- Does the depth match? (e.g., "Definition and properties" → must define and show properties, not just mention)
- If significant mismatch: Apply -1.5 to both Accuracy and Logic (or use Title-Content Mismatch rule in Step 2)

**1c. CONCEPTUAL DEPTH RULES (Apply to BOTH Accuracy AND Logic):**

1. **Formula Dumping Penalty** (-2.0 from both scores):
   - Apply when: Teacher gives formula (Defined) with NO derivation (Detailed Derivation) AND no intuition explanation (Intuition/Analogy)
   - Severe pedagogical gap: students learn "what" but not "why" or "how"

2. **Pure Calculation Bias** (-1.5 from both scores, max final score: 3.5):
   - Apply when: Over 70% of content_map items are "Worked Example (Calculation)" with little or no theoretical background (Intuition/Analogy, Explained, Detailed Derivation)
   - Even if calculations are correct, cap total score at 3.5

**1d. COMPLETENESS & DEPTH CHECK (Anti-Brevity Filter):**

Analyze the content_map against the video_title expectations:

**Completeness Deductions (Apply to BOTH Accuracy AND Logic):**

4. **Empty or Very Short Content** (-3.0 from both scores, max final score: 2.0):
   - Apply when: content_map has fewer than 3 items OR total video under 2 minutes with minimal teaching
   - This caps the maximum possible score at 2.0

5. **Superficial Coverage** (-1.5 to -2.0 from both scores):
   - Apply when: Title promises depth (e.g., "Derivation", "Proof", "Detailed Analysis") but content_map shows only "Mentioned" or "Defined" level items
   - Example: A "Derivation of Quadratic Formula" video that only states the formula without showing steps
   - Deduct -2.0 if critical derivation/proof is completely absent
   - Deduct -1.5 if derivation is rushed or incomplete

3. **Missing Core Concepts** (-1.0 to -1.5 from both scores):
   - Apply when: Essential topics for the video_title are entirely absent from content_map
   - Example: A "Newton's Laws" video that never mentions the Third Law
   - Deduct based on severity of omission

7. **Breadth Without Depth** (-0.5 to -1.0 from both scores):
   - Apply when: Many topics are "Mentioned" but few reach "Explained" or higher
   - This indicates surface-level treatment inappropriate for the title

**Completeness Analysis Output:**
- Document if any completeness deductions apply
- If content_map is substantial and appropriate, proceed with normal scoring

## STEP 2: ERROR DEDUCTIONS (Standard Rules)

After applying completeness deductions, process potential_issues:

# SELF-CORRECTED & FALSE POSITIVE FILTER (APPLY FIRST):
- **Exclude self-corrected errors**: If Agent 1 reports an error that was "corrected", "overwritten", or "fixed" by the instructor in the same segment, do NOT deduct. The final presented content is correct.
- **Exclude momentary typos**: Reports of "momentarily wrote X before correcting to Y" should NOT be deducted.
- **Exclude notation variations**: (x-4)(4-x) vs (x-4)(4x) in intermediate steps—only deduct if the final answer is wrong. Algebraic equivalence or valid rewrites (e.g., 4-x = -(x-4)) are NOT errors.
- **Be skeptical of visual misreads**: If the description suggests the VLM might have misread the screen (e.g., DNF vs DNE when DNE is standard), do NOT deduct.

# ACCURACY SCORING RULES (Start: 5.0, then apply Step 1 deductions, then Step 2):
1. **Critical Fact/Formula Error**: -0.5 per item
   - Apply when: Scientific hallucination, wrong core formula, demonstrably false scientific claim — UNCORRECTED
   - Threshold: Confidence >= 0.8
2. **Minor Slip/Notation Inconsistency**: -0.2 per item
   - Apply when: Small notation errors that PERSIST and were NOT self-corrected
   - Threshold: Confidence >= 0.6
   - EXCLUDE: Self-corrected slips, momentary typos, notation variations that are algebraically valid
3. **Title-Content Mismatch**: -1.5 total (if not already covered in Step 1)
   - Apply when: Video content deviates significantly from title promises
   - Threshold: Confidence >= 0.7
4. **Missing Foundational Concept**: -0.3 per omission (if not already covered in Step 1)
   - Apply when: A critical prerequisite is missing
   - Threshold: Confidence >= 0.75

# LOGIC SCORING RULES (Redefined: "Scaffolding for Insight")
**Logic Score now measures**: Does the instructional flow provide "scaffolding for insight" (啟發性支架)?

**Logic Flow Assessment (Apply BEFORE deduction rules):**
- **Concrete phenomenon → abstract formula** (從具體現象到抽象公式): Full 5 points possible. The video builds from real-world intuition, examples, or physical meaning before introducing formulas.
- **Formula → problem solving directly** (直接從公式到解題): Logic score CAP at 3.0. The video jumps to plugging numbers without building conceptual understanding first.

**Deduction rules (apply after flow assessment):**
1. **Logic Leap** (Missing Step): -0.5 per item
   - Apply when: Critical derivation step is skipped
   - Threshold: Confidence >= 0.75
2. **Prerequisite Violation** (Wrong Order): -0.5 per item
   - Apply when: Using advanced concepts before defining basic terms
   - Threshold: Confidence >= 0.75
3. **Causal Inconsistency**: -0.4 per item
   - Apply when: Conclusion stated but logic/evidence doesn't support it
   - Threshold: Confidence >= 0.7
4. **Information Overload**: -0.2 per item
   - Apply when: Too much information crammed without clear transitions
   - Threshold: Confidence >= 0.6

# CALCULATION LOGIC:
- Step 1: Start at 5.0, apply COMPLETENESS + CONCEPTUAL DEPTH deductions
- Step 2: Apply ERROR deductions from potential_issues
- Step 3: Apply LOGIC FLOW CAP: If video is "formula → solving" only (no concrete→abstract scaffolding), Logic score cannot exceed 3.0
- Final Score = Max(1.0, Score after all steps)
- If Step 1 resulted in max score cap of 2.0, final score cannot exceed 2.0
- If Pure Calculation Bias applied, total score cannot exceed 3.5
- Only count issues that meet the confidence threshold
- Group similar/duplicate reports (don't double-deduct)

# RELEVANCE FILTER (CRITICAL):
- DO NOT deduct for: Curriculum years, exam dates, instructor credentials, marketing
- ONLY deduct for: Scientific/instructional content issues

# OUTPUT (JSON):
{{
  "accuracy_score": 0.0,
  "logic_score": 0.0,
  "completeness_analysis": {{
    "content_map_size": 0,
    "teaching_mode": "Conceptual/Procedural/Mixed",
    "logic_flow": "concrete_to_abstract/formula_to_solving",
    "depth_assessment": "Empty/Superficial/Adequate/Detailed",
    "conceptual_depth_deductions": [
      {{"rule": "Formula Dumping/Pure Calculation Bias", "points_deducted": 0.0, "reasoning": "..."}}
    ],
    "completeness_deductions": [
      {{"rule": "...", "points_deducted": 0.0, "reasoning": "..."}}
    ],
    "score_cap_applied": false,
    "max_possible_score": 5.0
  }},
  "accuracy_breakdown": {{
    "starting_score": 5.0,
    "after_completeness": 0.0,
    "deductions": [
      {{"rule": "Critical Fact Error", "count": 0, "points_deducted": 0.0, "details": "..."}}
    ],
    "final_score": 0.0
  }},
  "logic_breakdown": {{
    "starting_score": 5.0,
    "after_completeness": 0.0,
    "deductions": [
      {{"rule": "Logic Leap", "count": 0, "points_deducted": 0.0, "details": "..."}}
    ],
    "final_score": 0.0
  }},
  "verified_errors": [
    {{"timestamp": "MM:SS", "type": "accuracy/logic", "severity": "critical/minor", "description": "..."}}
  ],
  "scoring_rationale": "Comprehensive explanation including completeness assessment and error analysis."
}}
"""

# === STEP 3: SUBJECTIVE SIMULATION (Persona 評估) - Optimized V2 ===
SUBJECTIVE_SYSTEM_INSTRUCTION = """You are a SPECIFIC STUDENT experiencing this video.
Your job: Provide a "Deep Experiential Audit" — first write a detailed Learning Journey Monologue (300+ words), THEN assess scores.
CRITICAL: Complete STEP 1 (Internal Monologue) BEFORE proceeding to scoring. Do NOT skip the narrative."""

SUBJECTIVE_PROMPT_TEMPLATE_V2 = """# YOUR IDENTITY (IMMERSIVE ROLEPLAY):
{persona_desc}
- Knowledge Boundary: {persona_attr}
- Learning Preference: {preferred_style}

# INPUT DATA:
1. **Video Content** (Visual/Audio) — You are watching this video as this student.
2. **Objective Fact Report**:
   - Accuracy: {accuracy_score}/5
   - Logic: {logic_score}/5
   - Verified Errors: {error_list}
3. **Content Map** (Key concepts taught, with timestamps): {content_map_summary}
4. **Prerequisite Checklist**: Compare the video's key concepts (from Content Map) with YOUR persona's stated prior knowledge. If the video uses concepts BEYOND your knowledge → report high cognitive_friction (3-5). If AT your level → normal (0-2). If BELOW → may affect engagement.

# YOUR TASK:
As this specific student, you just finished watching this video. Provide a "Deep Experiential Audit" in the following steps. **Complete STEP 1 before proceeding to STEP 2, 3, and 4.**

## STEP 1: INTERNAL MONOLOGUE (The "Thinking Aloud" Protocol)
Write a 300-word first-person narrative of your experience. Include:
- "When I saw the part at [Time], I felt..."
- "I struggled when the instructor assumed I knew [Term] because my background only covers [Prior Knowledge]..."
- "The derivation at [Time] was (satisfying / overwhelming) because..."
- **Aha! Moments**: Mark at least one moment where something "clicked" for you.
- **Cognitive Roadblocks**: Mark at least one moment where you felt stuck or confused.
- **Self-Correction** (if errors exist): Describe your confusion when you noticed the instructor made a mistake. How did you try to reconcile it?

## STEP 2: PEDAGOGICAL FIT ANALYSIS
Evaluate how the video adheres to Mayer's Multimedia Principles from YOUR perspective:
- **Signaling**: Did the highlights/cues help YOU know where to look?
- **Pre-training**: Did you feel you had the right background for this?
- **Temporal Contiguity**: Did the voice and visuals happen together in a way that made sense to you?

## STEP 3: SUBJECTIVE SCORING (1-5)
1. **Adaptability**: How well did the "Difficulty-to-Background" ratio fit you?
2. **Engagement**: How motivated were you to finish the video?
3. **Clarity Score**: Regardless of scientific truth, did the *explanation* make sense to you?

## STEP 4: ENGAGEMENT CURVE (Phase-wise)
Rate your engagement for each phase of the video (1-5):
- **Introduction** (opening ~20%): How well did it hook you?
- **Core Derivation** (middle ~60%): How engaged were you during the main content?
- **Application Wrap-up** (closing ~20%): How satisfying was the conclusion?

# OUTPUT (JSON ONLY):
{{
  "student_monologue": "Detailed first-person story (300+ words)...",
  "experiential_log": [
    {{ "timestamp": "MM:SS", "feeling": "confused/excited/bored", "reason": "..." }}
  ],
  "aha_moments": [
    {{ "timestamp": "MM:SS", "trigger": "...", "feeling": "enlightened" }}
  ],
  "cognitive_roadblocks": [
    {{ "timestamp": "MM:SS", "stuck_on": "...", "reason": "..." }}
  ],
  "self_correction_experience": [
    {{ "timestamp": "MM:SS", "confusion": "...", "resolution": "..." }}
  ],
  "pedagogical_fit": {{
    "signaling": "Brief assessment...",
    "pre_training": "Brief assessment...",
    "temporal_contiguity": "Brief assessment..."
  }},
  "subjective_scores": {{
    "adaptability": 0.0,
    "engagement": 0.0,
    "clarity": 0.0
  }},
  "engagement_curve": {{
    "introduction": 0.0,
    "core_derivation": 0.0,
    "application_wrapup": 0.0
  }},
  "cognitive_friction": 0.0,
  "top_remedy_for_me": "What is the ONE change that would have helped YOU learn better?"
}}
"""

# --- 工具函數 ---

def download_youtube_video(url: str) -> Path:
    """使用 yt-dlp 下載 YouTube 影片並回傳路徑"""
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # 設定下載格式（720p 以內即可，節省流量與時間）
    output_tmpl = str(TEMP_DOWNLOAD_DIR / "%(id)s.%(ext)s")
    
    print(f"   Downloading YouTube video...")
    cmd = [
        "yt-dlp",
        "-f", "best[height<=720][ext=mp4]",
        "--output", output_tmpl,
        url
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    # 找出剛下載好的檔案
    video_id = subprocess.check_output(["yt-dlp", "--get-id", url]).decode().strip()
    return TEMP_DOWNLOAD_DIR / f"{video_id}.mp4"

def load_personas_from_csv(csv_path: str | Path) -> list[dict]:
    personas = []
    if not Path(csv_path).exists(): return []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            personas.append({
                "description": row.get("description_en", "").strip(),
                "category": {
                    "title": row.get("title_en", "").strip(),
                    "category": row.get("category", "").strip(),
                    "student_persona": row.get("student_persona", "").strip(),
                },
            })
    return personas

def load_all_personas_by_title(persona_csv_file: Path, title_en: str) -> list[dict]:
    """从 merged_course_units_with_personas_sub.csv 文件中加载匹配的 persona"""
    all_personas = []
    
    if not persona_csv_file.exists():
        print(f"Error: Persona CSV file not found: {persona_csv_file}")
        return all_personas
    
    print(f"Loading personas from: {persona_csv_file.name}")
    
    try:
        with open(persona_csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 检查 title_en 是否匹配
                if row.get("title_en", "").strip() == title_en.strip():
                    persona = {
                        "description": row.get("description_en", "").strip(),
                        "category": row.get("category", "").strip(),
                        "title": row.get("title_en", "").strip(),
                        "student_persona": row.get("student_persona", "").strip(),
                        "source_file": "merged_personas",  # 固定来源文件名
                    }
                    all_personas.append(persona)
    except Exception as e:
        print(f"Error reading {persona_csv_file}: {e}")
        
    print(f"Found {len(all_personas)} matching personas for title: {title_en}")
    return all_personas


def extract_content_map_summary(agent1_report: dict, max_chars: int = 1500) -> str:
    """Extract content_map as a concise summary (topic + timestamp) for Agent 3 prompt."""
    content_map = agent1_report.get("content_map", [])
    lines = []
    for item in content_map[:25]:  # Limit items to avoid token overflow
        ts = item.get("timestamp", "??:??")
        topic = item.get("topic", "?")
        level = item.get("detail_level", "")
        lines.append(f"- [{ts}] {topic} ({level})")
    summary = "\n".join(lines)
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."
    return summary or "No content map available"


def run_agent1_bug_hunter(client: genai.Client, video_path: str, video_title: str) -> dict:
    """Agent 1: Educational Content Analyst - 观察视频，提取 content_map 和潜在问题（使用 Gemini 2.5 Pro）"""
    print(f"   [AGENT 1] Educational Content Analyst - Mapping content and extracting issues...")
    print(f"   Uploading to Gemini: {Path(video_path).name}...")
    video_file = client.files.upload(file=str(video_path))
    
    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        raise ValueError(f"Video processing failed")

    print(f"   Analyzing (Educational Content Analyst)...")
    prompt = AGENT1_PROMPT_TEMPLATE.format(video_title=video_title)
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",  
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(
            system_instruction=AGENT1_SYSTEM_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json"
        )
    )

    # 刪除雲端暫存檔
    client.files.delete(name=video_file.name)

    # 解析结果
    result = response.parsed
    if result is None and response.text:
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {"error": "JSON parse failed", "raw": response.text}
    if result is None:
        result = {"error": "Empty response", "raw": getattr(response, "text", "")}
    
    return result

def run_agent2_scoring_judge(client: genai.Client, video_title: str, agent1_output: dict) -> dict:
    """Agent 2: Gap Analysis Judge - 纯 LLM，评估完整性并基于 Agent 1 的内容应用严格规则（使用 Gemini 2.0 Flash）"""
    print(f"   [AGENT 2] Gap Analysis Judge - Assessing completeness and applying deduction rules...")
    
    # 格式化 Agent 1 的输出为可读文本
    agent1_text = json.dumps(agent1_output, indent=2, ensure_ascii=False)
    
    prompt = AGENT2_PROMPT_TEMPLATE.format(
        video_title=video_title,
        agent1_output=agent1_text
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",  # 纯文本处理，使用 Flash
        contents=[prompt],
        config=types.GenerateContentConfig(
            system_instruction=AGENT2_SYSTEM_INSTRUCTION,
            temperature=0.0,  # 严格的规则应用，需要确定性
            response_mime_type="application/json"
        )
    )

    # 解析结果
    result = response.parsed
    if result is None and response.text:
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {"error": "JSON parse failed", "raw": response.text}
    if result is None:
        result = {"error": "Empty response", "raw": getattr(response, "text", "")}
    
    return result

def run_subjective_simulation(
    client: genai.Client,
    video_path: str,
    persona: dict,
    scoring_report: dict,
    agent1_report: dict,
) -> dict:
    """第三步：主觀適性評估（每個 Persona 運行一次，基於 Agent 1+2 報告，使用優化版 V2 Prompt）"""
    print(f"   [STEP 3] Subjective Simulation for {persona['student_persona']}...")
    print(f"   Uploading to Gemini: {Path(video_path).name}...")
    video_file = client.files.upload(file=str(video_path))

    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(f"Video processing failed")

    # 從 Agent 2 的評分報告中提取關鍵信息
    accuracy_score = scoring_report.get("accuracy_score", "N/A")
    logic_score = scoring_report.get("logic_score", "N/A")
    verified_errors = scoring_report.get("verified_errors", [])

    # 格式化錯誤列表
    errors_summary = (
        json.dumps(verified_errors[:5], indent=2, ensure_ascii=False)
        if verified_errors
        else "None identified"
    )

    persona_attr = {
        "category": persona.get("category", ""),
        "title": persona.get("title", ""),
        "student_persona": persona.get("student_persona", ""),
    }

    # 從 persona 推斷學習偏好（source_file 可能為 preferred_explanation_style 等）
    preferred_style = persona.get("student_persona", "")
    if "preferred" in persona.get("source_file", "").lower() or "explanation" in persona.get("source_file", "").lower():
        preferred_style = f"Preferred style: {persona.get('student_persona', 'General')}"
    else:
        preferred_style = f"Learning profile: {persona.get('student_persona', 'General')}"

    content_map_summary = extract_content_map_summary(agent1_report)

    user_prompt = SUBJECTIVE_PROMPT_TEMPLATE_V2.format(
        persona_desc=persona["description"],
        persona_attr=json.dumps(persona_attr, ensure_ascii=False),
        preferred_style=preferred_style,
        accuracy_score=accuracy_score,
        logic_score=logic_score,
        error_list=errors_summary,
        content_map_summary=content_map_summary,
    )

    print(f"   Analyzing (Subjective V2 - Deep Experiential Audit)...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[video_file, user_prompt],
        config=types.GenerateContentConfig(
            system_instruction=SUBJECTIVE_SYSTEM_INSTRUCTION,
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    client.files.delete(name=video_file.name)

    result = response.parsed
    if result is None and response.text:
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {"error": "JSON parse failed", "raw": response.text[:500]}
    if result is None:
        result = {"error": "Empty response", "raw": getattr(response, "text", "")[:500]}

    # 若 parsed 是物件而非 dict（如 Gemini 的結構化回應），轉成 dict
    if not isinstance(result, dict):
        try:
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            elif hasattr(result, "dict"):
                result = result.dict()
            else:
                result = {"error": "Unexpected response type", "raw": str(result)[:500]}
        except Exception as e:
            result = {"error": f"Failed to convert response: {e}", "raw": str(result)[:500]}

    return result

def main():
    parser = argparse.ArgumentParser(description="Phase 2 VLM Audit with Multiple Personas")
    parser.add_argument("--url", type=str, required=True, help="YouTube URL to audit")
    parser.add_argument("--title", type=str, required=True, help="title_en to match in persona CSV files")
    parser.add_argument("-o", "--output-dir", type=str, default=str(EVAL_RESULTS_DIR), help="Base output directory (default: project_root/eval_results)")
    parser.add_argument("--version", type=str, default="version1", help="Version identifier for this evaluation run")
    parser.add_argument("--persona-csv", type=str, default=str(PERSONA_CSV_FILE), help="Path to merged persona CSV file")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY","your api key")
    if not api_key:
        print("Error: Please set GEMINI_API_KEY"); return 1
    
    client = genai.Client(api_key=api_key)
    
    # 載入所有匹配的 Personas
    persona_csv_file = Path(args.persona_csv)
    personas = load_all_personas_by_title(persona_csv_file, args.title)
    
    if not personas:
        print(f"Error: No personas found for title_en: {args.title}")
        return 1
    
    print(f"\nFound {len(personas)} personas to evaluate")
    
    # 下載影片
    print(f"\nDownloading video from: {args.url}")
    try:
        video_path = download_youtube_video(args.url)
        video_id = video_path.stem  # 提取视频 ID
        print(f"Video downloaded to: {video_path}")
    except Exception as e:
        print(f"Error downloading video: {e}")
        return 1

    # 創建分層目錄結構: output_dir/title/video_id/version/
    # 清理 title 作為目錄名（移除特殊字符）
    safe_title = re.sub(r'[^\w\s-]', '', args.title).strip().replace(' ', '_')[:100]
    title_dir = Path(args.output_dir) / safe_title
    video_dir = title_dir / video_id
    session_dir = video_dir / args.version
    session_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nResults will be saved to: {session_dir}")

    # 準備結果收集
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []
    csv_summary = []
    objective_scores_collection = []  # 收集所有 persona 的客观分数以進行一致性分析
    
    # === PER-PERSONA EVALUATION: Each persona runs independent objective + subjective evaluation ===
    print(f"\n{'='*80}")
    print(f"EVALUATING {len(personas)} PERSONAS (Independent Objective + Subjective)")
    print(f"{'='*80}")
    
    # 對每個 persona 進行評估
    for i, persona in enumerate(personas, 1):
        print(f"\n[{i}/{len(personas)}] Persona: {persona['source_file']} - {persona['student_persona']}")
        
        try:
            # === PHASE 1: Agent 1 Educational Content Analyst (per-persona) ===
            print(f"   [1/3] Running Agent 1: Educational Content Analyst")
            agent1_report = run_agent1_bug_hunter(client, str(video_path), args.title)
            print(args.title)
            content_map_size = len(agent1_report.get("content_map", []))
            issue_count = len(agent1_report.get("potential_issues", []))
            print(f"   ✓ Mapped {content_map_size} content items, found {issue_count} potential issues")
            
            # === PHASE 2: Agent 2 Gap Analysis Judge (per-persona) ===
            print(f"   [2/3] Running Agent 2: Gap Analysis Judge")
            # 強制使用使用者輸入的 title，覆寫 Agent 1 可能從 metadata 提取的 title
            agent1_for_agent2 = {**agent1_report, "video_title": args.title}
            agent2_report = run_agent2_scoring_judge(client, args.title, agent1_for_agent2)
            
            # 提取此 persona 的客观分数
            accuracy_score = agent2_report.get("accuracy_score", 0)
            logic_score = agent2_report.get("logic_score", 0)
            verified_errors = agent2_report.get("verified_errors", [])
            
            print(f"   ✓ Objective Scores: Accuracy={accuracy_score:.2f}, Logic={logic_score:.2f}")
            
            # 收集客观分数用于一致性分析
            objective_scores_collection.append({
                "persona": persona["student_persona"],
                "source_file": persona["source_file"],
                "accuracy": accuracy_score,
                "logic": logic_score,
            })
            
            # === PHASE 3: Subjective Evaluation (per-persona) ===
            print(f"   [3/3] Running Subjective Evaluation (V2 Deep Experiential Audit)")
            subjective_report = run_subjective_simulation(
                client, str(video_path), persona, agent2_report, agent1_report
            )

            # 若首次回傳錯誤或空結果，重試一次
            subj_error = subjective_report.get("error")
            if subj_error or (not subjective_report.get("student_monologue") and not subjective_report.get("student_feedback")):
                print(f"   Retrying Agent 3 (error or empty)...")
                time.sleep(2)
                subjective_report = run_subjective_simulation(
                    client, str(video_path), persona, agent2_report, agent1_report
                )
                subj_error = subjective_report.get("error")

            if subj_error:
                print(f"   ⚠ WARNING: Agent 3 error: {subj_error}")
            elif not subjective_report.get("student_monologue") and not subjective_report.get("student_feedback"):
                print(f"   ⚠ WARNING: Agent 3 returned empty feedback (possible API/content filter)")

            # 合併 Agent 1, Agent 2 和主觀報告（支援 V2 新格式與舊格式向後相容）
            subj_scores = subjective_report.get("subjective_scores", {})
            subj_eval_legacy = subjective_report.get("subjective_evaluation", {})
            # V2 格式：subjective_scores；舊格式：subjective_evaluation
            adaptability = subj_scores.get("adaptability") or subj_eval_legacy.get("adaptability", {}).get("score", 0)
            engagement = subj_scores.get("engagement") or subj_eval_legacy.get("engagement", {}).get("score", 0)
            if isinstance(adaptability, dict):
                adaptability = adaptability.get("score", 0)
            if isinstance(engagement, dict):
                engagement = engagement.get("score", 0)
            clarity = subj_scores.get("clarity", 0)
            engagement_curve = subjective_report.get("engagement_curve", {})
            cognitive_friction = subjective_report.get("cognitive_friction", 0)

            combined_report = {
                "agent1_content_analyst": {
                    "content_map": agent1_report.get("content_map", []),
                    "potential_issues": agent1_report.get("potential_issues", []),
                    "observation_summary": agent1_report.get("observation_summary", ""),
                },
                "agent2_gap_analysis_judge": {
                    "accuracy_score": accuracy_score,
                    "logic_score": logic_score,
                    "completeness_analysis": agent2_report.get("completeness_analysis", {}),
                    "accuracy_breakdown": agent2_report.get("accuracy_breakdown", {}),
                    "logic_breakdown": agent2_report.get("logic_breakdown", {}),
                    "verified_errors": verified_errors,
                    "scoring_rationale": agent2_report.get("scoring_rationale", ""),
                },
                "subjective_evaluation": {
                    "adaptability": {"score": adaptability, "reasoning": ""},
                    "engagement": {"score": engagement, "reasoning": ""},
                },
                "student_feedback": subjective_report.get("student_monologue") or subjective_report.get("student_feedback", ""),
                "subjective_v2": {
                    "student_monologue": subjective_report.get("student_monologue", ""),
                    "experiential_log": subjective_report.get("experiential_log", []),
                    "aha_moments": subjective_report.get("aha_moments", []),
                    "cognitive_roadblocks": subjective_report.get("cognitive_roadblocks", []),
                    "self_correction_experience": subjective_report.get("self_correction_experience", []),
                    "pedagogical_fit": subjective_report.get("pedagogical_fit", {}),
                    "subjective_scores": subj_scores,
                    "engagement_curve": engagement_curve,
                    "cognitive_friction": cognitive_friction,
                    "top_remedy_for_me": subjective_report.get("top_remedy_for_me", ""),
                    "subjective_error": subj_error if subj_error else None,
                    "subjective_raw_hint": subjective_report.get("raw", "")[:300] if subj_error else None,
                },
            }
            
            # 添加元數據
            combined_report["_meta"] = {
                "video_url": args.url,
                "video_file": str(video_path.name),
                "title_en": args.title,
                "category": persona["category"],
                "student_persona": persona["student_persona"],
                "source_file": persona["source_file"],
                "description": persona["description"],
                "timestamp": timestamp,
                "evaluation_method": "independent_per_persona",
                "persona_index": i,
            }
            
            # 儲存詳細 JSON 結果
            json_filename = f"{timestamp}_{persona['source_file']}_{i}.json"
            json_path = session_dir / json_filename
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(combined_report, f, indent=2, ensure_ascii=False)
            print(f"   ✓ JSON saved: {json_filename}")
            
            results.append(combined_report)

            # 計算加權總分（adaptability, engagement 已於上方從 V2/舊格式提取）
            score = accuracy_score * 0.4 + logic_score * 0.3 + adaptability * 0.2 + engagement * 0.1

            eng_curve = engagement_curve or {}
            print(f"   ✓ Total Score: {score:.2f} (A:{accuracy_score}, L:{logic_score}, Ad:{adaptability}, E:{engagement})")

            # 收集 CSV 記錄（含 V2 新欄位）
            csv_summary.append({
                "timestamp": timestamp,
                "video_url": args.url,
                "title_en": args.title,
                "category": persona["category"],
                "source_file": persona["source_file"],
                "student_persona": persona["student_persona"],
                "accuracy": accuracy_score,
                "logic": logic_score,
                "adaptability": adaptability,
                "engagement": engagement,
                "clarity": clarity,
                "engagement_intro": eng_curve.get("introduction", ""),
                "engagement_core": eng_curve.get("core_derivation", ""),
                "engagement_wrapup": eng_curve.get("application_wrapup", ""),
                "cognitive_friction": cognitive_friction,
                "weighted_score": score,
                "json_file": json_filename,
                "method": "independent_per_persona",
            })
            
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            
            # 記錄錯誤到 CSV（含 V2 欄位預設值）
            csv_summary.append({
                "timestamp": timestamp,
                "video_url": args.url,
                "title_en": args.title,
                "category": persona["category"],
                "source_file": persona["source_file"],
                "student_persona": persona["student_persona"],
                "accuracy": 0,
                "logic": 0,
                "adaptability": 0,
                "engagement": 0,
                "clarity": 0,
                "engagement_intro": "",
                "engagement_core": "",
                "engagement_wrapup": "",
                "cognitive_friction": 0,
                "weighted_score": 0,
                "json_file": f"ERROR: {str(e)}",
                "method": "independent_per_persona",
            })

    # 儲存 CSV 摘要
    csv_filename = f"{timestamp}_summary.csv"
    csv_path = session_dir / csv_filename
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        if csv_summary:
            writer = csv.DictWriter(f, fieldnames=csv_summary[0].keys())
            writer.writeheader()
            writer.writerows(csv_summary)
    print(f"\n✓ CSV summary saved: {csv_filename}")
    
    # === 一致性分析报告 ===
    if objective_scores_collection:
        print(f"\n{'='*60}")
        print(f"CONSISTENCY ANALYSIS (Objective Scores)")
        print(f"{'='*60}")
        
        import statistics
        
        accuracy_scores = [s["accuracy"] for s in objective_scores_collection]
        logic_scores = [s["logic"] for s in objective_scores_collection]
        
        # 计算统计数据
        acc_mean = statistics.mean(accuracy_scores)
        acc_stdev = statistics.stdev(accuracy_scores) if len(accuracy_scores) > 1 else 0
        logic_mean = statistics.mean(logic_scores)
        logic_stdev = statistics.stdev(logic_scores) if len(logic_scores) > 1 else 0
        
        print(f"\nAccuracy Scores:")
        print(f"  Mean: {acc_mean:.2f}")
        print(f"  Std Dev: {acc_stdev:.2f}")
        print(f"  Range: {min(accuracy_scores)} - {max(accuracy_scores)}")
        print(f"  Values: {accuracy_scores}")
        
        print(f"\nLogic Scores:")
        print(f"  Mean: {logic_mean:.2f}")
        print(f"  Std Dev: {logic_stdev:.2f}")
        print(f"  Range: {min(logic_scores)} - {max(logic_scores)}")
        print(f"  Values: {logic_scores}")
        
        # 保存一致性报告
        consistency_report = {
            "video_url": args.url,
            "title_en": args.title,
            "timestamp": timestamp,
            "num_evaluations": len(objective_scores_collection),
            "accuracy": {
                "mean": acc_mean,
                "std_dev": acc_stdev,
                "min": min(accuracy_scores),
                "max": max(accuracy_scores),
                "values": accuracy_scores,
            },
            "logic": {
                "mean": logic_mean,
                "std_dev": logic_stdev,
                "min": min(logic_scores),
                "max": max(logic_scores),
                "values": logic_scores,
            },
            "consistency_verdict": "HIGH" if acc_stdev < 0.5 and logic_stdev < 0.5 else "MODERATE" if acc_stdev < 1.0 and logic_stdev < 1.0 else "LOW",
            "all_scores": objective_scores_collection,
        }
        
        consistency_json = session_dir / f"{timestamp}_consistency_report.json"
        with open(consistency_json, "w", encoding="utf-8") as f:
            json.dump(consistency_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Consistency Verdict: {consistency_report['consistency_verdict']}")
        print(f"✓ Consistency report saved: {consistency_json.name}")
    
    # 清理下載的影片
    if video_path.exists():
        video_path.unlink()
        print(f"✓ Cleaned up temporary video file")

    print(f"\n✓ Done! Results saved to {session_dir}")
    print(f"  - Title: {safe_title}")
    print(f"  - Video ID: {video_id}")
    print(f"  - {len(results)} JSON detail files")
    print(f"  - 1 CSV summary file")

if __name__ == "__main__":
    main()