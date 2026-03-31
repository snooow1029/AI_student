# YOUR TASK: Content & Logic Quality Judge

Video Title: **{video_title}**

Agent 1 (Content Analyst) has provided:
1. A **content_map** showing what was taught (topics, detail levels, timestamps)
2. A list of **potential_issues** (accuracy/logic bugs — pre-filtered by Agent 1)
3. **presentation_analysis** including visual_content_alignment

```
{agent1_output}
```

---

# CRITICAL OUTPUT REQUIREMENT
- Each severity field MUST output an **INTEGER** in **{{1, 0, -1, -2, -3}}** (see scale below).
- Each count field MUST output an **INTEGER >= 0**.
- Provide clear evidence whenever the rating is not **0**.

## AGENT SEVERITY SCALE (1, 0, -1, -2, -3)
- **+1 (Beyond expectation)**: This criterion is **exceptionally strong**; no deduction.
- **0 (No deduction)**: Meets expectations; no issue for this criterion.
- **-1 (Minor deduction)**: Noticeable but tolerable problem.
- **-2 (Moderate deduction)**: Clear problem; significantly limits learning.
- **-3 (Severe deduction)**: Blocking issue; content fails as promised on this criterion.

## PER-FLAG OUTPUT
Use **1, 0, -1, -2, -3** for every numbered severity field below.

---

# STAGE 1: PEDAGOGICAL DEPTH ISSUES (Apply to Both Accuracy & Logic)

**1. Formula Dumping** → Output: INTEGER 1, 0, -1, -2, or -3
*Teacher gives formula with NO derivation AND no intuition/analogy whatsoever.*
- **+1** = Every major formula is motivated: intuition, analogy, limiting case, or sketch of derivation before or alongside formalism; scaffolding is **clearly stronger than typical** for this topic and runtime (reserve for rare, standout exposition—do not use +1 for merely "acceptable").
- -1 = Has definitions but skips "why" for 1 key concept
- -2 = Multiple key formulas presented without any rationale
- -3 = Entire video presents formulas as facts with zero conceptual scaffolding

**2. Pure Calculation Bias** → Output: INTEGER 1, 0, -1, -2, or -3
*Over 70%+ of content_map items are "Worked Example (Calculation)" with minimal theory.*
- **+1** = Worked examples are **subordinate** to a visible conceptual spine: theory and structure lead; calculations illustrate rather than dominate; proportion and pacing make the video feel **concept-first**, not drill-heavy (even if many items are calculations on the map).
- -1 = Theory exists but is brief (~60% calculation)
- -2 = Heavily skewed (~75% calculation, thin theory)
- -3 = Almost pure calculation (>85%), essentially a worked-examples playlist

**3. Pedagogical Depth Gap** → Output: INTEGER 1, 0, -1, -2, or -3
*Title promises "Concept/Understanding" but content is procedural.*
- -1 = Title slightly overpromises, some conceptual content exists
- -2 = Title says "Understanding" but content is mostly procedural
- -3 = Complete mismatch: title promises derivation/concept, video is pure plug-and-chug

---

# STAGE 2: COMPLETENESS ISSUES (Apply to Both Accuracy & Logic)

**4. Content Brevity** → Output: INTEGER 1, 0, -1, -2, or -3
*Content is too thin relative to the title's promise.*
- -1 = Slightly brief; most key topics covered but thin
- -2 = Clearly incomplete; important sections missing
- -3 = Near-empty (< 3 content_map items, or < 2 min of actual teaching)

**5. Superficial Coverage** → Output: INTEGER 1, 0, -1, -2, or -3
*Title promises depth (Derivation/Proof/Analysis) but detail_levels are shallow.*
- **+1** = Where the title implies derivation, proof, or analysis, the video **delivers fully**: non-skipped critical steps, explicit assumptions, and closure appropriate to the claim—depth is **clearly above** a rushed or "result-only" treatment for comparable length (reserve for standout thoroughness).
- -1 = Some depth missing; key steps rushed
- -2 = Critical derivation/proof incomplete or heavily abbreviated
- -3 = Promised derivation/proof completely absent; only result stated

**6. Missing Core Concepts** → Output: INTEGER 1, 0, -1, -2, or -3
*Essential topics for this video_title are entirely absent.*
- -1 = 1 minor supporting concept missing
- -2 = 1 core concept absent (e.g., "Limits & Continuity" video missing continuity)
- -3 = Multiple core concepts absent; video fails its stated scope

**7. Breadth Without Depth** → Output: INTEGER 1, 0, -1, -2, or -3
*Many topics touched at "Mentioned" level; few reach "Explained" or higher.*
- **+1** = **Wide scope without thinning**: most `content_map` items reach **Explained** (or deeper), not merely "Mentioned"; the video sustains substance across topics instead of a shallow survey (unusual clarity given breadth—reserve for exceptional integration).
- -1 = Some breadth issues; most topics have adequate depth
- -2 = Majority of topics are "Mentioned" only
- -3 = Essentially a topic list with no meaningful depth anywhere

---

# STAGE 3: ACCURACY ISSUES (Accuracy Score Only)

**8. Title-Content Mismatch** → Output: INTEGER 1, 0, -1, -2, or -3
*Video content deviates significantly from what the title promises.*
- -1 = Minor overpromising (small scope difference)
- -2 = Significant mismatch (e.g., "Derivation" video shows only formula)
- -3 = Fundamental mismatch (completely different topic or approach)

**9. Visual Alignment Issue** → Output: INTEGER 1, 0, -1, -2, or -3
*From Agent 1's visual_content_alignment — visuals systematically fail to support audio.*
- **+1** = **Exceptional alignment**: graphics, notation, and on-screen emphasis **track** the spoken argument in real time; visuals **anticipate or repair** potential confusion (e.g., highlighting, step-wise reveals) so the learner rarely must "ignore the screen" to follow—clearly above standard slide-read-along quality (reserve for standout integration).
- **0** = High alignment (visuals directly clarify concepts).
- **-1** = Medium alignment (occasional misalignment).
- **-2** = Low alignment (decorative images during technical content, slides lag narration).
- **-3** = Severe misalignment (visuals actively contradict or distract from audio).

**10. Critical Fact Error Count** → Output: INTEGER count (>=0)
*Uncorrected scientific/mathematical errors from potential_issues.*
- **INCLUDES**: Calculation mistakes, false scientific claims, misleading overgeneralizations, and **incorrect scientific diagrams** (e.g., wrong chemical structures) even if audio is correct.
- **FILTER RULES**: Exclude self-corrected errors, algebraically equivalent notations, and suspected VLM visual misreads. Confidence >= 0.8 only.

**11. Minor Slip Count** → Output: INTEGER count (>=0)
*Small errors that persist (not self-corrected).* 
- **INCLUDES**: Minor typos, dropped negative signs in intermediate steps, or **imprecise terminology** (e.g., loosely saying "weight" instead of "mass") that don't derail the final conclusion.
- **FILTER RULES**: Confidence >= 0.6. Exclude algebraically valid rewrites.

---

# STAGE 4: LOGIC ISSUES (Logic Score Only)

**12. Logic Flow** → Output: STRING 
- `inductive`: Real-world examples → Abstract formula (Best for beginners).
- `deductive`: Principle/Definition → Formula → Examples (Standard academic, acceptable).
- `formula_dump`: Formula given as fact → Plug-and-chug (Poor scaffolding).

**13. Logic Leap Count** → Output: INTEGER count (>=0)
*Critical derivation steps skipped without justification. Confidence >= 0.75*

**14. Prerequisite Violation Count** → Output: INTEGER count (>=0)
*Advanced concepts used before prerequisites are defined. Confidence >= 0.75*

**15. Causal Inconsistency Count** → Output: INTEGER count (>=0)
*Conclusions stated where the logic/evidence doesn't support them. Confidence >= 0.7*

**16. Information Overload Count** → Output: INTEGER count (>=0)
*Segments where too much is crammed without clear transitions. Confidence >= 0.6*

---

# OUTPUT (JSON ONLY)
{{
  "content_overview": {{
    "teaching_mode": "Conceptual/Procedural/Mixed",
    "content_map_size": 0
  }},
  "pedagogical_depth": {{
    "formula_dumping_level": 0,
    "formula_dumping_evidence": "...",
    "pure_calculation_bias_level": 0,
    "pure_calculation_bias_evidence": "...",
    "pedagogical_depth_gap_level": 0,
    "pedagogical_depth_gap_evidence": "..."
  }},
  "completeness": {{
    "content_brevity_level": 0,
    "content_brevity_evidence": "...",
    "superficial_coverage_level": 0,
    "superficial_coverage_evidence": "...",
    "missing_core_concepts_level": 0,
    "missing_core_concepts_evidence": "...",
    "breadth_without_depth_level": 0,
    "breadth_without_depth_evidence": "..."
  }},
  "accuracy_flags": {{
    "title_content_mismatch_level": 0,
    "title_content_mismatch_evidence": "...",
    "visual_alignment_issue_level": 0,
    "visual_alignment_issue_evidence": "...",
    "critical_fact_error_count": 0,
    "critical_fact_error_evidence": "Brief list of critical errors, e.g. '03:08 incorrect bond notation; 03:41 wrong units'",
    "minor_slip_count": 0,
    "minor_slip_evidence": "Brief list of minor slips, e.g. '04:42 typo in time unit'"
  }},
  "logic_flags": {{
    "logic_flow_assessment": "inductive/deductive/formula_dump",
    "logic_leap_count": 0,
    "prerequisite_violation_count": 0,
    "causal_inconsistency_count": 0,
    "information_overload_count": 0
  }},
  "verified_errors": [
    {{"timestamp": "MM:SS", "type": "accuracy/logic", "severity": "critical/minor", "description": "..."}}
  ],
  "scoring_rationale": "Brief explanation of major issues found."
}}
