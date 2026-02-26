## AI student

This repo is organized into two main phases:

- **phase_1**: earlier experiments and text evaluation pipeline (legacy, not documented here yet).
- **phase_2**: YouTube data collection and Gemini-based video evaluation.

Below are the main scripts used in **phase_2**.

---

### `phase_2/data_collect.py`

- **Purpose**:  
  Download YouTube playlist videos (e.g., Khan Academy middle school chemistry/physics) to build a small local dataset.

- **What it does**:
  - Creates a folder `phase_2/data/<theme>/` (e.g., `data/chemistry/`).
  - Uses `yt-dlp` to download:
    - Video (best quality up to 720p, or best available).
    - Auto-generated subtitles in English and Traditional Chinese (`en`, `zh-Hant`) when possible.
  - Uses a browser cookie file `www.youtube.com_cookies.txt` and Android client impersonation to reduce 403/429 errors.

- **Requirements**:
  - Python 3
  - `yt-dlp` installed on PATH
  - (Recommended) `ffmpeg` installed for merging video + audio
  - A valid `www.youtube.com_cookies.txt` in `phase_2/`

- **Run** (from `phase_2/`):
  ```bash
  cd phase_2
  python data_collect.py
  ```

---

### `phase_2/eval.py`

- **Purpose**:  
  Run a Gemini-based *diagnostic-to-remediation* audit on a single YouTube video for multiple student personas.

- **What it does**:
  - Downloads one YouTube video, runs Agent 1 (Content Analyst) + Agent 2 (Gap Analysis Judge) + Agent 3 (Subjective Simulation) per persona.
  - Loads personas from `persona/sep/*.csv` by matching `title_en`.
  - Saves per-persona JSON reports to `eval_results/<topic>/<video_id>/<version>/`.

- **Requirements**:
  - Python 3, `google-genai`, `yt-dlp`
  - `export GEMINI_API_KEY="YOUR_API_KEY"`

- **Basic usage** (from project root or `phase_2/`):
  ```bash
  python phase_2/eval.py --url "https://www.youtube.com/watch?v=VIDEO_ID" \
    --title "Topic: Limits and Continuity - Definition and properties of limits" \
    --version version1
  ```

- **Outputs**:
  - Per-persona JSON: `eval_results/<topic>/<video_id>/<version>/<timestamp>_<source>_<i>.json`
  - CSV summary: `<timestamp>_summary.csv`
  - Consistency report: `<timestamp>_consistency_report.json`

---

### `phase_2/eval_copy.py`

- **Purpose**:  
  Same audit as `eval.py` but supports **local MP4 files** and **custom topic/persona**.

- **Video input** (choose one):
  - `--url` — YouTube URL
  - `--video` / `-v` — Local MP4 path

- **Persona input** (choose one):
  - `--persona "description string"` — Single persona from string
  - `--persona-file` / `-p` — JSON file with personas
  - `--persona-csv` — CSV (default, matched by `--topic`)

- **Example**:
  ```bash
  # Local video + custom persona string
  python phase_2/eval_copy.py -v my_lecture.mp4 -t "Topic: Chemistry of Life" \
    --persona "The student is a quick learner with strong math background."

  # Local video + persona JSON file
  python phase_2/eval_copy.py -v video.mp4 -t "My Topic" -p example_custom_personas.json
  ```

---

### `phase_2/batch_audit_processor.py`

- **Purpose**:  
  Use **Gemini API** to process multiple videos concurrently with async downloads.

- **What it does**:
  - Reads `input_videos.json` in `phase_2/`.
  - For each video: downloads (async), runs Agent 1 → Agent 2 → Agent 3 per persona.
  - Processes multiple videos in parallel (controlled by `MAX_CONCURRENT`).
  - Saves results to `eval_results/concurrent_YYYYMMDD_HHMMSS/`.

- **Requirements**:
  - Packages:
    ```bash
    pip install google-genai yt-dlp
    ```
  - `export GEMINI_API_KEY="YOUR_API_KEY"`
  - `phase_2/prompts/` with `agent1_prompt.md`, `agent2_prompt.md`, `subjective_prompt.md`
  - `phase_2/input_videos.json` (see `input_videos_example.json` for format)

- **Input format** (`input_videos.json`):
  ```json
  [
    {
      "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "title": "Topic: Chemistry of Life - Structure of water and hydrogen bonding",
      "personas": [
        "Education Level: University | Learning Motivation: Research papers | Timeline Urgency: Urgent",
        "Preferred Explanation Style: Intuition | Focus Level: Medium"
      ]
    }
  ]
  ```

- **Run** (from `phase_2/`):
  ```bash
  cd phase_2

  # Create input_videos.json (or copy from input_videos_example.json)
  cp input_videos_example.json input_videos.json
  # Edit input_videos.json with your videos and personas

  # Optional: set max concurrent tasks (default 3)
  export MAX_CONCURRENT=5

  python batch_audit_processor.py
  ```

- **Outputs**:
  - Directory: `eval_results/concurrent_YYYYMMDD_HHMMSS/`
  - Per-task JSON files
  - CSV summary: `concurrent_summary_YYYYMMDD_HHMMSS.csv`

---

More details for `phase_1` and additional tooling can be added later as the pipeline stabilizes.

