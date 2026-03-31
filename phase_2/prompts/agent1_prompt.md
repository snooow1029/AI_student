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

Extract all uncorrected errors. To ensure the highest audit rigor and minimize *hallucinated bugs*, you **MUST** apply the following **Strict Verification Protocol** before logging any issue:

---

### 1. The 0.9 Confidence & Multimodal Priority Rule

- **Visual vs. Audio (for `potential_issues` only)**  
  VLMs often misread complex notation (e.g., `6/6` as `4/4`, `Δ` as `A`).  
  If the visual text looks wrong but the **audio explanation is pedagogically correct**, assume the visual is a minor rendering or handwriting artifact and **DO NOT FLAG** in `potential_issues` unless it is a persistent, critical error.  
  Conversely, VLMs also often mis-transcribe spoken math/science terms (e.g., hearing "m v squared" as "m fit squared", or "delta" as "dealt-uh"). If the **on-screen formula is correct** and the spoken pronunciation is a plausible colloquial, informal, or TTS-generated rendition of the same term, **DO NOT FLAG**. Only flag if the speaker says something **semantically different** that would mislead the student (e.g., saying "velocity cubed" when the screen shows `v²`).  
  **This rule does NOT apply to `presentation_analysis` alignment:** if the **spoken topic, equation, or labels** clearly refer to one idea while the **slide or on-screen text/graphic** refers to another (or is stuck on an old slide), that is **narration–slide mismatch** — you must still capture it under **PHASE 3 → Visual & LecEval Alignment** (see below), even when the audio alone is pedagogically sound.

- **Doubt = No Flag**  
  If you are **less than 90% certain** that an item is an error under **High School standards**, do not log it.

---

### 2. The "High School Boundary" Rule (Avoid Over-Pedantry)

- **Valid Simplifications**  
  High School science uses simplified models (e.g., Bohr model in Chemistry, Newtonian mechanics without relativity).  
  **DO NOT FLAG** these as inaccurate if they are standard at the AP/IB level, even if technically incomplete at the university level.

- **Pedagogical License**  
  If an instructor uses a non-standard term to aid intuition, it is **not an error** unless it creates a fundamental misconception.

---

### 3. The Final-State (Self-Correction) Rule

- **Segment-Level Resolution**  
  Check the **10 seconds following** a suspected error.  
  If the instructor says *“Sorry, I meant X”* or overwrites a number on screen, it is a **Self-Correction** and must be **EXCLUDED** from the audit.

- Only log **Silent Errors** that remain uncorrected.

---

### 4. The Functional Equivalence Rule

- **Mathematical Synonyms**  
  Expressions such as  
  `(x − 4)(4 − x)` and `−(x − 4)²`,  
  or different but valid methods of balancing a redox reaction, are **NOT errors**.

- **Notation Variance**  
  Do not flag differences in notation (e.g., `f′(x)` vs. `dy/dx`) **unless** the instructor becomes inconsistent and causes logical confusion.

---

### 5. The Artistic & Metadata Exclusion

- **Decorative Elements**  
  Do not over-analyze title slides, thumbnails, or background decorations.  
  If a crown or logo partially covers an “O” in `H₂O`, do not hallucinate it as `HOF`.

- **Admin / Marketing Content**  
  Ignore claims about exam dates, “2025 updates,” or instructor credentials.

---

## Issue Taxonomy (Categories to Watch For)

### A. Accuracy Issues (Scientific / Fact-based)

- **Critical Fact / Formula Error**  
  A fundamental, uncorrected error in a core formula or scientific law  
  (e.g., stating gravity is an upward force).

- **Title–Content Mismatch (High Priority)**  
  The video content deviates fundamentally from the title `{video_title}`.  
  *Example:* Title is *“Chemistry of Water”* but content is *“Gene Regulation.”*

- **Pedagogical Depth Gap**  
  The title promises *conceptual understanding*, but the content is entirely *recipe-style calculation* with no explanation of *why*.

---

### B. Logic Issues (Instructional Flow)

- **Logic Leaps (Scaffolding Failure)**  
  The instructor jumps from Step A to Step D without explaining intermediate reasoning, exceeding the cognitive capacity of a 15–18 year old learner.

- **Prerequisite Violations**  
  Using calculus concepts in a *Pre-Calculus* video without prior definition.

- **Causal Inconsistencies**  
  Drawing a “therefore…” conclusion that is not logically supported by preceding evidence.

- **Information Overload**  
  Cramming too many unrelated facts into a single segment without clear transitions or segmentation  
  (violating **Mayer’s Segmenting Principle**).

---

# PHASE 3: TECHNICAL & MULTIMEDIA AUDIT

## 1. Visual & LecEval Alignment
- **Visual Style**: (e.g., Tablet handwriting, Digital Slides, AI-generated CGI).
- **Narration–slide alignment** (single field: `visual_content_alignment`): Judge whether **what is on screen** (figures, equations, labels, bullet text) **matches what the speaker is saying at that moment** — not only whether each modality is “fine” in isolation.

  **Rate `visual_content_alignment.score` as High / Medium / Low** using this rubric:
  - **High**: For most of the runtime, slides or key visuals **track** the narration (same concept, same formula step, same labels). Brief title cards or intro stingers alone do **not** lower this.
  - **Medium**: **Repeated or clearly noticeable** desynchronization: e.g., speaker derives or discusses **Step B** while the slide still shows **Step A** for several seconds; diagram illustrates **concept X** while the voice explains **concept Y**; bullets list keywords that **omit** the term the speaker is defining; **B-roll or stock imagery** that **does not illustrate** the spoken example (generic decoration during a precise claim). List **at least one timestamped** instance in `visual_content_alignment.observation`.
  - **Low**: **Sustained** mismatch or misleading visuals: wrong equation relative to speech, contradictory on-screen text vs. narration, slide **lags several beats** so learners would read one thing while hearing another, or visuals are **mostly irrelevant** to the spoken explanation for long stretches. List **multiple timestamps** (or one long segment) in `observation`.

  **Concrete mismatch patterns to watch for (non-exhaustive):**
  - Voice: “As we see in this graph…” but the visible chart shows a **different** quantity or trend.
  - Speaker references a **specific symbol or term** on screen, but the visible equation/figure uses **different** notation or labels.
  - Slide title or section header **does not match** the subsection the speaker entered (stale slide).
  - Voice corrects or updates an idea, but **on-screen text is never updated**.
  - Decorative **AI / stock** imagery that **conflicts** with the spoken analogy or creates false expectations.

  **Output discipline:**
  - Put the full rationale in **`visual_content_alignment.observation`** (prose). The **score** is the canonical label; do **not** duplicate the same content in a second string field.
  - If score is **Medium** or **Low**, `observation` **must** include **timestamped** evidence (MM:SS), not vague wording.
  - **Do not** mark **High** just because audio quality or pacing is good; alignment is **semantic**, not audio fidelity.

- **Aesthetic Audit (AI Slop)**: Detect "AI-generated fatigue" (glossy plastic 3D renders, unnatural artifacts, sterile CGI, inconsistent art styles).

## 2. Audio & TTS Continuity Audit
- **Pacing**: (Fast / Moderate / Slow).
- **Audio Transition Quality**: Detect slide-based TTS artifacts:
  - **Identity Shifts**: Does the voice tone/pitch change abruptly at slide transitions? (Sounds like a different person).
  - **Transition Glitches**: Detect audio overlaps (bleeding), awkward gaps, or robotic cut-offs between segments.
  - **NOT a glitch**: TTS or human speakers may pronounce math symbols in colloquial or abbreviated ways (e.g., "v squared" sounding like "v-squah'd", or reading "mv²" as a single slurred phrase). These are normal speech patterns, not transition artifacts — do not flag them here.

## 3. Visual Accessibility (CRITICAL)
**Simulate Human Vision**: You (the VLM) may read text easily, but humans cannot if contrast is low. 
- **Contrast Check**: Specifically flag **White/Light text on Pastel/Light backgrounds** (e.g., light blue/pink boxes) or **Dark on Dark**.
- **Aspect Ratio Distortion**: Are text, math formulas, diagrams, or images unnaturally squashed, stretched, or flattened?
  - **How to detect**: Compare the proportions of letters/symbols against standard typesetting. Common signs: italic math characters (e.g., *GM*, *r*, *T*) appear **horizontally compressed or vertically squished**; characters look cramped together with unnatural spacing; equal signs (=) look too narrow; fractions appear flattened so numerator and denominator are too close. Circles in diagrams appear as ovals.
  - **Concrete example**: If `GM/r = (2πr/T)²` looks like the letters are squeezed into a shorter horizontal space than normal — the font appears condensed, bold-ish, and the subscripts/superscripts are unnaturally close — that is aspect ratio distortion.
- **Pixelation/Blurriness**: Is the text, formula, or image low-resolution or blurry?
- **Severity**: Critical (illegible), Moderate (requires squinting), Minor.


---

# OUTPUT (JSON ONLY)
{{
  "teaching_mode": "Conceptual/Procedural/Mixed",
  "content_map": [
    {{ "timestamp": "MM:SS", "topic": "...", "detail_level": "...", "description": "..." }}
  ],
  "potential_issues": [
    {{ "timestamp": "MM:SS", "description": "...", "confidence": 0.9, "evidence_type": "...", "category": "accuracy/logic" }}
  ],
  "presentation_analysis": {{
    "visual_style": "string",
    "ai_slop_detected": ["Description with timestamps"],
    "audio_pacing": "string",
    "audio_transition_audit": {{
        "vocal_consistency": "Describe Consistent/Inconsistent events with timestamps",
        "glitches": ["Description with timestamps"]
    }},
    "visual_content_alignment": {{
        "score": "High/Medium/Low",
        "observation": "If Medium/Low: timestamped narration–slide mismatches (MM:SS). If High: one short sentence why visuals track audio."
    }},
    "visual_accessibility_audit": {{
        "issues": [
            {{ "timestamp": "MM:SS", "type": "contrast/distortion/pixelation", "issue": "e.g., White text on light pink box / Math formula horizontally stretched / Blurry diagram", "severity": "Critical/Moderate/Minor" }}
        ]
    }}
  }},
  "observation_summary": "string"
}}
