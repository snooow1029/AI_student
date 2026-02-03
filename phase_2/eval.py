#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from google.genai import Client, types

SYSTEM_INSTRUCTION = """You are a Lead Instructional Designer & Critical Auditor. 
Your goal: Diagnostic-to-Remediation audit for a specific student persona.

SCORING BAR:
- Be rigorous. A score of 3 is 'functional/okay'. 
- A score of 5 is 'Pedagogical Perfection' (e.g., 3Blue1Brown level).
- Do not default to 4; force a distinction between good and exceptional.

REMEDIATION RULE:
For every issue, provide an [ACTION] [Timestamp] [Fix] [Goal] ticket."""

USER_PROMPT_TEMPLATE = """STUDENT PERSONA:
{persona_desc}
Attributes: {persona_attr}

TASK:
1. EVIDENCE: List key visual/audio quotes as facts.
2. AUDIT: Assign 1-5 scores based on:
   - Accuracy (40%): Flawless facts vs Hallucinations.
   - Logic (30%): Scaffolding & Prerequisites vs Chaotic leaps.
   - Adaptability (20%): Analogies & Jargon-fit for the Persona.
   - Engagement (10%): Audio-Visual Sync (Signaling Principle).
3. REMEDIATE: Provide technical instructions for production.

OUTPUT FORMAT (JSON ONLY):
{{
  "summary": {{
    "scores": {{ "acc": 0, "log": 0, "ada": 0, "eng": 0 }},
    "weighted": 0.0,
    "monologue": "Persona's inner thought."
  }},
  "audit": [
    {{ "time": "MM:SS", "issue": "...", "mayer": "principle", "plan": "[ACTION]..." }}
  ],
  "fact_check": "Detailed error list or 'None'"
}}"""

DEFAULT_PERSONA = {
    "description": "Middle schooler (Grades 7-9). Visual learner, hates raw formulas without analogies.",
    "category": { "grade": "7-9", "style": "visual", "priors": "basic math" }
}

def _safe_filename(s: str) -> str:
    """Replace full-width characters in file names with ASCII-safe equivalents to avoid encoding issues."""
    return s.replace("\uff5c", "|")  # Full-width '｜' → half-width '|'


def collect_video_paths(data_dir: str) -> list[tuple[str, str]]:
    data_path = Path(data_dir)
    if not data_path.exists(): return []
    videos = []
    for theme_dir in data_path.iterdir():
        if not theme_dir.is_dir(): continue
        for f in theme_dir.glob("*.mp4"):
            videos.append((theme_dir.name, str(f)))
    return sorted(videos)

def run_unified_audit_pipeline(client: Client, video_path: str, persona: dict) -> dict:
    # Copy to a temporary path (ASCII-only filename) to avoid Unicode characters like '｜' breaking upload
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(video_path, tmp_path)
        video_file = client.files.upload(file=tmp_path)
    finally:
        os.unlink(tmp_path)

    # Wait until file state is ACTIVE; keep polling while state is None or PROCESSING
    while True:
        state = str(video_file.state or "").upper()
        if state == "ACTIVE":
            break
        if state == "FAILED":
            raise ValueError(f"File processing failed: {video_file.name}")
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    persona_attr = persona.get("category", persona.get("attributes", {}))
    prompt = USER_PROMPT_TEMPLATE.format(
        persona_desc=persona["description"],
        persona_attr=json.dumps(persona_attr, ensure_ascii=False),
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            max_output_tokens=4096,
            temperature=0.1,
        ),
    )

    try:
        text = response.text
    except (ValueError, AttributeError) as e:
        cand = response.candidates[0] if response.candidates else None
        reason = getattr(cand, "finish_reason", None) if cand else None
        raise ValueError(
            f"Response invalid (finish_reason={reason}): {e}. "
            "If this is MAX_TOKENS, please increase max_output_tokens."
        ) from e

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "JSON Decode Error", "raw": text[:500]}

def main():
    parser = argparse.ArgumentParser(description="Phase 2 VLM Audit")
    parser.add_argument("-n", "--num-samples", type=int, default=None)
    parser.add_argument("-d", "--data-dir", type=str, default="data")
    parser.add_argument("-o", "--output-dir", type=str, default="eval_results")
    parser.add_argument("--personas", type=str, default=None)
    parser.add_argument("--persona-index", type=int, default=0)
    args = parser.parse_args()

    api_key = "AIzaSyAk9fTQQ7q3YhCa0dnam5F9zR83ut9ltaU"  # Prefer reading this from environment variables in production
    if not api_key:
        print("Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variables")
        return 1
    client = Client(api_key=api_key)

    script_dir = Path(__file__).parent
    data_dir = script_dir / args.data_dir
    videos = collect_video_paths(str(data_dir))
    if not videos: return 1
    if args.num_samples: videos = videos[:args.num_samples]

    # Load persona configuration
    persona = DEFAULT_PERSONA
    if args.personas:
        with open(args.personas, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
            persona = lines[args.persona_index]

    output_dir = script_dir / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, (theme, video_path) in enumerate(videos, 1):
        name = Path(video_path).stem
        print(f"[{i}/{len(videos)}] Auditing: {theme}/{name}")
        try:
            report = run_unified_audit_pipeline(client, video_path, persona)
            report["_meta"] = {"video": name, "theme": theme}
            
            out_name = _safe_filename(f"{theme}_{name}.json")
            with open(output_dir / out_name, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            results.append(report)
            score = report.get("summary", {}).get("weighted", "?")
            print(f"   ✓ Score: {score}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, ensure_ascii=False, indent=2)

    return 0

if __name__ == "__main__":
    exit(main())