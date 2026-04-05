#!/usr/bin/env python3
"""
Streamlit Human-Eval Interface for Educational Video Assessment.
Humans use the same per-flag scale as automated eval (1, 0, -1, -2, -3); scores follow
batch_audit_processor (base 4.0, bonus 1/n_fields toward 5, clip [1, 5]).
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import os

# Configure page to wide mode (title updated on first run)
st.set_page_config(
    page_title="Human Video Evaluation",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Allow selectbox dropdown options to wrap instead of truncating
st.markdown("""
<style>
/* Dropdown list items: wrap text, no truncation */
[data-baseweb="select"] li,
[data-baseweb="menu"] li,
[data-baseweb="popover"] li {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    line-height: 1.4 !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}
/* Selected value in the box itself */
[data-baseweb="select"] [data-testid="stSelectbox"] div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
</style>
""", unsafe_allow_html=True)

# Constants (use resolve() for absolute paths - works regardless of streamlit cwd)
BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "phase_2"
VIDEO_POOL_JSON = RESULTS_DIR / "eval_video_pool.json"
HUMAN_EVAL_CSV = RESULTS_DIR / "human_eval_detailed_results.csv"
ASSIGNMENTS_JSON  = RESULTS_DIR / "annotator_assignments.json"
PILOT_CONFIG_JSON = RESULTS_DIR / "eval_pilot_config.json"
ATTENTION_CHECKS_JSON = RESULTS_DIR / "eval_attention_checks.json"
EXAMPLE_VIDEOS_JSON = RESULTS_DIR / "eval_example_videos.json"
MAX_VIDEOS_PER_ANNOTATOR = 5
N_CONTENT_VIDEOS = 4  # 4 regular + 1 attention check = 5 total

# Session state initialization
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'lang' not in st.session_state:
    st.session_state.lang = 'en'  # 'en' or 'ch'

# ==============================================================================
# TRANSLATIONS (UI only; data stored in English)
# ==============================================================================
TRANSLATIONS = {
    'en': {
        'page_title': "Human Video Evaluation (Deduction Mode)",
        'login_title': "🎓 Human Video Evaluation (Deduction Mode)",
        'enter_name': "Enter Evaluator Name",
        'start': "Start",
        'user': "User",
        'video_index': "Video Index",
        'current': "Current",
        'no_data': "No data found.",
        'ai_audit': "ℹ️ AI Audit Log Summary",
        'ai_audit_caption': "Detailed JSON would be loaded here in full version",
        'eval_form': "📝 Evaluation Form",
        'obj_quality': "1. Objective Quality (Accuracy & Logic)",
        'obj_caption': "Apply to the video content regardless of persona.",
        'pedagogical': "Pedagogical Depth",
        'scaffolding_failure': "Scaffolding Failure: Formula / Logic Leap",
        'scaffolding_failure_help': "Formulas with no 'why', AND/OR derivation steps skipped without justification. e.g. E=mc² stated without mass-energy intuition; or 'therefore the series converges' with no convergence test shown.",
        'pure_calc': "Pure Calculation Bias",
        'pure_calc_help': "Video is mostly worked examples with minimal conceptual explanation. e.g. 10 integration problems solved back-to-back, with only one sentence of theory at the start.",
        'completeness': "Completeness",
        'content_completeness': "Content Completeness",
        'content_completeness_help': "Does the video cover all topics its title implies? e.g. A 'Trigonometry' video skipping cosine and tangent entirely, or a 3-min video on a topic that clearly needs 20+ min.",
        'explanatory_depth': "Explanatory Depth",
        'explanatory_depth_help': "For topics that ARE present, how deep is the treatment vs. what the title promises? e.g. A 'Derivation of X' video that just states the result without showing any derivation steps.",
        'accuracy_checks': "Accuracy Checks",
        'title_mismatch': "Title / Depth Mismatch",
        'title_mismatch_help': "Video delivers something substantially different from the title — in topic OR depth. e.g. Title says 'Deriving X' but only explains the result; or title says 'Understanding X' but content is just plug-and-chug.",
        'visual_alignment': "Visual Alignment",
        'visual_alignment_help': "Slides and audio are out of sync or contradictory. e.g. Narration explains vector addition while the slide shows an unrelated scalar equation.",
        'error_counts': "Error Counts",
        'critical_errors': "Critical Fact Errors",
        'minor_slips': "Minor Slips",
        'logic_checks': "Logic Checks",
        'causal_inconsistencies': "Causal Inconsistencies",
        'causal_inconsistencies_help': "Count of contradictory cause-effect claims. e.g. First saying 'higher resistance means more current', then later 'higher resistance means less current' — without clarifying the context.",
        'calc_score': "🧮 Calculated Score: **Accuracy: {acc}** | **Logic: {log}**",
        'subj_exp': "2. Subjective Experience (Per Persona)",
        'persona': "Persona",
        'student_profile': "👤 **Student Profile:**",
        'adaptability_flags': "#### 🧠 Adaptability Flags (Barriers)",
        'jargon': "1. Jargon Overload",
        'jargon_help': "Terms used without definition that this persona wouldn't know. e.g. Using 'eigenvalue' with no explanation for a high-school student, or 'gradient descent' for a non-ML beginner.",
        'prereq_gap': "2. Prerequisite Gap",
        'prereq_gap_help': "Content jumps ahead of what this persona has learned. e.g. Integrating by parts before introducing integration, or referencing the chain rule mid-derivation without prior coverage.",
        'pacing': "3. Pacing Mismatch",
        'pacing_help': "Speed doesn't match this persona's needs. e.g. Spending 2 seconds on a multi-step derivation for a slow learner, or reading every word off the slide aloud for an advanced viewer.",
        'illegible': "4. Illegible Text",
        'illegible_help': "Text on screen is hard to read. e.g. Light grey formula on white background, 8pt font in a corner, or blurry handwriting that can't be zoomed.",
        'scaffolding': "5. Missing Scaffolding",
        'scaffolding_help': "No examples, analogies, or worked walkthroughs to support this persona. e.g. An 'examples-first' learner gets only abstract definitions with no numerical walkthrough.",
        'ineffective_visual': "6. Ineffective Visual Representation",
        'ineffective_visual_help': "A static or decorative image is used where a diagram, animation, or graph would actually teach. e.g. Explaining projectile motion with a stock photo of a ball instead of a trajectory arc.",
        'engagement_flags': "#### ⚡ Engagement Flags (Motivation)",
        'monotone': "7. Monotone Audio",
        'monotone_help': "Voice is flat, robotic, or TTS-like. e.g. Every sentence delivered at the same pitch and speed, no emphasis on key terms, or a synthetic voice with no inflection.",
        'ai_fatigue': "8. AI Fatigue (visuals)",
        'ai_fatigue_help': "Visuals look cheap, generic, or AI-generated. e.g. Stock-photo-style AI art people smiling at laptops, identical gradient backgrounds on every slide, or clip-art-style icons. (Voice/TTS quality → use Monotone instead.)",
        'clutter': "9. Visual Clutter",
        'clutter_help': "Slide is too dense to process while listening. e.g. A slide with 150 words of bullet points, 3 overlapping diagrams, and 4 different font sizes all at once.",
        'disconnect': "10. AV Disconnect",
        'disconnect_help': "What's on screen doesn't match what's being said. e.g. Narration explaining Step 3 while the slide still shows Step 1, or audio describing a force diagram while the slide shows an equation.",
        'decorative_eye_candy': "11. Decorative Eye-Candy",
        'decorative_eye_candy_help': "Flashy animations or visuals with no instructional value. e.g. A 5-second zoom-in transition between slides, spinning 3D logos, or particle effects that serve no explanatory purpose.",
        'subj_calc': "🧮 Calculated Score: **Adaptability: {adt}** | **Engagement: {eng}**",
        'optional_comments': "Optional Comments",
        'save_evals': "💾 Save All Evaluations",
        'saved_toast': "✅ Evaluation Saved!",
        'save_incomplete': "Please select all metrics before saving. ({n} fields not yet rated)",
        'rating_scale_caption': "📝 Same scale as automated pipeline. Use the segmented control: **left = −3 (worst)** → **right = +1 (best)**.",
        'scale_legend': "−3 Severe · −2 Moderate · −1 Minor · 0 Meets · +1 Beyond",
        'scale_rubric_title': "📖 What each level means",
        'scale_rubric_md': """
### General rubric (most flags: teaching depth, alignment, jargon, pacing, scaffolding, monotone, disconnect, etc.)

| Level | Meaning |
|------:|---------|
| **+1** | **Beyond expectation** — Unusually strong on this criterion; **no deduction**. |
| **0** | **Meets expectation** — Fine for this criterion; **no deduction**. |
| **−1** | **Minor** — Noticeable issue but still tolerable / workable. |
| **−2** | **Moderate** — Clear problem; learning is **significantly** harder. |
| **−3** | **Severe** — **Blocking** or fundamentally fails what this flag checks. |

### Frequency-style rubric (use for **Illegible text**, **Visual clutter**, **Ineffective visuals**, **Decorative eye-candy**)

| Level | Meaning |
|------:|---------|
| **+1** | No problematic instances and **clearly exemplary** (e.g. legibility or layout). |
| **0** | No issues; meets expectations. |
| **−1** | **One** distinct slide/instance with the problem. |
| **−2** | **Two** distinct slides/instances. |
| **−3** | **Three or more** instances, **or** the issue is pervasive across the video. |

### How **+1** affects the **computed score (bonus toward 5)**

- **Objective (Accuracy / Logic):** every severity slider can contribute a **+1** count (plus error **counts** are never used for bonus — they only subtract).
- **Adaptability:** **All six** adaptability sliders count a **+1** toward bonus (each adds **1/6** of the 4→5 band, before headroom cap): **Jargon**, **Prerequisite gap**, **Pacing**, **Illegible text**, **Missing scaffolding**, **Ineffective visuals**.
- **Engagement:** **All five** engagement sliders count a **+1** toward bonus (each adds **1/5**): **Monotone** (voice/TTS delivery), **AI fatigue (visuals only)**, **Clutter**, **AV disconnect**, **Decorative eye-candy**.
""",
        'scale': {1: "Beyond", 0: "Meets", -1: "Minor", -2: "Moderate", -3: "Severe"},
        'tab_objective': "📐 Objective",
        'info_overload': "Information Overload Segments",
        'info_overload_help': "Count of segments where too much is crammed in at once. e.g. A slide listing 8 formulas all explained back-to-back, or 5 new definitions introduced in 30 seconds.",
        # Per-criteria (+1 / 0 / −1 / −2 / −3) — rubric aligned with agent prompts
        'scores_scaffolding': "+1: Every formula motivated + derivations step-complete | 0: OK | −1…−3: Missing why / skipped steps → blocking",
        'scores_p_calc': "+1: Strong balance theory/examples | 0: OK | −1…−3: Drift toward pure calculation",
        'scores_content_completeness': "+1: Richer than title implies | 0: OK | −1: minor gap | −2: core absent | −3: multiple core absent; cap 1.0",
        'scores_explanatory_depth': "+1: Depth clearly above typical | 0: OK | −1…−3: Surface treatment → entirely procedural",
        'scores_t_mismatch': "+1: Exceptional alignment | 0: OK | −1…−3: Drift → misleading vs title",
        'scores_v_align': "+1: Visuals strongly support audio | 0: OK | −1…−3: Misalignment → contradict",
        'scores_jargon': "+1: Ideal for persona | 0: OK | −1…−3: Undefined terms → blocking",
        'scores_prereq': "+1: Prerequisites well placed | 0: OK | −1…−3: Gap → cannot follow",
        'scores_pacing': "+1: Ideal pace for persona | 0: OK | −1…−3: Mismatch → unusable",
        'scores_illegible': "+1: Exemplary legibility | 0: OK | −1: 1 bad slide | −2: 2 | −3: 3+ or pervasive",
        'scores_scaffold': "+1: Rich scaffolding for preference | 0: OK | −1…−3: Missing support",
        'scores_monotone': "+1: Engaging delivery | 0: OK | −1…−3: Flat → robotic / stop watching",
        'scores_ai_fatigue': "+1: Authentic visuals | 0: OK | −1…−3: Visual AI-slop → off-putting (not voice/TTS)",
        'scores_clutter': "+1: Clean layout | 0: OK | −1: 1 cluttered slide | −2: 2 | −3: 3+",
        'scores_disconnect': "+1: AV tightly coupled | 0: OK | −1…−3: Often off → disconnected",
        'scores_ineffective_visual': "+1: Visuals match spatial/dynamic needs | 0: OK | −1: 1 weak segment | −2: 2 | −3: 3+ or pervasive",
        'scores_decorative_eye_candy': "+1: Motion encodes ideas / no fluff | 0: OK | −1: 1 seductive-detail segment | −2: 2 | −3: 3+",
        # Instructions page
        'instructions_title': "📖 Annotator Instructions",
        'instructions_proceed_btn': "✅ I've read the instructions — Start",
        'instructions_task_md': """
## What you will do
You will watch short educational videos and rate their quality on a set of structured criteria. Your ratings will be used to study the quality of AI-generated math/science teaching content.

- You will annotate **5 videos** in total. A subset will be used for quality verification.
- Each video has **3 student personas**; for subjective metrics, rate from each persona's perspective in the corresponding tab.
- **Objective metrics** (Sections 1–4 below) apply to the video content itself.
- **Subjective metrics** (Sections 5–6) depend on the assigned student persona.

## Rating scale
| Level | Meaning |
|------:|---------|
| **+1** | **Beyond expectation** — this aspect is genuinely stronger than typical for the topic and runtime. Reserve for standout cases. |
| **0** | **Meets expectation** — no issue; no deduction. |
| **−1** | **Minor** — noticeable but tolerable; learner can still follow. |
| **−2** | **Moderate** — clear problem; learning is meaningfully impaired. |
| **−3** | **Severe** — blocking issue; content fails on this criterion. |

Count fields (error counts, information overload) use integers ≥ 0.
""",
        'instructions_obj_header': "### 📐 Objective Metrics",
        'instructions_subj_header': "### 🧠 Subjective Metrics (by Persona)",
        'instructions_metric_levels': "**Levels:**",
        'instructions_rules_header': "### ✅ Annotation Rules — Please Read Carefully",
        'instructions_examples_header': "### 🎬 Calibration Examples",
        'instructions_example_ratings': "**Reference ratings:**",
        'instructions_example_comment': "**Why these ratings:**",
        # Pilot & assignment
        'pilot_banner': "🎯 Pilot Test — Before You Begin",
        'pilot_intro': "Please evaluate the video below. We will compare your ratings with our expert reference (tolerance ±1 per metric). You need **≥{pct}%** agreement to proceed. Attempts used: {used}/{max}.",
        'pilot_pass': "✅ Pilot passed! Your calibration is good. Loading your assigned videos…",
        'pilot_fail': "❌ {n_off} metric(s) were off by more than ±1. Please review the scale guide and try again.",
        'pilot_fail_final': "You have used all {max} pilot attempts. Please contact the research team.",
        'pilot_attempts_left': "{n} attempt(s) remaining",
        'pilot_submit_btn': "💾 Submit Pilot",
        'pilot_result_header': "📊 Pilot Result — Reference Comparison",
        'pilot_result_pass_msg': "✅ **Passed!** Your ratings align with the reference. Review the comparison below, then continue.",
        'pilot_result_fail_msg': "❌ **Not quite** — {n_off} metric(s) were off by more than ±1. Study the reference below and try again.",
        'pilot_result_fail_final_msg': "❌ **Maximum attempts reached.** Please contact the research team.",
        'pilot_result_attempts_left': "Attempts remaining: {n}",
        'pilot_metric_col': "Metric",
        'pilot_your_col': "Your Rating",
        'pilot_ref_col': "Reference",
        'pilot_match_col': "Match",
        'pilot_continue_btn': "➡️ Continue to Evaluation",
        'pilot_retry_btn': "🔄 Try Again",
        'assigned_banner': "📋 Your assigned videos ({done}/{total} completed)",
        'all_done': "🎉 You have completed all {n} assigned videos! Please contact the recruiter with your account name — we will pay you after verifying your annotation is valid (pass the attention check and complete record).",
    },
    'ch': {
        'page_title': "教學影片人工評測（扣分模式）",
        'login_title': "🎓 教學影片人工評測（扣分模式）",
        'enter_name': "輸入評測者姓名",
        'start': "開始",
        'user': "使用者",
        'video_index': "影片索引",
        'current': "目前",
        'no_data': "找不到資料。",
        'ai_audit': "ℹ️ AI 稽核摘要",
        'ai_audit_caption': "完整版會在此載入詳細 JSON",
        'eval_form': "📝 評測表單",
        'obj_quality': "1. 客觀品質（準確性與邏輯）",
        'obj_caption': "適用於影片內容，與學習者角色無關。",
        'pedagogical': "教學深度",
        'scaffolding_failure': "鷹架缺失：公式 / 邏輯跳躍",
        'scaffolding_failure_help': "公式沒有「為什麼」，以及／或推導步驟無說明就跳過。例：E=mc² 直接給出無質能直覺；或「因此級數收斂」卻沒有展示任何收斂判斷。",
        'pure_calc': "純計算偏重",
        'pure_calc_help': "影片以例題演算為主，概念說明極少。例：連續解 10 道積分題，開頭只有一句理論說明。",
        'completeness': "完整性",
        'content_completeness': "內容完整性",
        'content_completeness_help': "影片是否涵蓋標題所隱含的所有主題？例：「三角函數」影片只講 sin，完全跳過 cos 和 tan；或一個需要 20 分鐘的主題只拍了 3 分鐘。",
        'explanatory_depth': "解釋深度",
        'explanatory_depth_help': "對於已涵蓋的主題，深度是否符合標題承諾？例：「推導 X」影片只陳述結果，完全沒有展示任何推導步驟。",
        'accuracy_checks': "準確性檢查",
        'title_mismatch': "標題／深度不符",
        'title_mismatch_help': "影片與標題的差距——主題或深度。例：標題「推導 X」但只解釋結果；或標題「理解 X」但只是代公式。",
        'visual_alignment': "視覺對齊",
        'visual_alignment_help': "投影片與口述不同步或相互矛盾。例：口述在講向量加法，投影片卻顯示一個不相關的純量方程式。",
        'error_counts': "錯誤計數",
        'critical_errors': "重大事實錯誤",
        'minor_slips': "輕微疏漏",
        'logic_checks': "邏輯檢查",
        'causal_inconsistencies': "因果不一致",
        'causal_inconsistencies_help': "因果關係互相矛盾的次數。例：先說「電阻越大電流越大」，後來又說「電阻越大電流越小」，沒有說明前後語境的差異。",
        'calc_score': "🧮 計算分數：**準確性：{acc}** | **邏輯：{log}**",
        'subj_exp': "2. 主觀體驗（依角色）",
        'persona': "角色",
        'student_profile': "👤 **學生：**",
        'adaptability_flags': "####  適應性指標（障礙）",
        'jargon': "1. 術語過載",
        'jargon_help': "對此角色未加定義就使用的術語。例：對高中生直接說「特徵值」，或對非 ML 背景者說「梯度下降」。",
        'prereq_gap': "2. 先備知識落差",
        'prereq_gap_help': "內容跳過此角色還沒學到的東西。例：在介紹積分之前就做分部積分，或推導中途引用連鎖律但從未教過。",
        'pacing': "3. 節奏不匹配",
        'pacing_help': "速度不適合此角色。例：對慢速學習者用 2 秒帶過多步驟推導，或對進階學習者逐字唸投影片。",
        'illegible': "4. 文字難以辨識",
        'illegible_help': "螢幕上的文字難以閱讀。例：白底淺灰公式、角落 8pt 字、無法放大的模糊手寫。",
        'scaffolding': "5. 缺乏鷹架",
        'scaffolding_help': "缺乏此角色需要的範例、類比或引導。例：偏好先看例子的學習者只得到抽象定義，沒有任何數值示範。",
        'ineffective_visual': "6. 無效視覺表徵",
        'ineffective_visual_help': "應該用圖表、動畫或示意圖的地方卻用靜態或裝飾性畫面。例：解說拋體運動時只放一張球的示意照，沒有軌跡弧線。",
        'engagement_flags': "#### ⚡ 投入度指標（動機）",
        'monotone': "7. 單調語音",
        'monotone_help': "聲音平板、機械化或像 TTS。例：每句話音調相同、關鍵詞無強調，或合成語音毫無抑揚頓挫。",
        'ai_fatigue': "8. AI 疲勞感（畫面）",
        'ai_fatigue_help': "畫面看起來廉價、套版或 AI 生成。例：每張投影片都是微笑對著電腦的 AI 人物圖、相同漸層背景、clipart 圖示。（語音／TTS 品質問題請用「單調語音」。）",
        'clutter': "9. 視覺雜亂",
        'clutter_help': "投影片太密集、邊聽邊看很難消化。例：一張投影片有 150 字的條列式、3 個重疊圖表、4 種不同字體大小。",
        'disconnect': "10. 影音脫節",
        'disconnect_help': "畫面和口述不同步或互相矛盾。例：講到第三步時投影片還停在第一步，或口述在解釋力的示意圖但畫面顯示方程式。",
        'decorative_eye_candy': "11. 裝飾性花俏畫面",
        'decorative_eye_candy_help': "有炫目動畫或視覺效果但無教學價值。例：5 秒鐘的換頁縮放特效、旋轉 3D Logo、或粒子特效。",
        'subj_calc': "🧮 計算分數：**適應性：{adt}** | **投入度：{eng}**",
        'optional_comments': "選填意見",
        'save_evals': "💾 儲存所有評測",
        'saved_toast': "✅ 評測已儲存！",
        'save_incomplete': "請選擇所有指標後再儲存。（{n} 項尚未評分）",
        'rating_scale_caption': "📝 與自動評測同一尺度。分段選項：**左邊 −3（最差）** → **右邊 +1（最好）**。",
        'scale_legend': "−3 嚴重 · −2 中度 · −1 輕微 · 0 符合 · +1 超出",
        'scale_rubric_title': "📖 各分數代表什麼",
        'scale_rubric_md': """
### 一般項目（多數旗標：教學深度、對齊、術語、節奏、鷹架、單調、影音脫節等）

| 分數 | 意義 |
|------:|------|
| **+1** | **超出預期** — 在該向度上**特別突出**；**不扣分**。 |
| **0** | **符合預期** — 沒問題；**不扣分**。 |
| **−1** | **輕微** — 有感，但還**勉強能跟**。 |
| **−2** | **中度** — 明顯問題，學習**明顯變難**。 |
| **−3** | **嚴重** — **擋路級**或根本不符合該項要檢查的內容。 |

### 頻率型項目（**文字難讀**、**畫面雜亂**、**無效視覺**、**裝飾花俏** 請用這套）

| 分數 | 意義 |
|------:|------|
| **+1** | 沒有問題案例，且**明顯是典範**（易讀或版面）。 |
| **0** | 沒問題；符合預期。 |
| **−1** | **1** 個明確投影片／片段有問題。 |
| **−2** | **2** 個。 |
| **−3** | **3 個以上**，或**整片**都是這個問題。 |

### 計算分數時，哪些 **+1** 會算進「往 5 分加分」

- **客觀（準確性／邏輯）：** 每個嚴重度滑桿的 **+1** 都會列入加分計數；**錯誤次數**只扣分、**不會**當成 +1。
- **適應性：** **六項**適應性滑桿的 **+1** 都列入加分（每個貢獻 **1/6** 的 4→5 加分帶）：**術語過載、先備落差、節奏、文字難讀、缺乏鷹架、無效視覺表徵**。
- **投入度：** **五項**投入度滑桿的 **+1** 都列入加分（每個 **1/5**）：**單調語音（含 TTS 語感）、AI 疲勞（僅畫面）、畫面雜亂、影音脫節、裝飾性花俏畫面**。
""",
        'scale': {1: "超出預期", 0: "符合", -1: "輕微", -2: "中度", -3: "嚴重"},
        'tab_objective': "📐 客觀",
        'info_overload': "資訊過載片段",
        'info_overload_help': "一次塞入太多資訊的片段數。例：一張投影片同時列出 8 條公式並全部講解，或 30 秒內介紹 5 個新定義。",
        'scores_scaffolding': "+1: 每個公式都有動機 + 推導步驟完整 | 0: 可 | −1…−3: 缺「為什麼」／跳步→阻礙",
        'scores_p_calc': "+1: 理論／例題平衡佳 | 0: 可 | −1…−3: 偏純計算",
        'scores_content_completeness': "+1: 比標題更豐富 | 0: 可 | −1: 小缺 | −2: 核心缺席 | −3: 多項核心缺席；cap 1.0",
        'scores_explanatory_depth': "+1: 深度明顯超出一般 | 0: 可 | −1…−3: 表面處理→完全程序化",
        'scores_t_mismatch': "+1: 與標題高度一致 | 0: 可 | −1…−3: 偏離→誤導",
        'scores_v_align': "+1: 畫面強化講解 | 0: 可 | −1…−3: 不合→干擾",
        'scores_jargon': "+1: 對此角色恰到好處 | 0: 可 | −1…−3: 術語問題→阻礙",
        'scores_prereq': "+1: 先備處理極佳 | 0: 可 | −1…−3: 落差→跟不上",
        'scores_pacing': "+1: 節奏極適合此角色 | 0: 可 | −1…−3: 不匹配→難用",
        'scores_illegible': "+1: 易讀性典範 | 0: 可 | −1: 1 張有問題 | −2: 2 張 | −3: 3+ 或整片",
        'scores_scaffold': "+1: 鷹架豐富符合偏好 | 0: 可 | −1…−3: 缺支持",
        'scores_monotone': "+1: 表達有吸引力 | 0: 可 | −1…−3: 平淡→難以看下去",
        'scores_ai_fatigue': "+1: 視覺真實可信 | 0: 可 | −1…−3: 畫面 AI 廉價感（不含語音/TTS）",
        'scores_clutter': "+1: 版面乾淨 | 0: 可 | −1: 1 張雜亂 | −2: 2 張 | −3: 3+",
        'scores_disconnect': "+1: 音畫緊密配合 | 0: 可 | −1…−3: 常脫節",
        'scores_ineffective_visual': "+1: 視覺符合空間／動態需求 | 0: 可 | −1: 1 段偏弱 | −2: 2 段 | −3: 3+ 或整片",
        'scores_decorative_eye_candy': "+1: 動畫承載概念／無純裝飾 | 0: 可 | −1: 1 段誘惑性細節 | −2: 2 | −3: 3+",
        # Instructions page
        'instructions_title': "📖 標注說明",
        'instructions_proceed_btn': "✅ 我已閱讀說明 — 開始",
        'instructions_task_md': """
## 您的任務
觀看簡短的教學影片，並依照結構化標準評估其品質。您的評分將用於研究 AI 生成數理教學內容的品質。

- 您總共需要標注 **5 部影片**。部分影片將用於品質驗證。
- 每部影片搭配 **3 個學生角色**；主觀指標請在對應的分頁中，分別從各角色的視角評分。
- **客觀指標**（以下第 1–4 節）針對影片內容本身評分。
- **主觀指標**（第 5–6 節）依分配的學生角色而定。

## 評分量表
| 分數 | 意義 |
|------:|------|
| **+1** | **超出預期** — 此向度明顯優於同主題同時長的一般影片。請保留給真正突出的案例。 |
| **0** | **符合預期** — 無問題，不扣分。 |
| **−1** | **輕微** — 有感但可接受，學習者仍大致能跟上。 |
| **−2** | **中度** — 明顯問題，學習體驗受到明顯影響。 |
| **−3** | **嚴重** — 阻礙級問題，影片在此向度完全不符預期。 |

計數欄位（錯誤次數、資訊過載片段）請填整數 ≥ 0。
""",
        'instructions_obj_header': "### 📐 客觀指標",
        'instructions_subj_header': "### 🧠 主觀指標（依學生角色）",
        'instructions_metric_levels': "**各分數說明：**",
        'instructions_rules_header': "### ✅ 標注規則 — 請仔細閱讀",
        'instructions_examples_header': "### 🎬 校準範例",
        'instructions_example_ratings': "**參考評分：**",
        'instructions_example_comment': "**這樣評的原因：**",
        # Pilot & assignment
        'pilot_banner': "🎯 前導測試 — 開始前",
        'pilot_intro': "請評測以下影片。我們會將您的評分與專家參考答案對比（每項容差 ±1）。需達到 **≥{pct}%** 一致才能繼續。已用次數：{used}/{max}。",
        'pilot_pass': "✅ 前導測試通過！您的校準良好，正在載入您分配的影片…",
        'pilot_fail': "❌ {n_off} 項指標偏差超過 ±1。請重新閱讀量表說明後重試。",
        'pilot_fail_final': "您已用完全部 {max} 次機會。請聯繫研究團隊。",
        'pilot_attempts_left': "剩餘 {n} 次機會",
        'pilot_submit_btn': "💾 提交前導測試",
        'pilot_result_header': "📊 前導測試結果 — 參考答案對照",
        'pilot_result_pass_msg': "✅ **通過！** 您的評分與參考答案一致。請對照以下比較後繼續。",
        'pilot_result_fail_msg': "❌ **未達標** — {n_off} 項指標偏差超過 ±1。請研讀參考答案後重試。",
        'pilot_result_fail_final_msg': "❌ **已用完全部機會。** 請聯繫研究團隊。",
        'pilot_result_attempts_left': "剩餘機會：{n}",
        'pilot_metric_col': "指標",
        'pilot_your_col': "您的評分",
        'pilot_ref_col': "參考答案",
        'pilot_match_col': "符合",
        'pilot_continue_btn': "➡️ 繼續正式評測",
        'pilot_retry_btn': "🔄 重新作答",
        'assigned_banner': "📋 您的分配影片（已完成 {done}/{total}）",
        'all_done': "🎉 您已完成全部 {n} 部分配影片！請以您的帳號名稱聯繫招募人員——我們在確認您的標注有效（通過 attention check 且紀錄完整）後將完成付款。",
    }
}

# ==============================================================================
# PER-FLAG LEVEL DESCRIPTIONS (users pick the most fitting description)
# ==============================================================================
FLAG_DESCRIPTIONS = {
    'en': {
        # --- Objective: Accuracy & Logic (shared flags) ---
        'scaffolding_failure': {
            1: "Every formula motivated + derivations step-complete; scaffolding clearly above typical",
            0: "No issue",
            -1: "Skips 'why' for 1 key concept, OR 1–2 unjustified derivation jumps",
            -2: "Multiple key formulas lack rationale, OR multiple critical steps skipped",
            -3: "Entire video: formulas as facts with zero scaffolding, OR derivations riddled with unexplained leaps",
        },
        'pure_calc_bias': {
            1: "Calculations subordinate to a visible conceptual spine; concept-first feel",
            0: "No issue",
            -1: "Theory exists but brief (~60% calc)",
            -2: "Heavily skewed (~75% calc, thin theory); cap 2.5",
            -3: "Almost pure calc (>85%); cap 2.5",
        },
        'content_completeness': {
            1: "Content is notably richer than the title implies; goes meaningfully beyond stated scope",
            0: "All implied topics present with adequate coverage",
            -1: "1 minor supporting concept missing, or content slightly thinner than implied",
            -2: "1 core concept absent, OR multiple supporting concepts missing, OR video noticeably too short",
            -3: "Multiple core concepts absent; video fails its stated scope; cap 1.0",
        },
        'explanatory_depth': {
            1: "Depth clearly above typical for this topic and runtime; sustained; non-skipped critical steps",
            0: "Depth appropriate for the title's promise; no issue",
            -1: "Some topics treated more shallowly than title implies; key steps occasionally rushed",
            -2: "Most topics 'mentioned' without explanation; title implies derivation but content is abbreviated",
            -3: "Title promises concept/derivation but delivery is entirely procedural/plug-and-chug",
        },
        'title_mismatch': {
            0: "No issue",
            -1: "Minor overpromise — title slightly exceeds what's delivered (topic or depth)",
            -2: "Clear mismatch — e.g. title says 'Derivation' but only shows formula; or 'Understanding X' but purely procedural",
            -3: "Fundamental mismatch — completely different topic, or title promises concept and video is entirely plug-and-chug",
        },
        'visual_alignment': {
            1: "Exceptional: graphics track spoken argument in real time, anticipate confusion",
            0: "High alignment (visuals directly clarify concepts)",
            -1: "Medium alignment (occasional misalignment)",
            -2: "Low alignment (decorative images during technical content, slides lag)",
            -3: "Severe misalignment (visuals actively contradict or distract)",
        },
        # --- Subjective: Adaptability ---
        'jargon': {
            0: "None; meets expectations",
            -1: "1 distinct instance of undefined jargon for this persona",
            -2: "2 distinct instances",
            -3: "3+ instances, or jargon is a constant style choice",
        },
        'prereq_gap': {
            1: "Prerequisites well placed; no gaps for this persona",
            0: "No deduction; meets expectations",
            -1: "A few steps skip light background; student can patch while watching",
            -2: "Several jumps assume knowledge persona lacks; must pause / look things up",
            -3: "Core steps incomprehensible without prior knowledge persona doesn't have",
        },
        'pacing': {
            1: "Ideal pace for this persona's speed + time combo",
            0: "No deduction; meets expectations",
            -1: "Occasionally too fast / slow; still finishes without major frustration",
            -2: "Often mismatched: frequently lost, must rewind, or time wasted",
            -3: "Unwatchable at this pace for this persona",
        },
        'illegible': {
            0: "None; meets expectations",
            -1: "1 slide with a clear legibility problem",
            -2: "2 distinct slides / moments",
            -3: "3+ or illegibility is the default style",
        },
        'scaffolding': {
            1: "Rich scaffolding matching persona preference",
            0: "No deduction; meets expectations",
            -1: "Mostly OK; one stretch feels under-explained for this preference",
            -2: "Major stretches missing preferred support (e.g. no examples for examples-first)",
            -3: "Opposite of need for long stretches — persona cannot learn as intended",
        },
        'ineffective_visual': {
            1: "Visuals match spatial / dynamic needs throughout",
            0: "None; meets expectations",
            -1: "1 slide / beat where static visual should be dynamic; audio still carries",
            -2: "2 such slides / beats; mental simulation becomes tiring",
            -3: "3+ or nearly all conceptual parts lack adequate visuals",
        },
        # --- Subjective: Engagement ---
        'monotone': {
            1: "Engaging delivery; voice drives attention",
            0: "No deduction; meets expectations",
            -1: "Somewhat flat or dry; still followable; mild urge to tune out",
            -2: "Drone-like or TTS chunking breaks immersion; rewind often needed",
            -3: "Would stop or skip due to voice; delivery is persistently soporific",
        },
        'ai_fatigue': {
            0: "None; meets expectations",
            -1: "1 slide / segment where visuals feel cheap / uncanny",
            -2: "2 such instances",
            -3: "3+ or dominant visual style is generic AI art end-to-end",
        },
        'clutter': {
            0: "None; meets expectations",
            -1: "1 slide clearly hard to scan while listening",
            -2: "2 such slides",
            -3: "3+ or clutter is the norm for most of the deck",
        },
        'disconnect': {
            1: "AV tightly coupled; visuals anticipate narration",
            0: "None; meets expectations",
            -1: "1 noticeable mismatch; meaning still recoverable from audio",
            -2: "2 mismatches, or 1 long stretch where visuals mislead",
            -3: "3+ or visuals repeatedly contradict the explanation",
        },
        'decorative_eye_candy': {
            0: "None; meets expectations",
            -1: "1 segment of flashy but empty spectacle",
            -2: "2 such segments",
            -3: "3+ or eye-candy replaces substance for serious learners",
        },
    },
    'ch': {
        # --- 客觀：準確性 & 邏輯 ---
        'scaffolding_failure': {
            1: "每個公式都有動機 + 推導步驟完整；鷹架明顯優於一般",
            0: "無問題",
            -1: "1 個關鍵概念跳過「為什麼」，或 1–2 個推導步驟無說明",
            -2: "多個關鍵公式缺理由，或多個關鍵步驟無說明就跳過",
            -3: "整部影片公式全無鋪陳，或推導充滿無法解釋的跳躍",
        },
        'pure_calc_bias': {
            1: "計算從屬於清晰的概念主軸；以概念為先的感覺",
            0: "無問題",
            -1: "有理論但簡短（≈60% 計算）",
            -2: "嚴重偏計算（≈75%，理論薄弱）；cap 2.5",
            -3: "幾乎純計算（>85%）；cap 2.5",
        },
        'content_completeness': {
            1: "內容遠比標題更豐富；明顯超出聲明範圍",
            0: "所有隱含主題均有充分涵蓋",
            -1: "缺 1 個次要概念，或內容略薄於標題所示",
            -2: "缺 1 個核心概念，或多個次要概念缺席，或影片明顯太短",
            -3: "多個核心概念缺席；影片無法達成其聲明範圍；cap 1.0",
        },
        'explanatory_depth': {
            1: "深度明顯優於同主題同時長的一般影片；所有涵蓋主題均維持高深度",
            0: "深度符合標題承諾；無問題",
            -1: "部分主題比標題暗示的更淺；關鍵步驟偶爾倉促帶過",
            -2: "多數主題僅「提及」無說明；或標題暗示推導但大量省略；整體流於表面",
            -3: "標題承諾概念／推導／理解，但實際完全程序化／代公式",
        },
        'title_mismatch': {
            0: "無問題",
            -1: "輕微落差——標題稍微超過實際內容（主題或深度）",
            -2: "明顯不符——如標題寫「推導」但只放公式；或「理解 X」但純粹代公式",
            -3: "根本不符——完全不同主題，或標題承諾概念但影片整個只是代公式",
        },
        'visual_alignment': {
            1: "傑出：畫面即時追蹤口述論點，預判混淆點",
            0: "高度對齊（畫面直接闡明概念）",
            -1: "中度對齊（偶爾不匹配）",
            -2: "低度對齊（技術內容時放裝飾圖、投影片落後口述）",
            -3: "嚴重不匹配（畫面主動矛盾或干擾音訊）",
        },
        # --- 主觀：適應性 ---
        'jargon': {
            0: "無問題；符合預期",
            -1: "1 個對此角色未定義的術語",
            -2: "2 個",
            -3: "3 個以上，或術語是全片的一貫風格",
        },
        'prereq_gap': {
            1: "先備知識安排得當；對此角色無缺口",
            0: "無扣分；符合預期",
            -1: "少數步驟跳過輕度背景；學生可邊看邊補",
            -2: "多處跳躍假設角色缺乏的知識；需暫停／查資料",
            -3: "核心步驟若無角色不具備的先備知識則無法理解",
        },
        'pacing': {
            1: "節奏完美契合此角色的速度 + 時間組合",
            0: "無扣分；符合預期",
            -1: "偶爾太快／太慢；仍能看完",
            -2: "經常不匹配：常迷失、需倒帶、或浪費時間",
            -3: "此角色完全無法適應此節奏",
        },
        'illegible': {
            0: "無問題；符合預期",
            -1: "1 張投影片有明確的可讀性問題",
            -2: "2 張",
            -3: "3 張以上，或難讀是預設風格",
        },
        'scaffolding': {
            1: "鷹架豐富且符合角色偏好",
            0: "無扣分；符合預期",
            -1: "大致可以；有一段對此偏好解釋不足",
            -2: "大段落缺乏偏好的支持（如需範例的角色卻無範例）",
            -3: "長時間與需求相反——角色無法照預期學習",
        },
        'ineffective_visual': {
            1: "全程視覺都符合空間／動態需求",
            0: "無問題；符合預期",
            -1: "1 張靜態畫面本應動態呈現；音訊仍能補救",
            -2: "2 處；心理模擬變得吃力",
            -3: "3 處以上或幾乎所有概念部分都缺乏適當視覺",
        },
        # --- 主觀：投入度 ---
        'monotone': {
            1: "表達有吸引力；聲音帶動注意力",
            0: "無扣分；符合預期",
            -1: "略平淡或乾燥；仍可跟上；輕微想分心",
            -2: "像念經或 TTS 斷句破壞沉浸；常需倒帶",
            -3: "會因聲音而停止或跳過；持續催眠感",
        },
        'ai_fatigue': {
            0: "無問題；符合預期",
            -1: "1 張畫面感覺廉價 / 不自然",
            -2: "2 處",
            -3: "3 處以上或主要視覺風格就是通用 AI 圖",
        },
        'clutter': {
            0: "無問題；符合預期",
            -1: "1 張投影片邊聽邊看明顯困難",
            -2: "2 張",
            -3: "3 張以上或雜亂是大部分投影片的常態",
        },
        'disconnect': {
            1: "音畫緊密配合；畫面預判口述",
            0: "無問題；符合預期",
            -1: "1 處明顯不匹配；仍可從音訊恢復意義",
            -2: "2 處不匹配，或 1 段長時間畫面誤導",
            -3: "3 處以上或畫面反覆與講解矛盾",
        },
        'decorative_eye_candy': {
            0: "無問題；符合預期",
            -1: "1 段華麗但空洞的畫面",
            -2: "2 段",
            -3: "3 段以上或花俏取代實質內容",
        },
    },
}


def t(key):
    """Get translated string for current language."""
    return TRANSLATIONS[st.session_state.lang].get(key, key)

# ==============================================================================
# SCORING LOGIC ENGINE (Aligned with batch_audit_processor.py)
# ==============================================================================

EVAL_SCHEMA_VERSION = 4

# Match batch_audit_processor: +1 anchors: (1) scaffolding_failure, (2) pure_calc_bias,
# (3) content_completeness, (4) explanatory_depth; accuracy also (6) visual_alignment.
N_BONUS_FIELDS_ACCURACY = 5
N_BONUS_FIELDS_LOGIC = 4
# Match batch: all adaptability / engagement sliders can contribute +1 toward 5.0 (1/N each; missing keys default 0).
N_BONUS_FIELDS_ADAPTABILITY = 4   # prereq, pacing, scaffolding, ineffective_visual (match batch_audit_processor)
N_BONUS_FIELDS_ENGAGEMENT = 3     # monotone, disconnect, visual_signaling (match batch_audit_processor)


def clip_score_1_5(score: float) -> float:
    if not isinstance(score, (int, float)):
        return 3.0
    return round(max(1.0, min(5.0, float(score))), 2)


def _apply_bonus_toward_five(score: float, num_plus_one: int, n_fields: int) -> float:
    if num_plus_one <= 0 or n_fields <= 0:
        return clip_score_1_5(score)
    s = float(score)
    headroom = max(0.0, 5.0 - s)
    raw_bonus = min(1.0, float(num_plus_one) / float(n_fields))
    bonus = min(headroom, raw_bonus)
    return clip_score_1_5(s + bonus)


def _count_plus_one_levels(*values) -> int:
    n = 0
    for v in values:
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)) and int(v) == 1:
            n += 1
    return n


def _sev_penalty_agent(level, p1=0.5, p2=1.0, p3=2.0):
    """1 = no penalty; 0 = none; -1/-2/-3 = tiers; legacy +2/+3 supported."""
    level = int(level) if isinstance(level, (int, float)) else 0
    if level == 0:
        return 0.0
    if level == 1:
        return 0.0
    if level > 1:
        idx = min(level, 3)
        return [0, p1, p2, p3][idx]
    idx = abs(level)
    return [0, p1, p2, p3][min(idx, 3)]


def _sev_idx(severity):
    if isinstance(severity, bool):
        return 2 if severity else 0
    if isinstance(severity, int):
        if severity == 1:
            return 0
        if severity == 0:
            return 0
        if severity < 0:
            return abs(severity)
        if severity >= 2:
            return min(severity, 3)
    return 0


def _calc_penalty_standard(severity):
    idx = _sev_idx(severity)
    return {0: 0, 1: 0.3, 2: 0.6, 3: 1.0}.get(idx, 1.0 if idx >= 3 else 0)


def _calc_penalty_monotone(severity):
    idx = _sev_idx(severity)
    return {0: 0, 1: 0.4, 2: 0.8, 3: 1.2}.get(idx, 1.2 if idx >= 3 else 0)


def calculate_accuracy(flags):
    """
    Matches batch_audit_processor._calculate_agent2_scores (base 4.0, bonus 1/n, clip).
    """
    accuracy = 4.0
    score_cap = 4.0
    fd = _sev_penalty_agent(flags.get("scaffolding_failure", 0), 0.5, 1.0, 1.5)
    pc = _sev_penalty_agent(flags.get("pure_calc_bias", 0), 0.3, 0.6, 1.0)
    accuracy -= fd + pc
    if abs(int(flags.get("pure_calc_bias", 0))) >= 2:
        score_cap = min(score_cap, 2.5)
    cc_level = int(flags.get("content_completeness", 0))
    if abs(cc_level) == 3:
        score_cap = min(score_cap, 1.0)
    cc = _sev_penalty_agent(cc_level, 0.5, 1.0, 1.5)
    ed = _sev_penalty_agent(flags.get("explanatory_depth", 0), 0.5, 1.5, 2.0)
    accuracy -= cc + ed
    tm = _sev_penalty_agent(flags.get("title_mismatch", 0), 0.5, 2, 4)
    va = _sev_penalty_agent(flags.get("visual_alignment", 0), 0.0, 0.5, 1.0)
    accuracy -= tm + va
    crit_errors = int(flags.get("critical_errors", 0))
    minor_slips = int(flags.get("minor_slips", 0))
    accuracy -= crit_errors * 0.3 + minor_slips * 0.2
    accuracy = round(min(score_cap, max(0.0, accuracy)), 2)
    n_bonus = _count_plus_one_levels(
        flags.get("scaffolding_failure", 0),
        flags.get("pure_calc_bias", 0),
        flags.get("content_completeness", 0),
        flags.get("explanatory_depth", 0),
        flags.get("visual_alignment", 0),
    )
    accuracy = _apply_bonus_toward_five(accuracy, n_bonus, N_BONUS_FIELDS_ACCURACY)
    return clip_score_1_5(accuracy), 0


def calculate_logic(flags):
    """Matches batch _calculate_agent2_scores logic arm."""
    logic = 4.0
    logic_cap = 4.0
    if int(flags.get("scaffolding_failure", 0)) <= -3:
        logic_cap = 2.0
    if abs(int(flags.get("pure_calc_bias", 0))) >= 2:
        logic_cap = min(logic_cap, 2.5)
    cc_level = int(flags.get("content_completeness", 0))
    if abs(cc_level) == 3:
        logic_cap = min(logic_cap, 1.0)
    fd = _sev_penalty_agent(flags.get("scaffolding_failure", 0), 0.5, 1.0, 1.5)
    pc = _sev_penalty_agent(flags.get("pure_calc_bias", 0), 0.3, 0.6, 1.0)
    cc = _sev_penalty_agent(cc_level, 0.5, 1.0, 1.5)
    ed = _sev_penalty_agent(flags.get("explanatory_depth", 0), 0.5, 1.5, 2.0)
    logic -= fd + pc + cc + ed
    ci = int(flags.get("causal_inconsistencies", 0))
    io = int(flags.get("information_overload", 0))
    logic -= ci * 0.4 + io * 0.2
    logic = round(min(logic_cap, max(0.0, logic)), 2)
    n_bonus = _count_plus_one_levels(
        flags.get("scaffolding_failure", 0),
        flags.get("pure_calc_bias", 0),
        flags.get("content_completeness", 0),
        flags.get("explanatory_depth", 0),
    )
    logic = _apply_bonus_toward_five(logic, n_bonus, N_BONUS_FIELDS_LOGIC)
    return clip_score_1_5(logic), 0


def calculate_adaptability(flags):
    """Illegible text (contrast_level): +1 = no penalty; -1/-2/-3 = frequency-style penalties. All six +1s split 1/6 bonus."""
    score = 4.0
    score -= _calc_penalty_standard(flags.get("jargon_level", 0))
    score -= _calc_penalty_standard(flags.get("prerequisite_level", 0))
    score -= _calc_penalty_standard(flags.get("pacing_level", 0))
    score -= _calc_penalty_standard(flags.get("scaffolding_level", 0))
    score -= _calc_penalty_standard(flags.get("ineffective_visual_level", 0))
    va = flags.get("contrast_level", 0)
    if isinstance(va, (int, float)) and int(va) == 1:
        pass
    elif isinstance(va, (int, float)) and int(va) != 0:
        idx = abs(int(va))
        if idx == 1:
            pen = 0.3
        elif idx == 2:
            pen = 0.6
        else:
            pen = 1.0
        score -= pen
    score = max(0.0, min(4.0, round(score, 2)))
    n_bonus = _count_plus_one_levels(
        flags.get("prerequisite_level", 0),
        flags.get("pacing_level", 0),
        flags.get("scaffolding_level", 0),
        flags.get("ineffective_visual_level", 0),
    )
    score = _apply_bonus_toward_five(score, n_bonus, N_BONUS_FIELDS_ADAPTABILITY)
    return clip_score_1_5(score), 0


def calculate_engagement(flags):
    score = 4.0
    score -= _calc_penalty_monotone(flags.get("monotone_level", 0))
    score -= _calc_penalty_standard(flags.get("ai_fatigue_level", 0))
    score -= _calc_penalty_standard(flags.get("clutter_level", 0))
    score -= _calc_penalty_standard(flags.get("disconnect_level", 0))
    score -= _calc_penalty_standard(flags.get("decorative_eye_candy_level", 0))
    score = max(0.0, min(4.0, round(score, 2)))
    n_bonus = _count_plus_one_levels(
        flags.get("monotone_level", 0),
        flags.get("disconnect_level", 0),
    )
    score = _apply_bonus_toward_five(score, n_bonus, N_BONUS_FIELDS_ENGAGEMENT)
    return clip_score_1_5(score), 0

# ==============================================================================
# UI HELPERS
# ==============================================================================

# Left → right: beyond expectation → severe
LEVEL_OPTIONS = [1, 0, -1, -2, -3]


def _csv_int(val, default: int = 0) -> int:
    try:
        if val is None or pd.isna(val):
            return default
    except TypeError:
        pass
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _csv_bool(val) -> bool:
    try:
        if val is None or pd.isna(val):
            return False
    except TypeError:
        pass
    if isinstance(val, bool):
        return val
    try:
        return int(float(val)) != 0
    except (TypeError, ValueError):
        return str(val).strip().lower() in ("true", "yes", "1")


def _normalize_agent_level(v, schema_v: int) -> int:
    """Legacy CSV used 0–3 (none→severe). Schema v2 stores 1,0,-1,-2,-3."""
    iv = _csv_int(v, 0)
    if schema_v >= EVAL_SCHEMA_VERSION:
        return max(-3, min(1, iv))
    if iv in (0, 1, 2, 3):
        return {0: 0, 1: -1, 2: -2, 3: -3}[iv]
    return max(-3, min(1, iv))


def render_compact_selector(label, key, help_text, scores_desc=None, scale_type="behavioral", default=0, flag_key=None):
    """
    Radio selector: each option shows the per-level description from FLAG_DESCRIPTIONS.
    Falls back to segmented control if no flag_key or descriptions found.
    """
    lang = st.session_state.lang
    descs = FLAG_DESCRIPTIONS.get(lang, FLAG_DESCRIPTIONS['en']).get(flag_key, {}) if flag_key else {}

    if not descs:
        # Fallback: segmented control
        st.markdown(f"**{label}**")
        st.caption(scores_desc if scores_desc else help_text)
        d = default if (default is not None and default in LEVEL_OPTIONS) else None
        scale_labels = t("scale")
        val = st.segmented_control(
            label,
            options=LEVEL_OPTIONS,
            format_func=lambda x, labels=scale_labels: labels.get(x, str(x)),
            default=d,
            key=key,
            label_visibility="collapsed",
        )
        return val  # None until user clicks

    # Build options from available levels (preserve order beyond → severe)
    options = [lv for lv in LEVEL_OPTIONS if lv in descs]
    idx_val = options.index(default) if (default is not None and default in options) else None
    val = st.selectbox(
        label,
        options=options,
        format_func=lambda x, _d=descs: _d[x],
        index=idx_val,
        key=key,
        help=help_text,
    )
    return val  # None until user selects

def parse_persona_attrs(persona_str: str) -> dict:
    """Parse persona string into Education, Motivation, Speed, Preference."""
    attrs = {}
    for part in persona_str.split("|"):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            k, v = k.strip(), v.strip()
            attrs[k] = v
    return attrs

def render_persona_header(persona_str: str):
    """Renders persona as a single concatenated string (no tags)."""
    st.caption(persona_str)

# ==============================================================================
# DATA LOADING
# ==============================================================================

def load_evaluation_data():
    """Load video pool from JSON."""
    if not VIDEO_POOL_JSON.exists():
        return None
    try:
        return _load_video_pool_json()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

@st.cache_data
def _load_video_pool_json():
    """Cached JSON load."""
    data = json.loads(VIDEO_POOL_JSON.read_text(encoding="utf-8"))
    return data.get("videos", [])

def load_saved_for_video(evaluator: str, video_url: str) -> dict | None:
    """Load previously saved evaluation for this evaluator + video. Returns dict with obj_flags and personas list, or None."""
    if not HUMAN_EVAL_CSV.exists():
        return None
    try:
        df = pd.read_csv(HUMAN_EVAL_CSV)
        rows = df[(df["evaluator"] == evaluator) & (df["video_url"] == video_url)]
        if rows.empty:
            return None
        first = rows.iloc[0]
        schema_v = _csv_int(first.get("eval_schema_version", 1), 1)
        obj = {
            "scaffolding_failure": _normalize_agent_level(first.get("scaffolding_failure", 0), schema_v),
            "pure_calc_bias": _normalize_agent_level(first.get("pure_calc_bias", 0), schema_v),
            "content_completeness": _normalize_agent_level(first.get("content_completeness", 0), schema_v),
            "explanatory_depth": _normalize_agent_level(first.get("explanatory_depth", 0), schema_v),
            "title_mismatch": _normalize_agent_level(first.get("title_mismatch", 0), schema_v),
            "visual_alignment": _normalize_agent_level(first.get("visual_alignment", 0), schema_v),
            "critical_errors": _csv_int(first.get("critical_errors", 0), 0),
            "minor_slips": _csv_int(first.get("minor_slips", 0), 0),
            "causal_inconsistencies": _csv_int(first.get("causal_inconsistencies", 0), 0),
            "information_overload": _csv_int(first.get("information_overload", 0), 0),
        }
        personas = []
        for _, row in rows.iterrows():
            personas.append({
                "jargon_level": _normalize_agent_level(row.get("jargon_level", 0), schema_v),
                "prerequisite_level": _normalize_agent_level(row.get("prerequisite_level", 0), schema_v),
                "pacing_level": _normalize_agent_level(row.get("pacing_level", 0), schema_v),
                "contrast_level": _normalize_agent_level(row.get("contrast_level", 0), schema_v),
                "scaffolding_level": _normalize_agent_level(row.get("scaffolding_level", 0), schema_v),
                "ineffective_visual_level": _normalize_agent_level(row.get("ineffective_visual_level", 0), schema_v),
                "monotone_level": _normalize_agent_level(row.get("monotone_level", 0), schema_v),
                "ai_fatigue_level": _normalize_agent_level(row.get("ai_fatigue_level", 0), schema_v),
                "clutter_level": _normalize_agent_level(row.get("clutter_level", 0), schema_v),
                "disconnect_level": _normalize_agent_level(row.get("disconnect_level", 0), schema_v),
                "decorative_eye_candy_level": _normalize_agent_level(row.get("decorative_eye_candy_level", 0), schema_v),
                "feedback": str(row.get("feedback", "") or ""),
            })
        return {"obj": obj, "personas": personas}
    except Exception:
        return None

def save_detailed_evaluation(data):
    """Save the detailed flag-based evaluation to CSV."""
    df_new = pd.DataFrame(data)
    
    if HUMAN_EVAL_CSV.exists():
        df_existing = pd.read_csv(HUMAN_EVAL_CSV)
        # Remove old entries for this user/video to avoid duplicates
        df_existing = df_existing[
            ~((df_existing['evaluator'] == data[0]['evaluator']) & 
              (df_existing['video_url'] == data[0]['video_url']))
        ]
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(HUMAN_EVAL_CSV, index=False)
    else:
        df_new.to_csv(HUMAN_EVAL_CSV, index=False)

# ==============================================================================
# PILOT & ASSIGNMENT MANAGEMENT
# ==============================================================================

def load_assignments() -> dict:
    if not ASSIGNMENTS_JSON.exists():
        return {}
    try:
        return json.loads(ASSIGNMENTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_assignments(data: dict) -> None:
    ASSIGNMENTS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )

def load_pilot_config() -> dict | None:
    if not PILOT_CONFIG_JSON.exists():
        return None
    try:
        cfg = json.loads(PILOT_CONFIG_JSON.read_text(encoding="utf-8"))
        url = cfg.get("pilot_video", {}).get("video_url", "")
        if "REPLACE_WITH" in url or not url:
            return None  # placeholder not yet filled in — skip pilot
        return cfg
    except Exception:
        return None

def _load_attention_check_pool() -> list:
    if not ATTENTION_CHECKS_JSON.exists():
        return []
    try:
        pool = json.loads(ATTENTION_CHECKS_JSON.read_text(encoding="utf-8")).get("attention_check_videos", [])
        return [v for v in pool if "REPLACE_WITH" not in v.get("video_url", "")]
    except Exception:
        return []

def get_or_create_assignment(username: str, content_video_urls: list) -> dict:
    """Return existing assignment or create a new one (pilot still pending)."""
    assignments = load_assignments()
    if username in assignments:
        return assignments[username]

    n_assigned = len(assignments)

    # Round-robin assign N_CONTENT_VIDEOS regular videos
    n = max(len(content_video_urls), 1)
    start = (n_assigned * N_CONTENT_VIDEOS) % n
    content_urls = [content_video_urls[(start + i) % n] for i in range(min(N_CONTENT_VIDEOS, len(content_video_urls)))]

    # Pick one attention check video (round-robin)
    attn_pool = _load_attention_check_pool()
    attn_url = attn_pool[n_assigned % len(attn_pool)]["video_url"] if attn_pool else None

    # Insert attention check at position 2 (3rd slot); annotator can't tell which it is
    assigned = list(content_urls)
    if attn_url:
        assigned.insert(min(2, len(assigned)), attn_url)

    entry = {
        "pilot_status": "pending",   # pending | passed | failed_max_attempts
        "pilot_attempts": 0,
        "assigned_video_urls": assigned,
        "attention_check_url": attn_url,
        "attention_check_result": None,  # null | passed | failed
        "created_at": datetime.now().isoformat(),
    }
    assignments[username] = entry
    save_assignments(assignments)
    return entry

def grade_against_ground_truth(submitted: dict, ground_truth: dict, tolerance: int = 1) -> tuple:
    """Returns (pass_rate 0–1, list of off-target field names)."""
    total, correct, off = 0, 0, []
    for key, expected in ground_truth.items():
        val = submitted.get(key)
        if val is None:
            total += 1
            off.append(key)
            continue
        total += 1
        if abs(int(val) - int(expected)) <= tolerance:
            correct += 1
        else:
            off.append(key)
    return (correct / total if total else 0.0), off

def _pilot_video_entry(pilot_cfg: dict) -> dict:
    """Convert pilot config to video_groups entry format."""
    pv = pilot_cfg["pilot_video"]
    return {
        "video_url": pv["video_url"],
        "title_en": pv.get("title_en", "Pilot Video"),
        "category": pv.get("category", "pilot"),
        "personas": pv.get("personas", [{"student_persona": ""}]),
    }

def _load_example_videos() -> dict:
    if not EXAMPLE_VIDEOS_JSON.exists():
        return {"examples": [], "annotation_rules": {"en": [], "ch": []}}
    try:
        return json.loads(EXAMPLE_VIDEOS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {"examples": [], "annotation_rules": {"en": [], "ch": []}}

def _attention_check_video_entry(attn_url: str) -> dict | None:
    """Get video_groups entry for an attention check video URL."""
    for ac in _load_attention_check_pool():
        if ac["video_url"] == attn_url:
            return {
                "video_url": ac["video_url"],
                "title_en": ac.get("title_en", ""),
                "category": ac.get("category", ""),
                "personas": ac.get("personas", [{"student_persona": ""}]),
            }
    return None

# ==============================================================================
# INSTRUCTIONS PAGE
# ==============================================================================

# Ordered list of objective metrics to display on the instructions page
_OBJ_METRICS = [
    ('scaffolding_failure', 'scaffolding_failure'),
    ('pure_calc', 'pure_calc_bias'),
    ('content_completeness', 'content_completeness'),
    ('explanatory_depth', 'explanatory_depth'),
    ('title_mismatch', 'title_mismatch'),
    ('visual_alignment', 'visual_alignment'),
]
_SUBJ_METRICS = [
    ('jargon', 'jargon'),
    ('prereq_gap', 'prereq_gap'),
    ('pacing', 'pacing'),
    ('illegible', 'illegible'),
    ('scaffolding', 'scaffolding'),
    ('ineffective_visual', 'ineffective_visual'),
    ('monotone', 'monotone'),
    ('ai_fatigue', 'ai_fatigue'),
    ('clutter', 'clutter'),
    ('disconnect', 'disconnect'),
    ('decorative_eye_candy', 'decorative_eye_candy'),
]


def render_pilot_result_page(pilot_cfg: dict) -> None:
    """Show submitted vs reference comparison after pilot grading. Returns when user clicks action button."""
    lang = st.session_state.lang
    result = st.session_state.pilot_graded_result   # {rate, off_fields, submitted, passed, attempts_used, max_att}
    gt = pilot_cfg.get("ground_truth", {})
    tolerance = pilot_cfg.get("tolerance", 1)
    passed = result["passed"]
    off_fields = result["off_fields"]
    attempts_used = result["attempts_used"]
    max_att = result["max_att"]
    remaining = max_att - attempts_used

    st.title(t('pilot_result_header'))

    if passed:
        st.success(t('pilot_result_pass_msg'))
    elif remaining <= 0:
        st.error(t('pilot_result_fail_final_msg'))
    else:
        st.error(
            t('pilot_result_fail_msg').format(n_off=len(off_fields)) +
            "  " + t('pilot_result_attempts_left').format(n=remaining)
        )

    # ── Comparison table ──────────────────────────────────────────────────────
    submitted = result["submitted"]
    LEVEL_BADGE = {1: "✅ +1", 0: "⬜ 0", -1: "🟡 −1", -2: "🟠 −2", -3: "🔴 −3"}
    # Obj metrics are stored without _level suffix; subj metrics with _level suffix
    # Build canonical ordered list: (label_key, submitted_key) for each metric in gt
    _subj_submitted_keys = {
        'jargon': 'jargon_level', 'prereq_gap': 'prerequisite_level',
        'pacing': 'pacing_level', 'illegible': 'contrast_level',
        'scaffolding': 'scaffolding_level', 'ineffective_visual': 'ineffective_visual_level',
        'monotone': 'monotone_level', 'ai_fatigue': 'ai_fatigue_level',
        'clutter': 'clutter_level', 'disconnect': 'disconnect_level',
        'decorative_eye_candy': 'decorative_eye_candy_level',
    }
    _ordered_metrics = []
    for lk, fk in _OBJ_METRICS:
        _ordered_metrics.append((lk, fk))   # obj: submitted key = fk (no suffix)
    for lk, fk in _SUBJ_METRICS:
        sub_key = _subj_submitted_keys.get(fk, f"{fk}_level")
        _ordered_metrics.append((lk, sub_key))

    header = st.columns([3, 2, 2, 1])
    header[0].markdown(f"**{t('pilot_metric_col')}**")
    header[1].markdown(f"**{t('pilot_your_col')}**")
    header[2].markdown(f"**{t('pilot_ref_col')}**")
    header[3].markdown(f"**{t('pilot_match_col')}**")
    st.divider()

    for lk, sub_key in _ordered_metrics:
        if sub_key not in gt:
            continue
        ref_val = int(gt[sub_key])
        sub_val = submitted.get(sub_key)
        label_text = t(lk) if lk in TRANSLATIONS.get(lang, TRANSLATIONS['en']) else lk.replace("_", " ").title()
        sub_badge = LEVEL_BADGE.get(int(sub_val), str(sub_val)) if sub_val is not None else "—"
        ref_badge = LEVEL_BADGE.get(ref_val, str(ref_val))
        within = (sub_val is not None) and abs(int(sub_val) - ref_val) <= tolerance
        match_icon = "✅" if within else "❌"
        row = st.columns([3, 2, 2, 1])
        row[0].markdown(label_text)
        row[1].markdown(sub_badge)
        row[2].markdown(ref_badge)
        row[3].markdown(match_icon)

    st.divider()

    # ── Action buttons ────────────────────────────────────────────────────────
    if passed:
        if st.button(t('pilot_continue_btn'), type="primary"):
            del st.session_state.pilot_graded_result
            st.rerun()
    elif remaining <= 0:
        pass  # no action — contact research team
    else:
        if st.button(t('pilot_retry_btn'), type="primary"):
            del st.session_state.pilot_graded_result
            st.rerun()


def render_instructions_page(assignment: dict) -> None:
    lang = st.session_state.lang
    descs = FLAG_DESCRIPTIONS.get(lang, FLAG_DESCRIPTIONS['en'])
    example_data = _load_example_videos()
    LEVEL_BADGE = {1: "✅ +1", 0: "⬜ 0", -1: "🟡 −1", -2: "🟠 −2", -3: "🔴 −3"}
    # Full annotation key → (label_key, flag_key) covering obj + subj metrics
    _ALL_METRIC_MAP = {fk: (lk, fk) for lk, fk in _OBJ_METRICS + _SUBJ_METRICS}
    # Also map from annotation json keys that differ from flag_keys
    _ALL_METRIC_MAP["ineffective_visual"] = ("ineffective_visual", "ineffective_visual")
    _ALL_METRIC_MAP["prerequisite_gap"]   = ("prereq_gap", "prereq_gap")

    st.title(t('instructions_title'))
    st.markdown(t('instructions_task_md'))

    # ── Annotation rules ─────────────────────────────────────────────
    st.divider()
    st.markdown(t('instructions_rules_header'))
    rules = example_data.get("annotation_rules", {}).get(lang, example_data.get("annotation_rules", {}).get("en", []))
    for rule in rules:
        st.markdown(f"- {rule}")

    # ── Calibration examples ─────────────────────────────────────────
    examples = example_data.get("examples", [])
    if examples:
        st.divider()
        st.markdown(t('instructions_examples_header'))
        for i, ex in enumerate(examples):
            title = ex.get(f"title_{lang}", ex.get("title_en", f"Example {i+1}"))
            with st.expander(f"**{title}**", expanded=(i == 0)):
                _, col_v, _ = st.columns([1, 2, 1])
                with col_v:
                    st.video(ex["video_url"])
                comment = ex.get("comments", {}).get(lang, ex.get("comments", {}).get("en", ""))
                if comment:
                    st.markdown(t('instructions_example_comment'))
                    st.info(comment)
                persona = ex.get("persona", "")
                if persona:
                    st.caption(f"👤 {persona}")
                anns = ex.get("annotations", {})
                if anns:
                    st.markdown(t('instructions_example_ratings'))
                    # Build reverse map: flag_key → annotation json key
                    _fk_to_ann = {v[1]: k for k, v in _ALL_METRIC_MAP.items()}
                    icon_map = {1: "✅", 0: "⬜", -1: "🟡", -2: "🟠", -3: "🔴"}
                    for lk, fk in _OBJ_METRICS + _SUBJ_METRICS:
                        ann_key = _fk_to_ann.get(fk, fk)
                        if ann_key not in anns:
                            continue
                        val = anns[ann_key]
                        label_text = t(lk) if lk in TRANSLATIONS.get(lang, TRANSLATIONS['en']) else lk.replace("_", " ").title()
                        level_descs = descs.get(fk, {})
                        desc_text = level_descs.get(int(val), LEVEL_BADGE.get(int(val), str(val)))
                        icon = icon_map.get(int(val), "")
                        st.markdown(f"- **{label_text}**: {icon} *{desc_text}*")

    # ── Metric reference ─────────────────────────────────────────────
    st.divider()
    st.markdown(t('instructions_obj_header'))
    _letters = "abcdefghijklmnopqrstuvwxyz"
    for i, (label_key, flag_key) in enumerate(_OBJ_METRICS):
        levels = descs.get(flag_key, {})
        help_key = 'pure_calc_help' if label_key == 'pure_calc' else f"{label_key}_help"
        letter = _letters[i]
        with st.expander(f"**{letter}. {t(label_key)}** — {t(help_key)}", expanded=False):
            st.markdown(t('instructions_metric_levels'))
            for lvl in [1, 0, -1, -2, -3]:
                if lvl in levels:
                    st.markdown(f"- **{LEVEL_BADGE[lvl]}**: {levels[lvl]}")

    st.divider()
    st.markdown(t('instructions_subj_header'))
    for label_key, flag_key in _SUBJ_METRICS:
        levels = descs.get(flag_key, {})
        with st.expander(f"**{t(label_key)}** — {t(f'{label_key}_help')}", expanded=False):
            st.markdown(t('instructions_metric_levels'))
            for lvl in [1, 0, -1, -2, -3]:
                if lvl in levels:
                    st.markdown(f"- **{LEVEL_BADGE[lvl]}**: {levels[lvl]}")

    st.divider()
    if st.button(t('instructions_proceed_btn'), type="primary", use_container_width=True):
        st.session_state.instructions_seen = True
        st.rerun()


# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    if not st.session_state.logged_in:
        # Simple Login
        col_ch, col_en, _ = st.columns([1, 1, 4])
        with col_ch:
            if st.button("CH", key="login_btn_ch", use_container_width=True) and st.session_state.lang != 'ch':
                st.session_state.lang = 'ch'
                st.rerun()
        with col_en:
            if st.button("EN", key="login_btn_en", use_container_width=True) and st.session_state.lang != 'en':
                st.session_state.lang = 'en'
                st.rerun()
        st.title(t('login_title'))
        with st.form("login"):
            name = st.text_input(t('enter_name'))
            if st.form_submit_button(t('start')):
                if name:
                    st.session_state.logged_in = True
                    st.session_state.username = name
                    st.rerun()
        return

    # ── Data + Assignment Gate ────────────────────────────────────────────────
    video_groups = load_evaluation_data()
    if not video_groups:
        st.error(t('no_data'))
        return

    pilot_cfg = load_pilot_config()
    content_urls = [v["video_url"] for v in video_groups]
    assignment = get_or_create_assignment(st.session_state.username, content_urls)

    # ── Instructions gate (per-session, resets on every login) ───────
    if not st.session_state.get("instructions_seen", False):
        render_instructions_page(assignment)
        return

    pilot_status = assignment["pilot_status"]
    is_pilot = (pilot_cfg is not None) and (pilot_status != "passed")

    # ── Pilot result gate (after grading, before next action) ─────────
    if "pilot_graded_result" in st.session_state and pilot_cfg is not None:
        render_pilot_result_page(pilot_cfg)
        return

    if is_pilot:
        if pilot_status == "failed_max_attempts":
            st.error(t('pilot_fail_final').format(max=pilot_cfg.get("max_attempts", 3)))
            return
        active_videos = [_pilot_video_entry(pilot_cfg)]
    else:
        attn_url = assignment.get("attention_check_url")
        url_to_video = {v["video_url"]: v for v in video_groups}
        if attn_url:
            attn_entry = _attention_check_video_entry(attn_url)
            if attn_entry:
                url_to_video[attn_url] = attn_entry
        active_videos = [url_to_video[u] for u in assignment["assigned_video_urls"] if u in url_to_video]
        if not active_videos:
            st.success(t('all_done').format(n=len(assignment["assigned_video_urls"])))
            return
        completed = sum(1 for v in active_videos if load_saved_for_video(st.session_state.username, v["video_url"]) is not None)

    with st.sidebar:
        # Language toggle
        col_lang1, col_lang2 = st.columns(2)
        with col_lang1:
            if st.button("CH", key="btn_ch", use_container_width=True) and st.session_state.lang != 'ch':
                st.session_state.lang = 'ch'
                st.rerun()
        with col_lang2:
            if st.button("EN", key="btn_en", use_container_width=True) and st.session_state.lang != 'en':
                st.session_state.lang = 'en'
                st.rerun()
        st.caption("CH / EN")
        st.write("---")
        st.write(f"{t('user')}: **{st.session_state.username}**")
        total_videos = len(active_videos)
        if is_pilot:
            st.info(t('pilot_banner'))
            idx = 0
        else:
            st.caption(t('assigned_banner').format(done=completed, total=total_videos))
            idx = st.number_input(t('video_index'), 0, total_videos - 1, min(st.session_state.current_index, total_videos - 1))
            st.session_state.current_index = idx
            st.progress((completed) / total_videos)

        current_video = active_videos[idx]
        st.caption(f"{t('current')}: {current_video['title_en']}")

    # ── Main Content ──────────────────────────────────────────────────────
    if is_pilot:
        pct = int(pilot_cfg.get("pass_threshold", 0.7) * 100)
        used = assignment["pilot_attempts"]
        max_att = pilot_cfg.get("max_attempts", 3)
        st.info(t('pilot_intro').format(pct=pct, used=used, max=max_att))
    st.header(f"📹 {current_video['title_en']}")

    # Video player (centred, not full-bleed)
    _, col_video, _ = st.columns([1, 2, 1])
    with col_video:
        st.video(current_video['video_url'])

    st.write("---")

    # Load saved evaluation for this user + video (when going back)
    saved = load_saved_for_video(st.session_state.username, current_video['video_url'])
    so = saved["obj"] if saved else None
    sp_list = saved["personas"] if saved else []

    # Tab layout: Objective | Persona 1 | Persona 2 | …
    tab_labels = [t('tab_objective')] + [
        f"👤 P{i+1}" for i in range(len(current_video['personas']))
    ]
    all_tabs = st.tabs(tab_labels)

    all_evals = []
    obj_flags = None
    k = lambda s: f"{s}_{idx}"  # key suffix so widgets reset on video advance

    # ── Tab 0: Objective (Accuracy & Logic) ──────────────────────────
    with all_tabs[0]:
        st.caption(t('obj_caption'))

        # — Pedagogical Depth —
        st.markdown(f"#### {t('pedagogical')}")
        c1, c2 = st.columns(2)
        with c1:
            scaffolding = render_compact_selector(t('scaffolding_failure'), k("scaffold"), t('scaffolding_failure_help'), t('scores_scaffolding'), "severity", default=(so.get("scaffolding_failure", 0) if so else None), flag_key="scaffolding_failure")
        with c2:
            pure_calc = render_compact_selector(t('pure_calc'), k("p_calc"), t('pure_calc_help'), t('scores_p_calc'), "severity", default=(so.get("pure_calc_bias", 0) if so else None), flag_key="pure_calc_bias")

        # — Completeness —
        st.markdown(f"#### {t('completeness')}")
        c1, c2 = st.columns(2)
        with c1:
            content_comp = render_compact_selector(t('content_completeness'), k("cont_comp"), t('content_completeness_help'), t('scores_content_completeness'), "severity", default=(so.get("content_completeness", 0) if so else None), flag_key="content_completeness")
        with c2:
            expl_depth = render_compact_selector(t('explanatory_depth'), k("expl_depth"), t('explanatory_depth_help'), t('scores_explanatory_depth'), "severity", default=(so.get("explanatory_depth", 0) if so else None), flag_key="explanatory_depth")

        # — Accuracy Checks —
        st.markdown(f"#### {t('accuracy_checks')}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            t_mismatch = render_compact_selector(t('title_mismatch'), k("t_mis"), t('title_mismatch_help'), t('scores_t_mismatch'), "severity", default=(so.get("title_mismatch", 0) if so else None), flag_key="title_mismatch")
        with c2:
            v_align = render_compact_selector(t('visual_alignment'), k("v_align"), t('visual_alignment_help'), t('scores_v_align'), "severity", default=(so.get("visual_alignment", 0) if so else None), flag_key="visual_alignment")
        with c3:
            crit_err = st.number_input(t('critical_errors'), 0, 10, (so.get("critical_errors", 0) if so else 0), key=k("crit_err"))
        with c4:
            minor_slip = st.number_input(t('minor_slips'), 0, 10, (so.get("minor_slips", 0) if so else 0), key=k("minor_slip"))

        # — Logic Checks —
        st.markdown(f"#### {t('logic_checks')}")
        c1, c2 = st.columns(2)
        with c1:
            causal_inc = st.number_input(t('causal_inconsistencies'), 0, 10, (so.get("causal_inconsistencies", 0) if so else 0), key=k("causal_inc"), help=t('causal_inconsistencies_help'))
        with c2:
            info_over = st.number_input(t('info_overload'), 0, 20, (so.get("information_overload", 0) if so else 0), key=k("info_over"), help=t('info_overload_help'))

        obj_flags = {
            'scaffolding_failure': scaffolding, 'pure_calc_bias': pure_calc,
            'content_completeness': content_comp, 'explanatory_depth': expl_depth,
            'title_mismatch': t_mismatch, 'visual_alignment': v_align,
            'critical_errors': crit_err, 'minor_slips': minor_slip,
            'causal_inconsistencies': causal_inc,
            'information_overload': info_over,
        }
        _safe = {k: (v if v is not None else 0) for k, v in obj_flags.items()}
        acc_score, _ = calculate_accuracy(_safe)
        log_score, _ = calculate_logic(_safe)

    # ── Tabs 1..N: Persona (Subjective) ──────────────────────────────
    for i, (tab, p_data) in enumerate(zip(all_tabs[1:], current_video['personas'])):
        sp = sp_list[i] if i < len(sp_list) else None
        with tab:
            render_persona_header(p_data['student_persona'])

            # — Adaptability Flags —
            st.markdown(t('adaptability_flags'))
            c1, c2, c3 = st.columns(3)
            with c1:
                jargon = render_compact_selector(t('jargon'), f"jargon_{idx}_{i}", t('jargon_help'), t('scores_jargon'), "behavioral", default=sp["jargon_level"] if sp else None, flag_key="jargon")
                prereq = render_compact_selector(t('prereq_gap'), f"prereq_{idx}_{i}", t('prereq_gap_help'), t('scores_prereq'), "behavioral", default=sp["prerequisite_level"] if sp else None, flag_key="prereq_gap")
            with c2:
                pacing = render_compact_selector(t('pacing'), f"pacing_{idx}_{i}", t('pacing_help'), t('scores_pacing'), "behavioral", default=sp["pacing_level"] if sp else None, flag_key="pacing")
                contrast = render_compact_selector(t('illegible'), f"cont_{idx}_{i}", t('illegible_help'), t('scores_illegible'), "frequency", default=sp["contrast_level"] if sp else None, flag_key="illegible")
            with c3:
                scaffolding = render_compact_selector(t('scaffolding'), f"scaff_{idx}_{i}", t('scaffolding_help'), t('scores_scaffold'), "behavioral", default=sp["scaffolding_level"] if sp else None, flag_key="scaffolding")
                ineffective_visual = render_compact_selector(t('ineffective_visual'), f"ineff_vis_{idx}_{i}", t('ineffective_visual_help'), t('scores_ineffective_visual'), "frequency", default=(sp.get("ineffective_visual_level", 0) if sp else None), flag_key="ineffective_visual")

            # — Engagement Flags —
            st.markdown(t('engagement_flags'))
            c1, c2, c3 = st.columns(3)
            with c1:
                monotone = render_compact_selector(t('monotone'), f"mono_{idx}_{i}", t('monotone_help'), t('scores_monotone'), "behavioral", default=sp["monotone_level"] if sp else None, flag_key="monotone")
                ai_fatigue = render_compact_selector(t('ai_fatigue'), f"ai_{idx}_{i}", t('ai_fatigue_help'), t('scores_ai_fatigue'), "behavioral", default=sp["ai_fatigue_level"] if sp else None, flag_key="ai_fatigue")
            with c2:
                clutter = render_compact_selector(t('clutter'), f"clut_{idx}_{i}", t('clutter_help'), t('scores_clutter'), "frequency", default=sp["clutter_level"] if sp else None, flag_key="clutter")
                disconnect = render_compact_selector(t('disconnect'), f"disc_{idx}_{i}", t('disconnect_help'), t('scores_disconnect'), "behavioral", default=sp["disconnect_level"] if sp else None, flag_key="disconnect")
            with c3:
                decorative_eye_candy = render_compact_selector(t('decorative_eye_candy'), f"eye_candy_{idx}_{i}", t('decorative_eye_candy_help'), t('scores_decorative_eye_candy'), "frequency", default=(sp.get("decorative_eye_candy_level", 0) if sp else None), flag_key="decorative_eye_candy")

            feedback = st.text_area(t('optional_comments'), value=sp["feedback"] if sp else "", key=f"feed_{idx}_{i}")

            subj_flags = {
                'jargon_level': jargon, 'prerequisite_level': prereq, 'pacing_level': pacing,
                'contrast_level': contrast, 'scaffolding_level': scaffolding,
                'ineffective_visual_level': ineffective_visual,
                'monotone_level': monotone, 'ai_fatigue_level': ai_fatigue,
                'clutter_level': clutter, 'disconnect_level': disconnect,
                'decorative_eye_candy_level': decorative_eye_candy,
            }
            _subj_safe = {k: (v if v is not None else 0) for k, v in subj_flags.items()}
            adt_score, _ = calculate_adaptability(_subj_safe)
            eng_score, _ = calculate_engagement(_subj_safe)

            eval_entry = {
                'timestamp': datetime.now().isoformat(),
                'eval_schema_version': EVAL_SCHEMA_VERSION,
                'evaluator': st.session_state.username,
                'video_url': current_video['video_url'],
                'title_en': current_video['title_en'],
                'student_persona': p_data['student_persona'],
                'accuracy': acc_score, 'logic': log_score,
                'adaptability': adt_score, 'engagement': eng_score,
                **obj_flags,
                **subj_flags,
                'feedback': feedback,
            }
            all_evals.append(eval_entry)

    # ── Submit ────────────────────────────────────────────────────────
    st.write("---")
    _severity_keys = [
        'scaffolding_failure', 'pure_calc_bias', 'content_completeness',
        'explanatory_depth', 'title_mismatch', 'visual_alignment',
    ]
    _subj_keys = [
        'jargon_level', 'prerequisite_level', 'pacing_level', 'contrast_level',
        'scaffolding_level', 'ineffective_visual_level', 'monotone_level',
        'ai_fatigue_level', 'clutter_level', 'disconnect_level', 'decorative_eye_candy_level',
    ]
    submit_label = t('pilot_submit_btn') if is_pilot else t('save_evals')
    if st.button(submit_label, type="primary", use_container_width=True):
        n_missing = sum(1 for k in _severity_keys if obj_flags is None or obj_flags.get(k) is None)
        for entry in all_evals:
            n_missing += sum(1 for k in _subj_keys if entry.get(k) is None)
        if n_missing:
            st.error(t('save_incomplete').format(n=n_missing))
        elif is_pilot:
            # ── Grade pilot ───────────────────────────────────────────
            gt = pilot_cfg.get("ground_truth", {})
            tolerance = pilot_cfg.get("tolerance", 1)
            threshold = pilot_cfg.get("pass_threshold", 0.7)
            max_att = pilot_cfg.get("max_attempts", 3)
            # Merge obj + subj from first eval_entry for grading
            submitted = {**all_evals[0]} if all_evals else {}
            rate, off_fields = grade_against_ground_truth(submitted, gt, tolerance)
            assignments = load_assignments()
            assignments[st.session_state.username]["pilot_attempts"] += 1
            attempts_used = assignments[st.session_state.username]["pilot_attempts"]
            passed_pilot = rate >= threshold
            if passed_pilot:
                assignments[st.session_state.username]["pilot_status"] = "passed"
                st.session_state.current_index = 0
            elif attempts_used >= max_att:
                assignments[st.session_state.username]["pilot_status"] = "failed_max_attempts"
            save_assignments(assignments)
            # Store result for comparison page, then rerun
            st.session_state.pilot_graded_result = {
                "rate": rate,
                "off_fields": off_fields,
                "submitted": submitted,
                "passed": passed_pilot,
                "attempts_used": attempts_used,
                "max_att": max_att,
            }
            st.rerun()
        else:
            # ── Normal save ───────────────────────────────────────────
            save_detailed_evaluation(all_evals)
            # Check attention check quality (silent, recorded only)
            attn_url = assignment.get("attention_check_url")
            if attn_url and current_video["video_url"] == attn_url and all_evals:
                for ac in _load_attention_check_pool():
                    if ac["video_url"] == attn_url:
                        ac_gt = ac.get("ground_truth", {})
                        ac_rate, _ = grade_against_ground_truth(all_evals[0], ac_gt, tolerance=1)
                        ac_result = "passed" if ac_rate >= 0.6 else "failed"
                        assignments = load_assignments()
                        assignments[st.session_state.username]["attention_check_result"] = ac_result
                        save_assignments(assignments)
                        break
            st.toast(t('saved_toast'))
            if idx < total_videos - 1:
                st.session_state.current_index = idx + 1
            st.rerun()

if __name__ == "__main__":
    main()