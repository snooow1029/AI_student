#!/usr/bin/env python3
"""
Streamlit Human-Eval Interface for Educational Video Assessment (Deduction Logic Version)
Humans fill out the exact same checklists as Agents, and scores are calculated deterministically.
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

# Constants
BASE_DIR = Path(__file__).parent.parent
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
        'completeness': "Completeness",
        'brevity': "Content Brevity",
        'brevity_help': "Too thin/short for topic.",
        'superficial': "Superficial Coverage",
        'superficial_help': "Mentions topics without explaining.",
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
        'engagement_flags': "#### ⚡ Engagement Flags (Motivation)",
        'monotone': "6. Monotone Audio",
        'monotone_help': "Robotic/Flat voice.",
        'ai_fatigue': "7. AI Fatigue",
        'ai_fatigue_help': "Generic/Inauthentic visuals.",
        'clutter': "8. Visual Clutter",
        'clutter_help': "Too much text/chaos.",
        'disconnect': "9. AV Disconnect",
        'disconnect_help': "Visuals don't match audio.",
        'subj_calc': "🧮 Calculated Score: **Adaptability: {adt}** | **Engagement: {eng}**",
        'optional_comments': "Optional Comments",
        'save_evals': "💾 Save All Evaluations",
        'saved_toast': "✅ Evaluation Saved!",
        # Unified level scale (legend shown above; options show 0-3 only)
        'scale_legend': "0 None · 1 Minor · 2 Mod · 3 Severe",
        'scale': {0: "0", 1: "1", 2: "2", 3: "3"},
        'tab_objective': "📐 Objective",
        # Per-criteria score descriptions (0-3)
        'scores_f_dump': "0: Full derivation | 1: Partial | 2: Minimal | 3: None",
        'scores_p_calc': "0: Balanced | 1: Some calc | 2: Mostly calc | 3: >70% calc",
        'scores_brevity': "0: Adequate | 1: Slightly thin | 2: Too short | 3: Inadequate",
        'scores_superficial': "0: Deep | 1: Some depth | 2: Surface only | 3: Just mentions",
        'scores_t_mismatch': "0: Matches | 1: Minor drift | 2: Notable gap | 3: Misleading",
        'scores_v_align': "0: Synced | 1: Minor mismatch | 2: Often off | 3: Disconnected",
        'scores_jargon': "0: All defined | 1: 1–2 undefined | 2: Several | 3: Many",
        'scores_prereq': "0: No gap | 1: Minor | 2: Notable | 3: Blocking",
        'scores_pacing': "0: Good fit | 1: Slight mismatch | 2: Too fast/slow | 3: Unusable",
        'scores_illegible': "0: Clear | 1: 1 slide | 2: 2 slides | 3: 3+ slides",
        'scores_scaffold': "0: Rich | 1: Some | 2: Sparse | 3: None",
        'scores_monotone': "0: Natural | 1: Slight | 2: Flat | 3: Robotic",
        'scores_ai_fatigue': "0: Authentic | 1: Minor | 2: Generic | 3: Off-putting",
        'scores_clutter': "0: Clean | 1: 1 slide | 2: 2 slides | 3: 3+ slides",
        'scores_disconnect': "0: Synced | 1: Minor | 2: Often off | 3: Disconnected",
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
        'completeness': "完整性",
        'brevity': "內容過簡",
        'brevity_help': "對該主題而言過於精簡。",
        'superficial': "表面涵蓋",
        'superficial_help': "僅提及主題但未解釋。",
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
        'engagement_flags': "#### ⚡ 投入度指標（動機）",
        'monotone': "6. 單調語音",
        'monotone_help': "機械化/平淡的聲音。",
        'ai_fatigue': "7. AI 疲勞感",
        'ai_fatigue_help': "通用/不真實的視覺。",
        'clutter': "8. 視覺雜亂",
        'clutter_help': "文字過多或混亂。",
        'disconnect': "9. 影音脫節",
        'disconnect_help': "畫面與語音不匹配。",
        'subj_calc': "🧮 計算分數：**適應性：{adt}** | **投入度：{eng}**",
        'optional_comments': "選填意見",
        'save_evals': "💾 儲存所有評測",
        'saved_toast': "✅ 評測已儲存！",
        # Unified level scale (legend shown above; options show 0-3 only)
        'scale_legend': "0 無 · 1 輕微 · 2 中度 · 3 嚴重",
        'rating_scale_caption': "📝 評分：**0** 無 · **1** 輕微 · **2** 中度 · **3** 嚴重",
        'scale': {0: "0", 1: "1", 2: "2", 3: "3"},
        'tab_objective': "📐 客觀",
        'scores_f_dump': "0: 完整推導 | 1: 部分 | 2: 極少 | 3: 無",
        'scores_p_calc': "0: 平衡 | 1: 偏計算 | 2: 多為計算 | 3: >70% 計算",
        'scores_brevity': "0: 足夠 | 1: 略簡 | 2: 過短 | 3: 不足",
        'scores_superficial': "0: 深入 | 1: 有深度 | 2: 表面 | 3: 僅提及",
        'scores_t_mismatch': "0: 相符 | 1: 略偏 | 2: 明顯不符 | 3: 誤導",
        'scores_v_align': "0: 同步 | 1: 略偏 | 2: 常不符 | 3: 脫節",
        'scores_jargon': "0: 全定義 | 1: 1–2 未定義 | 2: 多個 | 3: 許多",
        'scores_prereq': "0: 無落差 | 1: 輕微 | 2: 明顯 | 3: 阻礙",
        'scores_pacing': "0: 合適 | 1: 略不匹配 | 2: 過快/慢 | 3: 難用",
        'scores_illegible': "0: 清晰 | 1: 1 張 | 2: 2 張 | 3: 3+ 張",
        'scores_scaffold': "0: 豐富 | 1: 有 | 2: 稀少 | 3: 無",
        'scores_monotone': "0: 自然 | 1: 略平 | 2: 平淡 | 3: 機械",
        'scores_ai_fatigue': "0: 真實 | 1: 輕微 | 2: 通用 | 3: 反感",
        'scores_clutter': "0: 簡潔 | 1: 1 張 | 2: 2 張 | 3: 3+ 張",
        'scores_disconnect': "0: 同步 | 1: 輕微 | 2: 常不符 | 3: 脫節",
    }
}
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

def _sev_penalty(level, p1=0.5, p2=1.0, p3=2.0):
    """Severity → penalty: level 1/2/3 → p1/p2/p3 (matches batch_audit_processor)"""
    level = int(level) if isinstance(level, (int, float)) else 0
    return [0, p1, p2, p3][min(level, 3)]

def calculate_accuracy(flags):
    """
    Accuracy score - matches batch_audit_processor._calculate_agent2_scores.
    Human form fields: formula_dumping, pure_calc_bias, brevity, superficial,
    title_mismatch, visual_alignment, critical_errors, minor_slips.
    Missing fields (pedagogical_depth_gap, missing_core_concepts, breadth_without_depth) default to 0.
    """
    accuracy = 5.0
    score_cap = 5.0
    fd = _sev_penalty(flags.get('formula_dumping', 0), 0.5, 1.5, 2.0)
    pc = _sev_penalty(flags.get('pure_calc_bias', 0), 0.3, 1.0, 1.5)
    dg = _sev_penalty(flags.get('pedagogical_depth_gap', 0), 0.3, 1.0, 1.5)
    accuracy -= fd + pc + dg
    if int(flags.get('pure_calc_bias', 0)) >= 2:
        score_cap = min(score_cap, 3.5)
    brevity = int(flags.get('brevity', 0))
    if brevity == 3:
        score_cap = min(score_cap, 2.0)
    cb = _sev_penalty(brevity, 0.5, 1.5, 3.0)
    sc = _sev_penalty(flags.get('superficial', 0), 0.5, 1.5, 2.0)
    mc = _sev_penalty(flags.get('missing_core_concepts', 0), 0.3, 1.0, 1.5)
    bw = _sev_penalty(flags.get('breadth_without_depth', 0), 0.2, 0.5, 1.0)
    accuracy -= cb + sc + mc + bw
    tm = _sev_penalty(flags.get('title_mismatch', 0), 0.5, 2, 4)
    va = _sev_penalty(flags.get('visual_alignment', 0), 0.0, 0.5, 1.0)
    accuracy -= tm + va
    crit_errors = int(flags.get('critical_errors', 0))
    minor_slips = int(flags.get('minor_slips', 0))
    accuracy -= crit_errors * 0.5 + minor_slips * 0.2
    accuracy = round(min(score_cap, max(1.0, accuracy)), 2)
    return accuracy, 0

def calculate_logic(flags):
    """
    Logic score - matches batch_audit_processor._calculate_agent2_scores.
    """
    logic = 5.0
    logic_cap = 5.0
    flow = str(flags.get('logic_flow', '') or '').lower()
    if 'formula first' in flow or 'formula_dump' in flow or 'formula_to_solving' in flow or 'formula-to-solving' in flow:
        logic_cap = 3.0
    if int(flags.get('pure_calc_bias', 0)) >= 2:
        logic_cap = min(logic_cap, 3.5)
    brevity = int(flags.get('brevity', 0))
    if brevity == 3:
        logic_cap = min(logic_cap, 2.0)
    fd = _sev_penalty(flags.get('formula_dumping', 0), 0.5, 1.5, 2.0)
    pc = _sev_penalty(flags.get('pure_calc_bias', 0), 0.3, 1.0, 1.5)
    dg = _sev_penalty(flags.get('pedagogical_depth_gap', 0), 0.3, 1.0, 1.5)
    cb = _sev_penalty(brevity, 0.5, 1.5, 3.0)
    sc = _sev_penalty(flags.get('superficial', 0), 0.5, 1.5, 2.0)
    mc = _sev_penalty(flags.get('missing_core_concepts', 0), 0.3, 1.0, 1.5)
    bw = _sev_penalty(flags.get('breadth_without_depth', 0), 0.2, 0.5, 1.0)
    logic -= fd + pc + dg + cb + sc + mc + bw
    ll = int(flags.get('logic_leaps', 0))
    pv = int(flags.get('prereq_violations', 0))
    ci = int(flags.get('causal_inconsistencies', 0))
    io = int(flags.get('information_overload', 0))
    logic -= ll * 0.5 + pv * 0.5 + ci * 0.4 + io * 0.2
    logic = round(min(logic_cap, max(1.0, logic)), 2)
    return logic, 0

def _adapt_penalty(level):
    """Standard penalty: 1→0.3, 2→0.6, 3→1.0 (matches batch)"""
    level = int(level) if isinstance(level, (int, float)) else 0
    return [0, 0.3, 0.6, 1.0][min(level, 3)]

def _monotone_penalty(level):
    """Monotone: 1→0.5, 2→1.0, 3→1.5 (matches batch)"""
    level = int(level) if isinstance(level, (int, float)) else 0
    return [0, 0.5, 1.0, 1.5][min(level, 3)]

def _disconnect_penalty(level):
    """Disconnect: 1→0.5, 2→1.0, 3→1.5 (matches batch)"""
    level = int(level) if isinstance(level, (int, float)) else 0
    return [0, 0.5, 1.0, 1.5][min(level, 3)]

def calculate_adaptability(flags):
    """
    Adaptability score - matches batch_audit_processor._calculate_deterministic_scores.
    contrast_level maps to visual_accessibility; scaffolding_level to missing_scaffolding.
    """
    score = 5.0
    score -= _adapt_penalty(flags.get('jargon_level', 0))
    score -= _adapt_penalty(flags.get('prerequisite_level', 0))
    score -= _adapt_penalty(flags.get('pacing_level', 0))
    score -= _adapt_penalty(flags.get('scaffolding_level', 0))
    va = int(flags.get('contrast_level', 0) or 0)
    if va == 1:
        score -= 0.3
    elif va == 2:
        score -= 0.6
    elif va >= 3:
        score -= 1.0
    return max(0.0, min(5.0, round(score, 2))), 0

def calculate_engagement(flags):
    """
    Engagement score - matches batch_audit_processor._calculate_deterministic_scores.
    monotone and disconnect use higher penalties.
    """
    score = 5.0
    score -= _monotone_penalty(flags.get('monotone_level', 0))
    score -= _adapt_penalty(flags.get('ai_fatigue_level', 0))
    score -= _adapt_penalty(flags.get('clutter_level', 0))
    score -= _disconnect_penalty(flags.get('disconnect_level', 0))
    return max(0.0, min(5.0, round(score, 2))), 0

# ==============================================================================
# UI HELPERS
# ==============================================================================

# Format for segmented control: only 0-3
SEGMENTED_FORMAT = {0: "0", 1: "1", 2: "2", 3: "3"}
SEGMENTED_FORMAT_CH = {0: "0", 1: "1", 2: "2", 3: "3"}

def render_compact_selector(label, key, help_text, scores_desc=None, scale_type="behavioral"):
    """
    Renders a horizontal segmented control for 0-3 levels.
    scores_desc: optional per-criteria 0-3 level descriptions.
    """
    fmt = SEGMENTED_FORMAT_CH if st.session_state.lang == 'ch' else SEGMENTED_FORMAT
    st.markdown(f"**{label}**")
    st.caption(scores_desc if scores_desc else help_text)
    val = st.segmented_control(
        label,
        options=[0, 1, 2, 3],
        format_func=lambda x: fmt[x],
        default=0,
        key=key,
        label_visibility="collapsed"
    )
    return val if val is not None else 0

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
            json_path = BASE_DIR / entry["json_path"]
            video_url = entry["video_url"]
            if not json_path.exists():
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
        return groups
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
        st.write("---")
        
        # Tab-First Layout: Tab 0 = Objective, Tabs 1..N = Persona
        tab_labels = [t('tab_objective')] + [
            f"👤 P{i+1}" for i in range(len(current_video['personas']))
        ]
        all_tabs = st.tabs(tab_labels)
        
        all_evals = []
        obj_flags = None  # Set in Objective tab, used in Persona tabs
        
        # ----- Tab 0: Objective (Accuracy & Logic) -----
        with all_tabs[0]:
            st.caption(t('obj_caption'))
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"#### {t('pedagogical')}")
                f_dump = render_compact_selector(t('formula_dumping'), "f_dump", t('formula_dumping_help'), t('scores_f_dump'), "severity")
                pure_calc = render_compact_selector(t('pure_calc'), "p_calc", t('pure_calc_help'), t('scores_p_calc'), "severity")
                st.markdown(f"#### {t('completeness')}")
                brevity = render_compact_selector(t('brevity'), "brev", t('brevity_help'), t('scores_brevity'), "severity")
                superficial = render_compact_selector(t('superficial'), "super", t('superficial_help'), t('scores_superficial'), "severity")
            with c2:
                st.markdown(f"#### {t('accuracy_checks')}")
                t_mismatch = render_compact_selector(t('title_mismatch'), "t_mis", t('title_mismatch_help'), t('scores_t_mismatch'), "severity")
                v_align = render_compact_selector(t('visual_alignment'), "v_align", t('visual_alignment_help'), t('scores_v_align'), "severity")
                st.markdown(f"#### {t('error_counts')}")
                crit_err = st.number_input(t('critical_errors'), 0, 10, 0)
                minor_slip = st.number_input(t('minor_slips'), 0, 10, 0)
            st.markdown(f"#### {t('logic_checks')}")
            flow_opts = t('logic_flow_opts')
            l_flow_display = st.selectbox(t('logic_flow'), flow_opts)
            l_flow = LOGIC_FLOW_MAP.get(l_flow_display, l_flow_display)
            logic_leaps = st.number_input(t('logic_leaps'), 0, 10, 0)
            prereq_viol = st.number_input(t('prereq_violations'), 0, 10, 0)
            causal_inc = st.number_input(t('causal_inconsistencies'), 0, 10, 0)
            
            obj_flags = {
                'formula_dumping': f_dump, 'pure_calc_bias': pure_calc,
                'brevity': brevity, 'superficial': superficial,
                'title_mismatch': t_mismatch, 'visual_alignment': v_align,
                'critical_errors': crit_err, 'minor_slips': minor_slip,
                'logic_flow': l_flow, 'logic_leaps': logic_leaps,
                'prereq_violations': prereq_viol, 'causal_inconsistencies': causal_inc
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
            with tab:
                render_persona_header(p_data['student_persona'])
                # Two-column: c1 = Adaptability, c2 = Engagement
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(t('adaptability_flags'))
                    jargon = render_compact_selector(t('jargon'), f"jargon_{i}", t('jargon_help'), t('scores_jargon'), "behavioral")
                    prereq = render_compact_selector(t('prereq_gap'), f"prereq_{i}", t('prereq_gap_help'), t('scores_prereq'), "behavioral")
                    pacing = render_compact_selector(t('pacing'), f"pacing_{i}", t('pacing_help'), t('scores_pacing'), "behavioral")
                    contrast = render_compact_selector(t('illegible'), f"cont_{i}", t('illegible_help'), t('scores_illegible'), "frequency")
                    scaffolding = render_compact_selector(t('scaffolding'), f"scaff_{i}", t('scaffolding_help'), t('scores_scaffold'), "behavioral")
                with c2:
                    st.markdown(t('engagement_flags'))
                    monotone = render_compact_selector(t('monotone'), f"mono_{i}", t('monotone_help'), t('scores_monotone'), "behavioral")
                    ai_fatigue = render_compact_selector(t('ai_fatigue'), f"ai_{i}", t('ai_fatigue_help'), t('scores_ai_fatigue'), "behavioral")
                    clutter = render_compact_selector(t('clutter'), f"clut_{i}", t('clutter_help'), t('scores_clutter'), "frequency")
                    disconnect = render_compact_selector(t('disconnect'), f"disc_{i}", t('disconnect_help'), t('scores_disconnect'), "behavioral")
                
                subj_flags = {
                    'jargon_level': jargon, 'prerequisite_level': prereq, 'pacing_level': pacing,
                    'contrast_level': contrast, 'scaffolding_level': scaffolding,
                    'monotone_level': monotone, 'ai_fatigue_level': ai_fatigue,
                    'clutter_level': clutter, 'disconnect_level': disconnect
                }
                adt_score, _ = calculate_adaptability(subj_flags)
                eng_score, _ = calculate_engagement(subj_flags)
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Adaptability", adt_score)
                with m2:
                    st.metric("Engagement", eng_score)
                
                feedback = st.text_area(t('optional_comments'), key=f"feed_{i}")
                
                eval_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'evaluator': st.session_state.username,
                    'video_url': current_video['video_url'],
                    'title_en': current_video['title_en'],
                    'student_persona': p_data['student_persona'],
                    'accuracy': acc_score, 'logic': log_score,
                    'adaptability': adt_score, 'engagement': eng_score,
                    **obj_flags,
                    **subj_flags,
                    'feedback': feedback
                }
                all_evals.append(eval_entry)

        # SUBMIT BUTTON (outside tabs)
        st.write("---")
        if st.button(t('save_evals'), type="primary", use_container_width=True):
            save_detailed_evaluation(all_evals)
            st.toast(t('saved_toast'))

if __name__ == "__main__":
    main()