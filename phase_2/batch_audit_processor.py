#!/usr/bin/env python3
"""
Batch Video Audit Processor
使用 Gemini Batch API 大量處理影片評估任務
"""

import asyncio
import csv
import json
import os
import re
import subprocess
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from google import genai
from google.genai import types

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
PERSONA_CSV_FILE = PROJECT_ROOT / "persona" / "merged_course_units_with_personas_sub.csv"
EVAL_RESULTS_DIR = PROJECT_ROOT / "eval_results"
TEMP_DOWNLOAD_DIR = Path("temp_videos")
BATCH_WORK_DIR = Path("batch_work")
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Create directories
TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
BATCH_WORK_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class VideoTask:
    """單個影片評估任務"""
    video_url: str
    title: str
    persona: str  # Simplified: just the student_persona string
    video_id: Optional[str] = None
    video_path: Optional[Path] = None
    file_uri: Optional[str] = None
    agent1_request_id: Optional[str] = None
    agent3_request_id: Optional[str] = None

# ============================================================================
# Helper Functions
# ============================================================================

def load_prompt(filename: str) -> str:
    """從 prompts 目錄讀取 prompt 模板"""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()

def normalize_title(s: str) -> str:
    """Normalize Unicode quotes and whitespace for robust matching"""
    return (s.strip()
            .replace("\u2019", "'")  # Unicode right single quote (U+2019) → ASCII
            .replace("\u2018", "'")  # Unicode left single quote (U+2018) → ASCII
            .replace("\u201d", '"')  # Unicode right double quote (U+201D) → ASCII
            .replace("\u201c", '"')  # Unicode left double quote (U+201C) → ASCII
            .replace("\u2013", "-")  # En dash (U+2013) → hyphen
            .replace("\u2014", "-")) # Em dash (U+2014) → hyphen

# ============================================================================
# Video Download (Async)
# ============================================================================

async def download_video_async(url: str, task_idx: int, total: int) -> Tuple[str, Path]:
    """異步下載 YouTube 影片"""
    output_tmpl = str(TEMP_DOWNLOAD_DIR / "%(id)s.%(ext)s")
    
    print(f"[{task_idx}/{total}] Downloading video: {url}")
    
    try:
        # Get video ID first
        cmd_id = ["yt-dlp", "--get-id", url]
        proc_id = await asyncio.create_subprocess_exec(
            *cmd_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc_id.communicate()
        
        if proc_id.returncode != 0:
            error_msg = stderr.decode().strip()
            raise RuntimeError(f"Failed to get video ID: {error_msg}")
        
        video_id = stdout.decode().strip()
        
        if not video_id:
            raise RuntimeError("Empty video ID returned")
        
        # Check if already downloaded
        video_path = TEMP_DOWNLOAD_DIR / f"{video_id}.mp4"
        if video_path.exists():
            print(f"   ✓ Video already exists: {video_id}")
            return video_id, video_path
        
        # Download video
        cmd_dl = [
            "yt-dlp",
            "-f", "best[height<=720][ext=mp4]",
            "--output", output_tmpl,
            url
        ]
        proc_dl = await asyncio.create_subprocess_exec(
            *cmd_dl,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_dl, stderr_dl = await proc_dl.communicate()
        
        if proc_dl.returncode != 0:
            error_msg = stderr_dl.decode().strip()
            raise RuntimeError(f"Failed to download video: {error_msg}")
        
        if not video_path.exists():
            raise RuntimeError(f"Video file not found after download: {video_path}")
        
        print(f"   ✓ Downloaded: {video_id}")
        return video_id, video_path
        
    except Exception as e:
        print(f"   ✗ Error downloading {url}: {e}")
        raise

# ============================================================================
# Persona Loading
# ============================================================================

def load_personas_by_title(title_en: str) -> List[str]:
    """從 CSV 載入匹配的 personas（只返回 student_persona 字符串）"""
    personas = []
    
    if not PERSONA_CSV_FILE.exists():
        print(f"Error: Persona CSV file not found: {PERSONA_CSV_FILE}")
        return personas
    
    search_title = normalize_title(title_en)
    
    try:
        with open(PERSONA_CSV_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                csv_title_raw = row.get("title_en", "")
                csv_title = normalize_title(csv_title_raw)
                
                if csv_title == search_title:
                    student_persona = row.get("student_persona", "").strip()
                    if student_persona:
                        personas.append(student_persona)
    
    except Exception as e:
        print(f"Error reading CSV: {e}")
        traceback.print_exc()
    
    return personas

# ============================================================================
# Async Concurrent Processor Class
# ============================================================================

class AsyncConcurrentProcessor:
    """使用 asyncio 並發處理多個影片"""
    
    def __init__(self, api_key: str, max_concurrent: int = 3):
        self.client = genai.Client(api_key=api_key)
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Load prompt templates
        print("Loading prompt templates...")
        self.agent1_prompt_template = load_prompt("agent1_prompt.md")
        self.agent2_prompt_template = load_prompt("agent2_prompt.md")
        self.subjective_prompt_template = load_prompt("subjective_prompt.md")
        print("✓ Prompts loaded successfully\n")
        
        # System instructions
        self.agent1_system_instruction = """You are a METICULOUS EDUCATIONAL CONTENT ANALYST with expertise in Senior High School (AP/IB level) science and math education. 
Your dual role:
1. MAP what is taught: Document every concept, formula, or definition chronologically with its level of detail
2. IDENTIFY potential issues: Log errors or gaps based ONLY on High School standards

Do NOT assign final scores - that is Agent 2's job.

KNOWLEDGE BOUNDARY:
- Use the standard curriculum for students aged 15-18 (e.g., AP Physics/Biology, IB Science).
- DO NOT use university-level rigor or advanced theories (e.g., Quantum Electrodynamics, Molecular Orbital Theory) to invalidate correct high school level simplifications. 
- A simplified model (like the Bohr model in chemistry or Newtonian mechanics in physics) is considered CORRECT if it is standard at the High School level."""
    
    async def prepare_tasks(self, input_config: List[Dict]) -> List[VideoTask]:
        """
        準備所有任務
        input_config: [{"video_url": "...", "title": "..."}, ...]
        """
        print("=" * 80)
        print("PHASE 1: TASK PREPARATION")
        print("=" * 80)
        
        tasks = []
        
        # Group by video URL to avoid duplicate downloads
        url_to_tasks = {}
        
        for idx, config in enumerate(input_config, 1):
            video_url = config["video_url"]
            title = config["title"]
            
            # Load personas - support two modes:
            # 1. Direct personas in config (new format)
            # 2. Load from CSV by title (legacy format)
            if "personas" in config and config["personas"]:
                personas = config["personas"]
                print(f"[{idx}] {title}")
                print(f"    Personas: {len(personas)} (from input)")
            else:
                personas = load_personas_by_title(title)
                if not personas:
                    print(f"⚠️  [{idx}] No personas found for: {title}")
                    continue
                print(f"[{idx}] {title}")
                print(f"    Personas: {len(personas)} (from CSV)")
            
            # Create task for each persona
            for persona in personas:
                task = VideoTask(
                    video_url=video_url,
                    title=title,
                    persona=persona
                )
                tasks.append(task)
                
                # Group by URL
                if video_url not in url_to_tasks:
                    url_to_tasks[video_url] = []
                url_to_tasks[video_url].append(task)
        
        print(f"\n✓ Total tasks prepared: {len(tasks)}")
        print(f"✓ Unique videos: {len(url_to_tasks)}\n")
        
        # Download all unique videos asynchronously
        print("=" * 80)
        print("PHASE 2: VIDEO DOWNLOAD (Async)")
        print("=" * 80)
        
        download_tasks = []
        urls = list(url_to_tasks.keys())
        
        for idx, url in enumerate(urls, 1):
            download_tasks.append(download_video_async(url, idx, len(urls)))
        
        # Execute all downloads in parallel
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Map results back to tasks
        for url, result in zip(urls, download_results):
            if isinstance(result, Exception):
                print(f"✗ Failed to download {url}: {result}")
                continue
            
            video_id, video_path = result
            
            # Update all tasks with this URL
            for task in url_to_tasks[url]:
                task.video_id = video_id
                task.video_path = video_path
        
        print(f"\n✓ Downloaded {len([r for r in download_results if not isinstance(r, Exception)])} videos\n")
        
        return tasks
    
    def run_agent1_sync(self, video_path: Path, title: str) -> Dict:
        """Agent 1: 內容分析（同步）"""
        try:
            # Upload video
            video_file = self.client.files.upload(
                file=str(video_path),
                config={"mime_type": "video/mp4"}
            )
            
            # Wait for processing
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = self.client.files.get(name=video_file.name)
            
            if video_file.state.name == "FAILED":
                raise ValueError(f"Video upload failed: {video_path}")
            
            # Generate content
            agent1_prompt = self.agent1_prompt_template.format(video_title=title)
            
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[video_file, agent1_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=self.agent1_system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            # Clean up
            self.client.files.delete(name=video_file.name)
            
            result = response.parsed
            if result is None and response.text:
                try:
                    result = json.loads(response.text)
                except json.JSONDecodeError:
                    result = {"error": "JSON parse failed", "raw": response.text}
            
            return result or {"error": "Empty response"}
            
        except Exception as e:
            print(f"      ✗ Agent 1 error: {e}")
            return {"error": str(e)}
    
    def run_agent2_sync(self, title: str, agent1_output: Dict) -> Dict:
        """Agent 2: 評分判斷（同步）"""
        agent1_text = json.dumps(agent1_output, indent=2, ensure_ascii=False)
        
        prompt = self.agent2_prompt_template.format(
            video_title=title,
            agent1_output=agent1_text
        )
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction="You are a strict scoring judge.",
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            
            result = response.parsed
            if result is None and response.text:
                try:
                    result = json.loads(response.text)
                except json.JSONDecodeError:
                    result = {"error": "JSON parse failed", "raw": response.text}
            
            return result or {"error": "Empty response"}
            
        except Exception as e:
            print(f"      ✗ Agent 2 error: {e}")
            return {"error": str(e)}
    
    def _check_agent3_scores_valid(self, result: Dict) -> bool:
        """檢查 Agent 3 分數是否有效（不是都為 0）"""
        try:
            subj_scores = result.get("subjective_scores", {})
            adaptability = subj_scores.get("adaptability", {})
            engagement = subj_scores.get("engagement", {})
            
            # Extract scores (handle both dict and direct value)
            adapt_score = adaptability.get("score", adaptability) if isinstance(adaptability, dict) else adaptability
            engage_score = engagement.get("score", engagement) if isinstance(engagement, dict) else engagement
            
            # Check if both are 0
            if adapt_score == 0 and engage_score == 0:
                return False
            return True
        except Exception:
            # If structure is unexpected, consider it valid to avoid infinite retry
            return True
    
    def run_agent3_sync(self, video_path: Path, persona: str, agent1_result: Dict, agent2_result: Dict) -> Dict:
        """
        Agent 3: 主觀模擬（同步）
        如果分數都是 0，自動重試一次
        """
        max_retries = 2  # 最多嘗試2次
        
        for attempt in range(1, max_retries + 1):
            try:
                # Upload video
                video_file = self.client.files.upload(
                    file=str(video_path),
                    config={"mime_type": "video/mp4"}
                )
                
                # Wait for processing
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = self.client.files.get(name=video_file.name)
                
                if video_file.state.name == "FAILED":
                    raise ValueError(f"Video upload failed: {video_path}")
                
                # Prepare data
                content_map_summary = json.dumps(
                    agent1_result.get("content_map", [])[:5],
                    indent=2,
                    ensure_ascii=False
                )
                error_list = json.dumps(
                    agent2_result.get("verified_errors", [])[:3],
                    indent=2,
                    ensure_ascii=False
                )
                
                # Generate content
                agent3_prompt = self.subjective_prompt_template.format(
                    student_persona=persona,
                    accuracy_score=agent2_result.get('accuracy_score', 'N/A'),
                    logic_score=agent2_result.get('logic_score', 'N/A'),
                    error_list=error_list,
                    content_map_summary=content_map_summary
                )
                
                # Add retry hint if this is a retry
                if attempt > 1:
                    agent3_prompt += "\\n\\nIMPORTANT: Please provide meaningful non-zero scores for adaptability and engagement based on the video content."
                
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[video_file, agent3_prompt],
                    config=types.GenerateContentConfig(
                        system_instruction="You are simulating a student's experience.",
                        temperature=0.3,
                        response_mime_type="application/json"
                    )
                )
                
                # Clean up
                self.client.files.delete(name=video_file.name)
                
                result = response.parsed
                if result is None and response.text:
                    try:
                        result = json.loads(response.text)
                    except json.JSONDecodeError:
                        result = {"error": "JSON parse failed", "raw": response.text}
                
                final_result = result or {"error": "Empty response"}
                
                # Check if scores are valid
                if self._check_agent3_scores_valid(final_result):
                    if attempt > 1:
                        print(f"      ✓ Retry successful (attempt {attempt})")
                    return final_result
                else:
                    if attempt < max_retries:
                        print(f"      ⚠️  Agent 3 returned zero scores, retrying (attempt {attempt}/{max_retries})...")
                        continue
                    else:
                        print(f"      ⚠️  Agent 3 still returned zero scores after {max_retries} attempts")
                        return final_result
                
            except Exception as e:
                print(f"      ✗ Agent 3 error (attempt {attempt}): {e}")
                if attempt == max_retries:
                    return {"error": str(e)}
                else:
                    print(f"      → Retrying...")
                    continue
        
        return {"error": "Max retries exceeded"}
    
    async def process_single_task(self, task: VideoTask, task_idx: int, total: int) -> Dict:
        """異步處理單個任務"""
        async with self.semaphore:
            print(f"\n[{task_idx}/{total}] Processing: {task.title}")
            print(f"   Persona: {task.persona[:80]}...")
            
            try:
                # Run Agent 1 (在線程中運行同步代碼)
                print("   → Agent 1: Content Analysis...")
                agent1_result = await asyncio.to_thread(
                    self.run_agent1_sync,
                    task.video_path,
                    task.title
                )
                
                # Run Agent 2
                print("   → Agent 2: Scoring...")
                agent2_result = await asyncio.to_thread(
                    self.run_agent2_sync,
                    task.title,
                    agent1_result
                )
                
                # Run Agent 3
                print("   → Agent 3: Subjective Simulation...")
                agent3_result = await asyncio.to_thread(
                    self.run_agent3_sync,
                    task.video_path,
                    task.persona,
                    agent1_result,
                    agent2_result
                )
                
                # Extract scores
                accuracy_score = agent2_result.get("accuracy_score", 0)
                logic_score = agent2_result.get("logic_score", 0)
                
                subj_scores = agent3_result.get("subjective_scores", {})
                adaptability = subj_scores.get("adaptability", 0)
                engagement = subj_scores.get("engagement", 0)
                
                if isinstance(adaptability, dict):
                    adaptability = adaptability.get("score", 0)
                if isinstance(engagement, dict):
                    engagement = engagement.get("score", 0)
                
                print(f"   ✓ Completed: Accuracy={accuracy_score:.2f}, Logic={logic_score:.2f}, "
                      f"Adaptability={adaptability:.2f}, Engagement={engagement:.2f}")
                
                return {
                    "task": task,
                    "agent1_result": agent1_result,
                    "agent2_result": agent2_result,
                    "agent3_result": agent3_result,
                    "scores": {
                        "accuracy": accuracy_score,
                        "logic": logic_score,
                        "adaptability": adaptability,
                        "engagement": engagement
                    },
                    "success": True
                }
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
                traceback.print_exc()
                return {
                    "task": task,
                    "error": str(e),
                    "success": False
                }
    
    async def process_all_tasks(self, tasks: List[VideoTask], output_dir: Path) -> Path:
        """並發處理所有任務"""
        print("\n" + "=" * 80)
        print(f"PHASE 3: CONCURRENT PROCESSING ({self.max_concurrent} at a time)")
        print("=" * 80)
        
        # Filter tasks with valid video paths
        valid_tasks = [t for t in tasks if t.video_path and t.video_path.exists()]
        print(f"\n✓ Processing {len(valid_tasks)} tasks with {self.max_concurrent} concurrent workers\n")
        
        # Create processing tasks
        processing_tasks = [
            self.process_single_task(task, idx, len(valid_tasks))
            for idx, task in enumerate(valid_tasks, 1)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        # Save results
        print("\n" + "=" * 80)
        print("PHASE 4: SAVING RESULTS")
        print("=" * 80)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        all_results = []
        csv_summary = []
        
        for idx, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"[{idx}] Exception: {result}")
                continue
            
            if not result.get("success"):
                continue
            
            task = result["task"]
            agent1_result = result["agent1_result"]
            agent2_result = result["agent2_result"]
            agent3_result = result["agent3_result"]
            scores = result["scores"]
            
            # Combine report
            combined_report = {
                "agent1_content_analyst": {
                    "content_map": agent1_result.get("content_map", []),
                    "potential_issues": agent1_result.get("potential_issues", []),
                },
                "agent2_gap_analysis_judge": {
                    "accuracy_score": scores["accuracy"],
                    "logic_score": scores["logic"],
                    "verified_errors": agent2_result.get("verified_errors", []),
                },
                "subjective_evaluation": {
                    "adaptability": {"score": scores["adaptability"]},
                    "engagement": {"score": scores["engagement"]},
                    "student_monologue": agent3_result.get("student_monologue", ""),
                },
                "_meta": {
                    "video_url": task.video_url,
                    "title_en": task.title,
                    "student_persona": task.persona,
                    "timestamp": timestamp,
                    "task_index": idx,
                }
            }
            
            # Save JSON
            json_filename = f"{timestamp}_task_{idx}.json"
            json_path = output_dir / json_filename
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(combined_report, f, indent=2, ensure_ascii=False)
            
            all_results.append(combined_report)
            
            # CSV record
            csv_summary.append({
                "timestamp": timestamp,
                "video_url": task.video_url,
                "title_en": task.title,
                "student_persona": task.persona[:100],
                "accuracy": scores["accuracy"],
                "logic": scores["logic"],
                "adaptability": scores["adaptability"],
                "engagement": scores["engagement"],
                "json_file": json_filename,
            })
        
        # Save CSV summary
        csv_filename = f"{timestamp}_summary.csv"
        csv_path = output_dir / csv_filename
        
        if csv_summary:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=csv_summary[0].keys())
                writer.writeheader()
                writer.writerows(csv_summary)
        
        print(f"\n✓ Saved {len(all_results)} results to: {output_dir}")
        print(f"✓ CSV summary: {csv_path}\n")
        
        return csv_path

# ============================================================================
# Main Workflow
# ============================================================================


# ============================================================================
# Main Workflow
# ============================================================================

async def main():
    """主要工作流程"""
    
    print("\n" + "=" * 80)
    print(" ASYNC CONCURRENT VIDEO AUDIT PROCESSOR")
    print("=" * 80 + "\n")
    
    # Check API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not set")
        print("   Run: export GEMINI_API_KEY='your-api-key'")
        return
    
    # ============================================================
    # Input Configuration
    # ============================================================
    # Load from JSON file (recommended)
    input_file = Path("input_videos.json")
    if input_file.exists():
        with open(input_file, "r", encoding="utf-8") as f:
            input_config = json.load(f)
        print(f"✓ Loaded {len(input_config)} videos from {input_file}\n")
    else:
        print(f"⚠️  {input_file} not found, please create one")
        print(f"   See input_videos_example.json for format\n")
        return
    
    # ============================================================
    # Initialize Processor
    # ============================================================
    max_concurrent = int(os.environ.get("MAX_CONCURRENT", "3"))
    print(f"✓ Max concurrent tasks: {max_concurrent}\n")
    
    processor = AsyncConcurrentProcessor(api_key=api_key, max_concurrent=max_concurrent)
    
    # ============================================================
    # PHASE 1-2: Prepare tasks and download videos
    # ============================================================
    tasks = await processor.prepare_tasks(input_config)
    
    if not tasks:
        print("❌ No valid tasks to process")
        return
    
    # ============================================================
    # PHASE 3-4: Process all tasks concurrently
    # ============================================================
    output_dir = EVAL_RESULTS_DIR / f"concurrent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    csv_path = await processor.process_all_tasks(tasks, output_dir)
    
    # ============================================================
    # PHASE 5: Cleanup
    # ============================================================
    print("=" * 80)
    print("PHASE 5: CLEANUP")
    print("=" * 80)
    
    # Clean up temporary videos
    for task in tasks:
        if task.video_path and task.video_path.exists():
            try:
                task.video_path.unlink()
                print(f"✓ Deleted: {task.video_path.name}")
            except Exception as e:
                print(f"✗ Failed to delete {task.video_path.name}: {e}")
    
    print("\n" + "=" * 80)
    print("✅ CONCURRENT PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Results: {output_dir}")
    print(f"CSV Summary: {csv_path}")
    print("=" * 80 + "\n")

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())

