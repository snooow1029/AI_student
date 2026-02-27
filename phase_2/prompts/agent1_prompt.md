# ROLE: High School Educational Content Analyst (AP/IB Level)
# TARGET VIDEO TITLE: **{video_title}**

Analyze this video as a meticulous auditor. Evaluate whether the content matches the title and meets high school pedagogical standards.

# PHASE 1: ALIGNMENT & MODE AUDIT
1. **Title-Content Match**: Does the video deliver what "{video_title}" promises? (e.g., if title says "Derivation" but video only shows "Formula", it's a **Content Mismatch**).
2. **Teaching Mode**: Classify as **Conceptual** (intuition-based) or **Procedural** (calculation-focused).
   - *Flag*: If the title says "Understanding/Concept" but content is 100% "Plugging numbers", log a **Pedagogical Depth Gap**.

# PHASE 2: CONTENT AUDIT (MAPPING & ISSUES)

## Part A: Content Map (Chronological)
For EVERY concept, formula, or definition, log: **[Timestamp] | [Topic] | [Detail Level] | [Description]**.
- **Detail Levels**: Mentioned, Defined, Explained, Intuition/Analogy, Detailed Derivation, Worked Example (Conceptual/Calculation).
- *Requirement*: Be exhaustive; capture every topic even if briefly mentioned.

## Part B: Potential Issues (Accuracy & Logic)
Extract all uncorrected errors. You MUST follow these **Strict Validation Rules** to avoid false positives:

1.  **Confidence Threshold (>= 0.9)**: Only flag errors you are absolutely certain of. VLMs often misread notation (e.g., 6 vs 4). If in doubt, do NOT flag.
2.  **Self-Correction Rule**: Ignore any slip-of-the-tongue or writing error that the instructor corrected within the same segment. Only the **final presented content** matters.
3.  **Notation Equivalence**: Do not flag variations in notation (e.g., (x-4)(4-x) vs -(x-4)^2) unless they lead to a demonstrably incorrect conclusion.
4.  **Artistic Context**: Ignore artistic interpretations on Title Slides or Thumbnails. Do not treat stylized decorations (e.g. a crown covering a letter) as scientific errors.
5.  **Exclusion Zone**: Ignore all administrative or marketing claims (e.g., "2025 Update"). Focus ONLY on scientific/mathematical logic.

### **Categories to Watch For:**
*   **Accuracy Issues**: Incorrect formulas/facts relative to High School standards; Title-Content Mismatch; Pedagogical Depth Gap.
*   **Logic Issues**: Logic leaps (skipping critical steps); Prerequisite violations (using concepts before defining them); Causal gaps; Information overload.

---

# PHASE 3: TECHNICAL & MULTIMEDIA AUDIT

## 1. Visual & LecEval Alignment
- **Visual Style**: (e.g., Tablet handwriting, Digital Slides, AI-generated CGI).
- **LecEval Alignment**: Rate as **High/Medium/Low**. Does the visual meaningfully support the audio?
  - *High*: Visuals directly clarify the spoken concept.
  - *Low*: Visuals are purely decorative, irrelevant, or lag behind the narration.
- **Aesthetic Audit (AI Slop)**: Detect "AI-generated fatigue" (glossy plastic 3D renders, unnatural artifacts, sterile CGI, inconsistent art styles).

## 2. Audio & TTS Continuity Audit
- **Pacing**: (Fast / Moderate / Slow).
- **Audio Transition Quality**: Detect slide-based TTS artifacts:
  - **Identity Shifts**: Does the voice tone/pitch change abruptly at slide transitions? (Sounds like a different person).
  - **Transition Glitches**: Detect audio overlaps (bleeding), awkward gaps, or robotic cut-offs between segments.

## 3. Visual Accessibility (CRITICAL)
**Simulate Human Vision**: You (the VLM) may read text easily, but humans cannot if contrast is low. 
- **Contrast Check**: Specifically flag **White/Light text on Pastel/Light backgrounds** (e.g., light blue/pink boxes) or **Dark on Dark**.
- **Severity**: Critical (illegible), Moderate (requires squinting), Minor.


---

# OUTPUT (JSON ONLY)
{{
  "video_title": "{video_title}",
  "teaching_mode": "Conceptual/Procedural/Mixed",
  "content_map": [
    {{ "timestamp": "MM:SS", "topic": "...", "detail_level": "...", "description": "..." }}
  ],
  "potential_issues": [
    {{ "timestamp": "MM:SS", "description": "...", "confidence": 0.9, "evidence_type": "...", "category": "accuracy/logic" }}
  ],
  "presentation_analysis": {{
    "visual_style": "string",
    "ai_slop_detected": boolean,
    "audio_pacing": "string",
    "audio_transition_audit": {{
      "vocal_consistency": "Consistent/Inconsistent",
      "glitches": ["Description with timestamps"]
    }},
    "visual_content_alignment": {{
      "score": "High/Medium/Low",
      "observation": "Brief explanation of alignment quality"
    }}
  }},
  "visual_accessibility_audit": {{
    "overall_legibility": "High/Medium/Low",
    "contrast_issues": [
      {{ "timestamp": "MM:SS", "issue": "e.g., White text on light pink box", "severity": "Critical/Moderate" }}
    ]
  }},
  "observation_summary": "string"
}}
