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

# Constants (use resolve() for absolute paths - works regardless of streamlit cwd)
BASE_DIR = Path(__file__).resolve().parent.parent
# Data source: human_eval_input.json (2 test entries) takes precedence over CSV
INPUT_JSON = BASE_DIR / "phase_2" / "human_eval_input.json"
CSV_PATH = BASE_DIR / "phase_2" / "merged_small_scale_summaries_20260224_014339.csv"
RESULTS_DIR = BASE_DIR / "phase_2"
HUMAN_EVAL_CSV = RESULTS_DIR / "human_eval_detailed_results.csv"

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
        'formula_dumping': "Formula Dumping",
        'formula_dumping_help': "No derivation/intuition provided.",
        'pure_calc': "Pure Calculation Bias",
        'pure_calc_help': ">70% content is just calculation.",
        'depth_gap': "Pedagogical Depth Gap",
        'depth_gap_help': "Title promises concept/understanding but delivery is mostly procedural.",
        'completeness': "Completeness",
        'brevity': "Content Brevity",
        'brevity_help': "Too thin/short for topic.",
        'superficial': "Superficial Coverage",
        'superficial_help': "Mentions topics without explaining.",
        'missing_core': "Missing Core Concepts",
        'missing_core_help': "Essential topics implied by the title are absent.",
        'breadth_no_depth': "Breadth Without Depth",
        'breadth_no_depth_help': "Many topics only “mentioned”; few reach explained depth.",
        'accuracy_checks': "Accuracy Checks",
        'title_mismatch': "Title Mismatch",
        'title_mismatch_help': "Content differs from title.",
        'visual_alignment': "Visual Alignment",
        'visual_alignment_help': "Visuals don't match audio.",
        'error_counts': "Error Counts",
        'critical_errors': "Critical Fact Errors",
        'minor_slips': "Minor Slips",
        'logic_checks': "Logic Checks",
        'logic_flow': "Logic Flow",
        'logic_flow_opts': ["Concrete/Inductive (Good)", "Deductive (Good)", "Formula First (Bad)"],
        'logic_leaps': "Logic Leaps (Steps skipped)",
        'prereq_violations': "Prerequisite Violations",
        'causal_inconsistencies': "Causal Inconsistencies",
        'calc_score': "🧮 Calculated Score: **Accuracy: {acc}** | **Logic: {log}**",
        'subj_exp': "2. Subjective Experience (Per Persona)",
        'persona': "Persona",
        'student_profile': "👤 **Student Profile:**",
        'adaptability_flags': "#### 🧠 Adaptability Flags (Barriers)",
        'jargon': "1. Jargon Overload",
        'jargon_help': "Undefined terms for this persona.",
        'prereq_gap': "2. Prerequisite Gap",
        'prereq_gap_help': "Assumes knowledge they lack.",
        'pacing': "3. Pacing Mismatch",
        'pacing_help': "Too fast/slow for this persona.",
        'illegible': "4. Illegible Text",
        'illegible_help': "Low contrast/small font.",
        'scaffolding': "5. Missing Scaffolding",
        'scaffolding_help': "Lack of examples/analogies.",
        'ineffective_visual': "6. Ineffective Visual Representation",
        'ineffective_visual_help': "Static/decorative visuals where vectors, charts, or motion would teach; student must imagine.",
        'engagement_flags': "#### ⚡ Engagement Flags (Motivation)",
        'monotone': "7. Monotone Audio",
        'monotone_help': "Robotic/Flat voice.",
        'ai_fatigue': "8. AI Fatigue (visuals)",
        'ai_fatigue_help': "Generic / stock / AI-slop images & slides only. Voice/TTS → use Monotone.",
        'clutter': "9. Visual Clutter",
        'clutter_help': "Too much text/chaos.",
        'disconnect': "10. AV Disconnect",
        'disconnect_help': "Visuals don't match audio.",
        'decorative_eye_candy': "11. Decorative Eye-Candy",
        'decorative_eye_candy_help': "Flashy motion/graphics with no instructional payload; distracts serious learners.",
        'subj_calc': "🧮 Calculated Score: **Adaptability: {adt}** | **Engagement: {eng}**",
        'optional_comments': "Optional Comments",
        'save_evals': "💾 Save All Evaluations",
        'saved_toast': "✅ Evaluation Saved!",
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
        'scale': {1: "+1", 0: "0", -1: "−1", -2: "−2", -3: "−3"},
        'tab_objective': "📐 Objective",
        'info_overload': "Information overload segments (count)",
        # Per-criteria (+1 / 0 / −1 / −2 / −3) — rubric aligned with agent prompts
        'scores_f_dump': "+1: Exceptional scaffolding | 0: OK | −1…−3: Missing intuition → blocking formula dump",
        'scores_p_calc': "+1: Strong balance theory/examples | 0: OK | −1…−3: Drift toward pure calculation",
        'scores_depth_gap': "+1: Title & depth aligned | 0: OK | −1…−3: Overpromise → procedural / plug-and-chug",
        'scores_brevity': "+1: Rich for title | 0: OK | −1…−3: Thin → inadequate coverage",
        'scores_superficial': "+1: Deep where promised | 0: OK | −1…−3: Surface → missing depth",
        'scores_missing_core': "+1: Core topics covered | 0: OK | −1: minor gap | −2: core absent | −3: multiple core gaps",
        'scores_breadth_no_depth': "+1: Adequate depth on topics | 0: OK | −1…−3: Topic list / mention-only",
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
        'formula_dumping': "公式堆砌",
        'formula_dumping_help': "未提供推導或直覺說明。",
        'pure_calc': "純計算偏重",
        'pure_calc_help': ">70% 內容僅為計算。",
        'depth_gap': "教學深度落差",
        'depth_gap_help': "標題承諾理解／概念，內容卻偏操作與演算。",
        'completeness': "完整性",
        'brevity': "內容過簡",
        'brevity_help': "對該主題而言過於精簡。",
        'superficial': "表面涵蓋",
        'superficial_help': "僅提及主題但未解釋。",
        'missing_core': "缺少核心概念",
        'missing_core_help': "依標題應涵蓋的核心內容缺席。",
        'breadth_no_depth': "廣而不深",
        'breadth_no_depth_help': "主題點很多但多半只帶過，缺乏講解深度。",
        'accuracy_checks': "準確性檢查",
        'title_mismatch': "標題不符",
        'title_mismatch_help': "內容與標題不符。",
        'visual_alignment': "視覺對齊",
        'visual_alignment_help': "畫面與語音不匹配。",
        'error_counts': "錯誤計數",
        'critical_errors': "重大事實錯誤",
        'minor_slips': "輕微疏漏",
        'logic_checks': "邏輯檢查",
        'logic_flow': "邏輯流程",
        'logic_flow_opts': ["具體/歸納（佳）", "演繹（佳）", "公式先行（差）"],
        'logic_leaps': "邏輯跳躍（省略步驟）",
        'prereq_violations': "先備知識違反",
        'causal_inconsistencies': "因果不一致",
        'calc_score': "🧮 計算分數：**準確性：{acc}** | **邏輯：{log}**",
        'subj_exp': "2. 主觀體驗（依角色）",
        'persona': "角色",
        'student_profile': "👤 **學生：**",
        'adaptability_flags': "####  適應性指標（障礙）",
        'jargon': "1. 術語過載",
        'jargon_help': "對該角色未定義的術語。",
        'prereq_gap': "2. 先備知識落差",
        'prereq_gap_help': "假設他們具備的知識。",
        'pacing': "3. 節奏不匹配",
        'pacing_help': "對該角色而言過快或過慢。",
        'illegible': "4. 文字難以辨識",
        'illegible_help': "對比度低或字體過小。",
        'scaffolding': "5. 缺乏鷹架",
        'scaffolding_help': "缺少範例或類比。",
        'ineffective_visual': "6. 無效視覺表徵",
        'ineffective_visual_help': "該用向量、圖表或動態演示時卻用靜態／裝飾畫面，學生只能靠想像。",
        'engagement_flags': "#### ⚡ 投入度指標（動機）",
        'monotone': "7. 單調語音",
        'monotone_help': "機械化/平淡的聲音。",
        'ai_fatigue': "8. AI 疲勞感（畫面）",
        'ai_fatigue_help': "僅限廉價／套版／AI 感圖像與版面；語音／TTS 請用單調語音。",
        'clutter': "9. 視覺雜亂",
        'clutter_help': "文字過多或混亂。",
        'disconnect': "10. 影音脫節",
        'disconnect_help': "畫面與語音不匹配。",
        'decorative_eye_candy': "11. 裝飾性花俏畫面",
        'decorative_eye_candy_help': "華麗動畫／圖像但無教學內容，干擾認真學習。",
        'subj_calc': "🧮 計算分數：**適應性：{adt}** | **投入度：{eng}**",
        'optional_comments': "選填意見",
        'save_evals': "💾 儲存所有評測",
        'saved_toast': "✅ 評測已儲存！",
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
        'scale': {1: "+1", 0: "0", -1: "−1", -2: "−2", -3: "−3"},
        'tab_objective': "📐 客觀",
        'info_overload': "資訊過載片段（次數）",
        'scores_f_dump': "+1: 鷹架極佳 | 0: 可 | −1…−3: 缺直覺→僅堆公式",
        'scores_p_calc': "+1: 理論／例題平衡佳 | 0: 可 | −1…−3: 偏純計算",
        'scores_depth_gap': "+1: 標題與深度一致 | 0: 可 | −1…−3: 過度承諾→偏操作／代公式",
        'scores_brevity': "+1: 對標題很充實 | 0: 可 | −1…−3: 過簡→不足",
        'scores_superficial': "+1: 深度符合標題 | 0: 可 | −1…−3: 表面→缺深度",
        'scores_missing_core': "+1: 核心概念齊備 | 0: 可 | −1: 小缺 | −2: 缺一核心 | −3: 缺多項核心",
        'scores_breadth_no_depth': "+1: 主題多有講透 | 0: 可 | −1…−3: 像目錄／只點名不講",
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
    }
}
def _logic_flow_index(flow_opts, stored_internal: str) -> int:
    """Find index in flow_opts whose internal value equals stored_internal."""
    for i, opt in enumerate(flow_opts):
        if LOGIC_FLOW_MAP.get(opt, opt) == stored_internal:
            return i
    return 0

# Logic flow: display label -> internal value (stored in CSV)
LOGIC_FLOW_MAP = {
    "Concrete/Inductive (Good)": "Concrete/Inductive (Good)",
    "Deductive (Good)": "Deductive (Good)",
    "Formula First (Bad)": "Formula First (Bad)",
    "具體/歸納（佳）": "Concrete/Inductive (Good)",
    "演繹（佳）": "Deductive (Good)",
    "公式先行（差）": "Formula First (Bad)",
}

def t(key):
    """Get translated string for current language."""
    return TRANSLATIONS[st.session_state.lang].get(key, key)

# ==============================================================================
# SCORING LOGIC ENGINE (Aligned with batch_audit_processor.py)
# ==============================================================================

EVAL_SCHEMA_VERSION = 4

# Match batch_audit_processor: bonus only for agent2 +1 anchors (1,2,5,7 + visual for accuracy).
N_BONUS_FIELDS_ACCURACY = 5
N_BONUS_FIELDS_LOGIC = 4
# Match batch: all adaptability / engagement sliders can contribute +1 toward 5.0 (1/N each; missing keys default 0).
N_BONUS_FIELDS_ADAPTABILITY = 6
N_BONUS_FIELDS_ENGAGEMENT = 5


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
    return {0: 0, 1: 0.5, 2: 1.0, 3: 1.5}.get(idx, 1.5 if idx >= 3 else 0)


def _calc_penalty_disconnect(severity):
    idx = _sev_idx(severity)
    return {0: 0, 1: 0.5, 2: 1.0, 3: 1.5}.get(idx, 1.5 if idx >= 3 else 0)


def calculate_accuracy(flags):
    """
    Matches batch_audit_processor._calculate_agent2_scores (base 4.0, bonus 1/n, clip).
    """
    accuracy = 4.0
    score_cap = 4.0
    fd = _sev_penalty_agent(flags.get("formula_dumping", 0), 0.5, 1.5, 2.0)
    pc = _sev_penalty_agent(flags.get("pure_calc_bias", 0), 0.3, 1.0, 1.5)
    dg = _sev_penalty_agent(flags.get("pedagogical_depth_gap", 0), 0.3, 1.0, 1.5)
    accuracy -= fd + pc + dg
    if abs(int(flags.get("pure_calc_bias", 0))) >= 2:
        score_cap = min(score_cap, 2.5)
    brevity = int(flags.get("brevity", 0))
    if abs(brevity) == 3:
        score_cap = min(score_cap, 1.0)
    cb = _sev_penalty_agent(brevity, 0.5, 1.5, 3.0)
    sc = _sev_penalty_agent(flags.get("superficial", 0), 0.5, 1.5, 2.0)
    mc = _sev_penalty_agent(flags.get("missing_core_concepts", 0), 0.3, 1.0, 1.5)
    bw = _sev_penalty_agent(flags.get("breadth_without_depth", 0), 0.2, 0.5, 1.0)
    accuracy -= cb + sc + mc + bw
    tm = _sev_penalty_agent(flags.get("title_mismatch", 0), 0.5, 2, 4)
    va = _sev_penalty_agent(flags.get("visual_alignment", 0), 0.0, 0.5, 1.0)
    accuracy -= tm + va
    crit_errors = int(flags.get("critical_errors", 0))
    minor_slips = int(flags.get("minor_slips", 0))
    accuracy -= crit_errors * 0.5 + minor_slips * 0.2
    accuracy = round(min(score_cap, max(0.0, accuracy)), 2)
    n_bonus = _count_plus_one_levels(
        flags.get("formula_dumping", 0),
        flags.get("pure_calc_bias", 0),
        flags.get("superficial", 0),
        flags.get("breadth_without_depth", 0),
        flags.get("visual_alignment", 0),
    )
    accuracy = _apply_bonus_toward_five(accuracy, n_bonus, N_BONUS_FIELDS_ACCURACY)
    return clip_score_1_5(accuracy), 0


def calculate_logic(flags):
    """Matches batch _calculate_agent2_scores logic arm."""
    logic = 4.0
    logic_cap = 4.0
    flow = str(flags.get("logic_flow", "") or "").lower()
    if (
        "formula_dump" in flow
        or "formula_to_solving" in flow
        or "formula-to-solving" in flow
        or "formula first" in flow
    ):
        logic_cap = 2.0
    if abs(int(flags.get("pure_calc_bias", 0))) >= 2:
        logic_cap = min(logic_cap, 2.5)
    brevity = int(flags.get("brevity", 0))
    if abs(brevity) == 3:
        logic_cap = min(logic_cap, 1.0)
    fd = _sev_penalty_agent(flags.get("formula_dumping", 0), 0.5, 1.5, 2.0)
    pc = _sev_penalty_agent(flags.get("pure_calc_bias", 0), 0.3, 1.0, 1.5)
    dg = _sev_penalty_agent(flags.get("pedagogical_depth_gap", 0), 0.3, 1.0, 1.5)
    cb = _sev_penalty_agent(brevity, 0.5, 1.5, 3.0)
    sc = _sev_penalty_agent(flags.get("superficial", 0), 0.5, 1.5, 2.0)
    mc = _sev_penalty_agent(flags.get("missing_core_concepts", 0), 0.3, 1.0, 1.5)
    bw = _sev_penalty_agent(flags.get("breadth_without_depth", 0), 0.2, 0.5, 1.0)
    logic -= fd + pc + dg + cb + sc + mc + bw
    ll = int(flags.get("logic_leaps", 0))
    pv = int(flags.get("prereq_violations", 0))
    ci = int(flags.get("causal_inconsistencies", 0))
    io = int(flags.get("information_overload", 0))
    logic -= ll * 0.5 + pv * 0.5 + ci * 0.4 + io * 0.2
    logic = round(min(logic_cap, max(0.0, logic)), 2)
    n_bonus = _count_plus_one_levels(
        flags.get("formula_dumping", 0),
        flags.get("pure_calc_bias", 0),
        flags.get("superficial", 0),
        flags.get("breadth_without_depth", 0),
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
        flags.get("jargon_level", 0),
        flags.get("prerequisite_level", 0),
        flags.get("pacing_level", 0),
        flags.get("contrast_level", 0),
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
    score -= _calc_penalty_disconnect(flags.get("disconnect_level", 0))
    score -= _calc_penalty_standard(flags.get("decorative_eye_candy_level", 0))
    score = max(0.0, min(4.0, round(score, 2)))
    n_bonus = _count_plus_one_levels(
        flags.get("monotone_level", 0),
        flags.get("ai_fatigue_level", 0),
        flags.get("clutter_level", 0),
        flags.get("disconnect_level", 0),
        flags.get("decorative_eye_candy_level", 0),
    )
    score = _apply_bonus_toward_five(score, n_bonus, N_BONUS_FIELDS_ENGAGEMENT)
    return clip_score_1_5(score), 0

# ==============================================================================
# UI HELPERS
# ==============================================================================

# Left → right: severe → beyond expectation (reversed from +1-first order)
LEVEL_OPTIONS = [-3, -2, -1, 0, 1]


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


def render_compact_selector(label, key, help_text, scores_desc=None, scale_type="behavioral", default=0):
    """
    Segmented control for agent scale: 1, 0, -1, -2, -3 (matches batch_audit_processor).
    """
    st.markdown(f"**{label}**")
    st.caption(scores_desc if scores_desc else help_text)
    d = default if default in LEVEL_OPTIONS else 0
    scale_labels = t("scale")
    val = st.segmented_control(
        label,
        options=LEVEL_OPTIONS,
        format_func=lambda x, labels=scale_labels: labels.get(x, str(x)),
        default=d,
        key=key,
        label_visibility="collapsed",
    )
    return val if val is not None else d

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

def render_ai_feedback(persona_data: dict):
    """Render AI audit feedback: scores + rationale + audit_log + suggestions."""
    ai_scores = persona_data.get("ai_scores", {})
    st.markdown("**Scores**")
    c1, c2, c3, c4 = st.columns(4)
    for col, (k, v) in zip([c1, c2, c3, c4], [("Accuracy", "acc"), ("Logic", "log"), ("Adaptability", "adt"), ("Engagement", "eng")]):
        with col:
            st.metric(k, ai_scores.get(v, "-"))
    ai_fb = persona_data.get("ai_feedback")
    agent2 = {}
    if ai_fb:
        agent2 = ai_fb.get("agent2", {})
    json_file = persona_data.get("json_file")
    if json_file and Path(json_file).exists():
        try:
            with open(json_file, encoding="utf-8") as f:
                raw = json.load(f)
            agent2_raw = raw.get("agent2_gap_analysis_judge", {})
            for key in ("pedagogical_depth", "completeness", "accuracy_flags", "logic_flags"):
                if key in agent2_raw and (not agent2.get(key)):
                    agent2[key] = agent2_raw[key]
        except Exception:
            pass
    if not ai_fb and not agent2:
        st.caption(t("ai_audit_caption"))
        return
    subj = (ai_fb or {}).get("subjective", {})
    agent1 = (ai_fb or {}).get("agent1", {})
    if agent2.get("scoring_rationale"):
        st.markdown("**Scoring rationale**")
        st.caption(agent2["scoring_rationale"])
    def _render_section(section: dict, title: str):
        if not section:
            return
        st.markdown(f"**{title}**")
        for k, v in section.items():
            if v is None or v == "":
                continue
            label = k.replace("_", " ").title()
            if isinstance(v, (int, float)):
                st.caption(f"  {label}: {v}")
            elif isinstance(v, str):
                st.caption(f"  {label}: {v}")
            else:
                st.caption(f"  {label}: {v}")
        st.write("")
    with st.expander("Agent 2: Pedagogical depth, Completeness, Accuracy & Logic flags", expanded=True):
        _render_section(agent2.get("pedagogical_depth"), "Pedagogical depth")
        _render_section(agent2.get("completeness"), "Completeness")
        _render_section(agent2.get("accuracy_flags"), "Accuracy flags")
        _render_section(agent2.get("logic_flags"), "Logic flags")
    if agent2.get("verified_errors"):
        with st.expander("Verified errors", expanded=False):
            for err in agent2["verified_errors"]:
                desc = err.get("description", "")
                st.markdown(f"- **{err.get('timestamp', '')}** ({err.get('type', '')}): {desc}")
    audit = subj.get("audit_log", {})
    if audit:
        with st.expander("Adaptability & engagement flags", expanded=False):
            for section, title in [(audit.get("adaptability_flags", {}), "Adaptability"), (audit.get("engagement_flags", {}), "Engagement")]:
                st.markdown(f"*{title}*")
                for k, v in section.items():
                    if "_evidence" in k:
                        st.caption(f"  {v[:200]}{'...' if len(str(v)) > 200 else ''}")
                    elif "_level" in k:
                        st.caption(f"**{k.replace('_level','').replace('_',' ').title()}**: {v}")
    if subj.get("top_fix_suggestion"):
        st.markdown("**Top fix suggestion**")
        st.info(subj["top_fix_suggestion"])
    if agent1.get("observation_summary"):
        st.markdown("**Observation summary**")
        st.caption(agent1["observation_summary"][:300] + ("..." if len(agent1["observation_summary"]) > 300 else ""))

def render_persona_header(persona_str: str):
    """Renders persona as a single concatenated string (no tags)."""
    st.caption(persona_str)

# ==============================================================================
# DATA LOADING
# ==============================================================================

def _load_from_input_json():
    """Load from human_eval_input.json (2 test entries with full AI feedback)."""
    if not INPUT_JSON.exists():
        return None
    try:
        with open(INPUT_JSON, encoding="utf-8") as f:
            entries = json.load(f)
        video_groups = []
        for entry in entries:
            json_path = (BASE_DIR / entry["json_path"]).resolve()
            video_url = entry["video_url"]
            if not json_path.exists():
                print(f"   ⚠️  human_eval_input.json: JSON not found: {json_path}")
                continue
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("_meta", {})
            agent2 = data.get("agent2_gap_analysis_judge", {})
            subj = data.get("subjective_evaluation", {})
            agent1 = data.get("agent1_content_analyst", {})
            video_info = {
                "video_url": video_url,
                "title_en": meta.get("title_en", "Unknown"),
                "category": meta.get("category", ""),
                "personas": [{
                    "student_persona": meta.get("student_persona", ""),
                    "json_file": str(json_path),
                    "ai_scores": {
                        "acc": agent2.get("accuracy_score", 0),
                        "log": agent2.get("logic_score", 0),
                        "adt": subj.get("adaptability", {}).get("score", 0),
                        "eng": subj.get("engagement", {}).get("score", 0),
                    },
                    "ai_feedback": {
                        "agent2": {
                            "score_breakdown": agent2.get("score_breakdown", {}),
                            "scoring_rationale": agent2.get("scoring_rationale", ""),
                            "verified_errors": agent2.get("verified_errors", []),
                            "pedagogical_depth": agent2.get("pedagogical_depth", {}),
                            "completeness": agent2.get("completeness", {}),
                            "accuracy_flags": agent2.get("accuracy_flags", {}),
                            "logic_flags": agent2.get("logic_flags", {}),
                        },
                        "subjective": {
                            "audit_log": subj.get("audit_log", {}),
                            "top_fix_suggestion": subj.get("top_fix_suggestion", ""),
                            "cognitive_friction": subj.get("experiential_context", {}).get("cognitive_friction_points", []),
                            "positive_moment": subj.get("experiential_context", {}).get("positive_moment", {}),
                        },
                        "agent1": {
                            "observation_summary": agent1.get("observation_summary", ""),
                            "potential_issues": agent1.get("potential_issues", []),
                        },
                    },
                }],
            }
            video_groups.append(video_info)
        return video_groups if video_groups else None
    except Exception as e:
        st.error(f"Error loading input JSON: {e}")
        return None

def load_evaluation_data():
    """Load data: prefer human_eval_input.json, else fall back to CSV."""
    groups = _load_from_input_json()
    if groups:
        if "data_source" not in st.session_state:
            st.session_state.data_source = "human_eval_input.json"
        return groups
    if "data_source" not in st.session_state:
        st.session_state.data_source = "CSV"
    if not CSV_PATH.exists():
        return None
    try:
        return _load_csv_data()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

@st.cache_data
def _load_csv_data():
    """Cached CSV load for large datasets."""
    df = pd.read_csv(CSV_PATH)
    video_groups = []
    for video_url, group in df.groupby("video_url", sort=False):
        first_row = group.iloc[0]
        video_info = {
            "video_url": video_url,
            "title_en": first_row["title_en"],
            "category": first_row["category"],
            "personas": [],
        }
        for _, row in group.iterrows():
            video_info["personas"].append({
                "student_persona": row["student_persona"],
                "json_file": row["json_file"],
                "ai_scores": {
                    "acc": row["accuracy"],
                    "log": row["logic"],
                    "adt": row["adaptability"],
                    "eng": row["engagement"],
                },
            })
        video_groups.append(video_info)
    return video_groups

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
        lf = first.get("logic_flow", "Concrete/Inductive (Good)")
        try:
            logic_flow_s = str(lf) if not pd.isna(lf) else "Concrete/Inductive (Good)"
        except TypeError:
            logic_flow_s = str(lf or "Concrete/Inductive (Good)")
        obj = {
            "formula_dumping": _normalize_agent_level(first.get("formula_dumping", 0), schema_v),
            "pure_calc_bias": _normalize_agent_level(first.get("pure_calc_bias", 0), schema_v),
            "pedagogical_depth_gap": _normalize_agent_level(first.get("pedagogical_depth_gap", 0), schema_v),
            "brevity": _normalize_agent_level(first.get("brevity", 0), schema_v),
            "superficial": _normalize_agent_level(first.get("superficial", 0), schema_v),
            "missing_core_concepts": _normalize_agent_level(first.get("missing_core_concepts", 0), schema_v),
            "breadth_without_depth": _normalize_agent_level(first.get("breadth_without_depth", 0), schema_v),
            "title_mismatch": _normalize_agent_level(first.get("title_mismatch", 0), schema_v),
            "visual_alignment": _normalize_agent_level(first.get("visual_alignment", 0), schema_v),
            "critical_errors": _csv_int(first.get("critical_errors", 0), 0),
            "minor_slips": _csv_int(first.get("minor_slips", 0), 0),
            "logic_flow": logic_flow_s,
            "logic_leaps": _csv_int(first.get("logic_leaps", 0), 0),
            "prereq_violations": _csv_int(first.get("prereq_violations", 0), 0),
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

    # Sidebar Navigation
    video_groups = load_evaluation_data()
    if not video_groups:
        st.error(t('no_data'))
        return

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
        st.caption(f"Data: {st.session_state.get('data_source', '?')}")
        st.write("---")
        st.write(f"{t('user')}: **{st.session_state.username}**")
        total_videos = len(video_groups)
        idx = st.number_input(t('video_index'), 0, total_videos-1, st.session_state.current_index)
        st.session_state.current_index = idx
        st.progress((idx+1)/total_videos)
        
        current_video = video_groups[idx]
        st.caption(f"{t('current')}: {current_video['title_en']}")

    # Main Content
    st.header(f"📹 {current_video['title_en']}")
    
    col_vid, col_form = st.columns([1, 1])
    
    with col_vid:
        st.video(current_video['video_url'])
        with st.expander(t('ai_audit'), expanded=False):
            render_ai_feedback(current_video['personas'][0])

    with col_form:
        st.caption(t('rating_scale_caption'))
        st.caption(t('scale_legend'))
        with st.expander(t('scale_rubric_title'), expanded=True):
            st.markdown(t('scale_rubric_md'))
        st.write("---")
        
        # Load saved evaluation for this user + video (when going back)
        saved = load_saved_for_video(st.session_state.username, current_video['video_url'])
        so = saved["obj"] if saved else None
        sp_list = saved["personas"] if saved else []
        
        # Tab-First Layout: Tab 0 = Objective, Tabs 1..N = Persona
        tab_labels = [t('tab_objective')] + [
            f"👤 P{i+1}" for i in range(len(current_video['personas']))
        ]
        all_tabs = st.tabs(tab_labels)
        
        all_evals = []
        obj_flags = None  # Set in Objective tab, used in Persona tabs
        
        # ----- Tab 0: Objective (Accuracy & Logic) -----
        # Use idx in keys so scores reset when advancing to next video
        k = lambda s: f"{s}_{idx}"
        with all_tabs[0]:
            st.caption(t('obj_caption'))
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"#### {t('pedagogical')}")
                f_dump = render_compact_selector(t('formula_dumping'), k("f_dump"), t('formula_dumping_help'), t('scores_f_dump'), "severity", default=(so.get("formula_dumping", 0) if so else 0))
                pure_calc = render_compact_selector(t('pure_calc'), k("p_calc"), t('pure_calc_help'), t('scores_p_calc'), "severity", default=(so.get("pure_calc_bias", 0) if so else 0))
                depth_gap = render_compact_selector(t('depth_gap'), k("depth_gap"), t('depth_gap_help'), t('scores_depth_gap'), "severity", default=(so.get("pedagogical_depth_gap", 0) if so else 0))
                st.markdown(f"#### {t('completeness')}")
                brevity = render_compact_selector(t('brevity'), k("brev"), t('brevity_help'), t('scores_brevity'), "severity", default=(so.get("brevity", 0) if so else 0))
                superficial = render_compact_selector(t('superficial'), k("super"), t('superficial_help'), t('scores_superficial'), "severity", default=(so.get("superficial", 0) if so else 0))
                missing_core = render_compact_selector(t('missing_core'), k("miss_core"), t('missing_core_help'), t('scores_missing_core'), "severity", default=(so.get("missing_core_concepts", 0) if so else 0))
                breadth_no_depth = render_compact_selector(t('breadth_no_depth'), k("breadth_nd"), t('breadth_no_depth_help'), t('scores_breadth_no_depth'), "severity", default=(so.get("breadth_without_depth", 0) if so else 0))
            with c2:
                st.markdown(f"#### {t('accuracy_checks')}")
                t_mismatch = render_compact_selector(t('title_mismatch'), k("t_mis"), t('title_mismatch_help'), t('scores_t_mismatch'), "severity", default=(so.get("title_mismatch", 0) if so else 0))
                v_align = render_compact_selector(t('visual_alignment'), k("v_align"), t('visual_alignment_help'), t('scores_v_align'), "severity", default=(so.get("visual_alignment", 0) if so else 0))
                st.markdown(f"#### {t('error_counts')}")
                crit_err = st.number_input(t('critical_errors'), 0, 10, (so.get("critical_errors", 0) if so else 0), key=k("crit_err"))
                minor_slip = st.number_input(t('minor_slips'), 0, 10, (so.get("minor_slips", 0) if so else 0), key=k("minor_slip"))
            st.markdown(f"#### {t('logic_checks')}")
            flow_opts = t('logic_flow_opts')
            flow_idx = _logic_flow_index(flow_opts, so.get("logic_flow", "Concrete/Inductive (Good)")) if so else 0
            l_flow_display = st.selectbox(t('logic_flow'), flow_opts, index=flow_idx, key=k("logic_flow"))
            l_flow = LOGIC_FLOW_MAP.get(l_flow_display, l_flow_display)
            logic_leaps = st.number_input(t('logic_leaps'), 0, 10, (so.get("logic_leaps", 0) if so else 0), key=k("logic_leaps"))
            prereq_viol = st.number_input(t('prereq_violations'), 0, 10, (so.get("prereq_violations", 0) if so else 0), key=k("prereq_viol"))
            causal_inc = st.number_input(t('causal_inconsistencies'), 0, 10, (so.get("causal_inconsistencies", 0) if so else 0), key=k("causal_inc"))
            info_over = st.number_input(t('info_overload'), 0, 20, (so.get("information_overload", 0) if so else 0), key=k("info_over"))

            obj_flags = {
                'formula_dumping': f_dump, 'pure_calc_bias': pure_calc,
                'pedagogical_depth_gap': depth_gap,
                'brevity': brevity, 'superficial': superficial,
                'missing_core_concepts': missing_core, 'breadth_without_depth': breadth_no_depth,
                'title_mismatch': t_mismatch, 'visual_alignment': v_align,
                'critical_errors': crit_err, 'minor_slips': minor_slip,
                'logic_flow': l_flow, 'logic_leaps': logic_leaps,
                'prereq_violations': prereq_viol, 'causal_inconsistencies': causal_inc,
                'information_overload': info_over,
            }
            acc_score, _ = calculate_accuracy(obj_flags)
            log_score, _ = calculate_logic(obj_flags)
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Accuracy", acc_score)
            with m2:
                st.metric("Logic", log_score)
        
        # ----- Tabs 1..N: Persona (Subjective) -----
        for i, (tab, p_data) in enumerate(zip(all_tabs[1:], current_video['personas'])):
            sp = sp_list[i] if i < len(sp_list) else None
            with tab:
                render_persona_header(p_data['student_persona'])
                # Two-column: c1 = Adaptability, c2 = Engagement (keys include idx for reset on advance)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(t('adaptability_flags'))
                    jargon = render_compact_selector(t('jargon'), f"jargon_{idx}_{i}", t('jargon_help'), t('scores_jargon'), "behavioral", default=sp["jargon_level"] if sp else 0)
                    prereq = render_compact_selector(t('prereq_gap'), f"prereq_{idx}_{i}", t('prereq_gap_help'), t('scores_prereq'), "behavioral", default=sp["prerequisite_level"] if sp else 0)
                    pacing = render_compact_selector(t('pacing'), f"pacing_{idx}_{i}", t('pacing_help'), t('scores_pacing'), "behavioral", default=sp["pacing_level"] if sp else 0)
                    contrast = render_compact_selector(t('illegible'), f"cont_{idx}_{i}", t('illegible_help'), t('scores_illegible'), "frequency", default=sp["contrast_level"] if sp else 0)
                    scaffolding = render_compact_selector(t('scaffolding'), f"scaff_{idx}_{i}", t('scaffolding_help'), t('scores_scaffold'), "behavioral", default=sp["scaffolding_level"] if sp else 0)
                    ineffective_visual = render_compact_selector(
                        t('ineffective_visual'),
                        f"ineff_vis_{idx}_{i}",
                        t('ineffective_visual_help'),
                        t('scores_ineffective_visual'),
                        "frequency",
                        default=(sp.get("ineffective_visual_level", 0) if sp else 0),
                    )
                with c2:
                    st.markdown(t('engagement_flags'))
                    monotone = render_compact_selector(t('monotone'), f"mono_{idx}_{i}", t('monotone_help'), t('scores_monotone'), "behavioral", default=sp["monotone_level"] if sp else 0)
                    ai_fatigue = render_compact_selector(t('ai_fatigue'), f"ai_{idx}_{i}", t('ai_fatigue_help'), t('scores_ai_fatigue'), "behavioral", default=sp["ai_fatigue_level"] if sp else 0)
                    clutter = render_compact_selector(t('clutter'), f"clut_{idx}_{i}", t('clutter_help'), t('scores_clutter'), "frequency", default=sp["clutter_level"] if sp else 0)
                    disconnect = render_compact_selector(t('disconnect'), f"disc_{idx}_{i}", t('disconnect_help'), t('scores_disconnect'), "behavioral", default=sp["disconnect_level"] if sp else 0)
                    decorative_eye_candy = render_compact_selector(
                        t('decorative_eye_candy'),
                        f"eye_candy_{idx}_{i}",
                        t('decorative_eye_candy_help'),
                        t('scores_decorative_eye_candy'),
                        "frequency",
                        default=(sp.get("decorative_eye_candy_level", 0) if sp else 0),
                    )

                subj_flags = {
                    'jargon_level': jargon, 'prerequisite_level': prereq, 'pacing_level': pacing,
                    'contrast_level': contrast, 'scaffolding_level': scaffolding,
                    'ineffective_visual_level': ineffective_visual,
                    'monotone_level': monotone, 'ai_fatigue_level': ai_fatigue,
                    'clutter_level': clutter, 'disconnect_level': disconnect,
                    'decorative_eye_candy_level': decorative_eye_candy,
                }
                adt_score, _ = calculate_adaptability(subj_flags)
                eng_score, _ = calculate_engagement(subj_flags)
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Adaptability", adt_score)
                with m2:
                    st.metric("Engagement", eng_score)
                
                feedback = st.text_area(t('optional_comments'), value=sp["feedback"] if sp else "", key=f"feed_{idx}_{i}")
                
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

        # SUBMIT BUTTON (outside tabs)
        st.write("---")
        if st.button(t('save_evals'), type="primary", use_container_width=True):
            save_detailed_evaluation(all_evals)
            st.toast(t('saved_toast'))
            # Auto-advance to next video (scores reset via key suffix)
            if idx < total_videos - 1:
                st.session_state.current_index = idx + 1
            st.rerun()

if __name__ == "__main__":
    main()