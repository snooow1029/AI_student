## AI student

This repo is organized into two main phases:

- **phase_1**: earlier experiments and text evaluation pipeline (legacy, not documented here yet).
- **phase_2**: YouTube data collection and Gemini-based video evaluation.

Below are the two main scripts currently used in **phase_2**.

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
  Run a Gemini (Google Gen AI) *diagnostic-to-remediation* audit on downloaded videos for a given student persona.

- **What it does**:
  - Scans `phase_2/data/<theme>/*.mp4` and uploads each video to the Gemini API.
  - Prompts a VLM model with:
    - The video file.
    - A rich system + user prompt describing:
      - Student persona (from `personas.jsonl`).
      - Evaluation rubrics (accuracy, logic, adaptability, engagement).
  - Saves per-video JSON reports to `phase_2/eval_results/`.

- **Requirements**:
  - Python 3
  - `google-genai` Python SDK:
    ```bash
    pip install google-genai
    ```
  - Gemini API key:
    ```bash
    export GEMINI_API_KEY="YOUR_API_KEY"
    # or
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```
  - Personas file at project root: `personas.jsonl`  
    (each line is a JSON object with fields like `description` and `category`).

- **Basic usage** (from `phase_2/`):
  ```bash
  cd phase_2

  # Evaluate the first 2 chemistry videos using persona index 3
  python eval.py --personas ../personas.jsonl --persona-index 3 -n 2
  ```

- **Outputs**:
  - Per-video report:  
    `phase_2/eval_results/<theme>_<video_title>.json`
  - Summary of all runs in the batch:  
    `phase_2/eval_results/summary.json`

More details for `phase_1` and additional tooling can be added later as the pipeline stabilizes.

