#!/usr/bin/env python3
"""
Streamlit Human-Eval Interface for Educational Video Assessment
Allows human experts to review AI-generated audit logs and provide their own scores.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import os

# Configure page to wide mode
st.set_page_config(
    page_title="Human Video Evaluation",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
BASE_DIR = Path(__file__).parent.parent
CSV_PATH = BASE_DIR / "phase_2" / "merged_small_scale_summaries_20260224_014339.csv"
RESULTS_DIR = BASE_DIR / "phase_2"
HUMAN_EVAL_CSV = RESULTS_DIR / "human_eval_results.csv"

# Session state initialization
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''

def show_login_page():
    """Display login page for user authentication."""
    st.title("🎓 Human Video Evaluation System")
    st.markdown("### 👤 User Login")
    st.markdown("Please enter your name to start evaluating videos.")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input(
                "Your Name",
                placeholder="Enter your full name or ID",
                help="This will be recorded with your evaluations"
            )
            
            submitted = st.form_submit_button("🚀 Start Evaluating", use_container_width=True, type="primary")
            
            if submitted:
                if username.strip():
                    st.session_state.logged_in = True
                    st.session_state.username = username.strip()
                    st.rerun()
                else:
                    st.error("❌ Please enter your name to continue")
        
        st.markdown("---")
        st.info("""
        **📋 Instructions:**
        - Enter your name or evaluator ID
        - You will evaluate educational videos across multiple student personas
        - Your progress will be saved automatically
        - You can return later to continue from where you left off
        """)

def get_user_evaluated_videos(username):
    """Get list of video URLs that the user has already evaluated."""
    if not HUMAN_EVAL_CSV.exists():
        return set()
    
    try:
        df = pd.read_csv(HUMAN_EVAL_CSV)
        # Filter by current user
        user_evals = df[df['evaluator'] == username]
        # Return unique video URLs
        return set(user_evals['video_url'].unique())
    except Exception as e:
        st.warning(f"Error reading evaluation history: {e}")
        return set()

@st.cache_data
def load_evaluation_data():
    """Load the merged summaries CSV file and group by video."""
    try:
        df = pd.read_csv(CSV_PATH)
        
        # Group by video_url to combine personas for the same video
        video_groups = []
        for video_url, group in df.groupby('video_url', sort=False):
            # Get common video info (same across all personas)
            first_row = group.iloc[0]
            
            video_info = {
                'video_url': video_url,
                'title_en': first_row['title_en'],
                'category': first_row['category'],
                'personas': []
            }
            
            # Collect all personas for this video
            for _, row in group.iterrows():
                persona_data = {
                    'student_persona': row['student_persona'],
                    'json_file': row['json_file'],
                    'ai_accuracy': row['accuracy'],
                    'ai_logic': row['logic'],
                    'ai_adaptability': row['adaptability'],
                    'ai_engagement': row['engagement'],
                    'ai_clarity': row.get('clarity', 'N/A'),
                    'timestamp': row['timestamp']
                }
                video_info['personas'].append(persona_data)
            
            video_groups.append(video_info)
        
        return video_groups
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def sort_videos_by_user_progress(video_groups, username):
    """Sort videos to prioritize unevaluated ones for the current user."""
    if not username or not video_groups:
        return video_groups
    
    evaluated_urls = get_user_evaluated_videos(username)
    
    # Separate into evaluated and unevaluated
    unevaluated = [v for v in video_groups if v['video_url'] not in evaluated_urls]
    evaluated = [v for v in video_groups if v['video_url'] in evaluated_urls]
    
    # Return unevaluated first, then evaluated
    return unevaluated + evaluated

def load_json_details(json_filename):
    """Load the detailed JSON file for a specific evaluation."""
    # Construct full path from relative json_file path
    # The json_file is like: 20260224_005547_merged_personas_3.json
    # We need to find it in the eval_results structure
    
    # Try to find the file by searching in eval_results
    eval_results_dir = BASE_DIR / "eval_results"
    
    # Search for the JSON file
    json_files = list(eval_results_dir.rglob(json_filename))
    
    if json_files:
        json_path = json_files[0]
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            st.warning(f"Error loading JSON {json_filename}: {e}")
            return None
    else:
        st.warning(f"JSON file not found: {json_filename}")
        return None

def get_video_path(video_url):
    """Extract video ID from URL and construct potential local path."""
    # Extract video ID from YouTube URL
    if "watch?v=" in video_url:
        video_id = video_url.split("watch?v=")[1].split("&")[0]
    else:
        video_id = video_url.split("/")[-1]
    
    # Look for downloaded video in temp_videos directory
    temp_videos = BASE_DIR / "phase_2" / "temp_videos"
    if temp_videos.exists():
        video_file = temp_videos / f"{video_id}.mp4"
        if video_file.exists():
            return str(video_file)
    
    return None

def save_human_evaluation(video_url, title_en, category, accuracy_score, logic_score, 
                         persona_scores, objective_feedback):
    """
    Save human evaluation results to CSV.
    
    Args:
        video_url: YouTube URL
        title_en: Video title
        category: Subject category
        accuracy_score: Objective accuracy score (shared across personas)
        logic_score: Objective logic score (shared across personas)
        persona_scores: List of dicts with {persona, adaptability, engagement, feedback, json_file, ai_scores}
        objective_feedback: Feedback on objective dimensions
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create one row for each persona
    rows = []
    for ps in persona_scores:
        row_data = {
            'timestamp': timestamp,
            'evaluator': st.session_state.username,  # Record actual evaluator name
            'video_url': video_url,
            'title_en': title_en,
            'category': category,
            'student_persona': ps['persona'],
            # Objective scores (same for all personas)
            'accuracy': accuracy_score,
            'logic': logic_score,
            'objective_feedback': objective_feedback,
            # Subjective scores (persona-specific)
            'adaptability': ps['adaptability'],
            'engagement': ps['engagement'],
            'persona_feedback': ps['feedback'],
            # Reference data
            'json_file': ps['json_file'],
            'ai_accuracy': ps['ai_accuracy'],
            'ai_logic': ps['ai_logic'],
            'ai_adaptability': ps['ai_adaptability'],
            'ai_engagement': ps['ai_engagement']
        }
        rows.append(row_data)
    
    # Create DataFrame from the evaluation data
    df_new = pd.DataFrame(rows)
    
    # Handle re-evaluation: remove old scores from this user for this video
    if HUMAN_EVAL_CSV.exists():
        df_existing = pd.read_csv(HUMAN_EVAL_CSV)
        
        # Remove previous evaluations from this user for this video
        df_existing = df_existing[
            ~((df_existing['evaluator'] == st.session_state.username) & 
              (df_existing['video_url'] == video_url))
        ]
        
        # Append new evaluation
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(HUMAN_EVAL_CSV, index=False)
    else:
        df_new.to_csv(HUMAN_EVAL_CSV, index=False)

def display_scoring_criteria():
    """Display comprehensive scoring criteria guide for human evaluators."""
    with st.expander("📋 評分標準說明 (Scoring Criteria Guide)", expanded=False):
        st.markdown("""
        ### 📐 客觀評估維度 (Objective Dimensions)
        
        #### 🎯 Accuracy Score（準確性分數）- 起始分數：5.0/5.0
        
        **第一步：完整性與概念深度檢查**
        
        **完整性扣分：**
        - **內容過少** (-3.0，最高限制 2.0)：內容少於3項或影片不到2分鐘
        - **表面覆蓋** (-1.5～-2.0)：標題承諾深度但內容只有「提及」或「定義」
        - **缺少核心概念** (-1.0～-1.5)：必要主題完全缺失
        - **廣度無深度** (-0.5～-1.0)：多數主題只「提及」，很少達到「解釋」
        
        **概念深度扣分：**
        - **公式傾倒懲罰** (-2.0)：給出公式但沒有推導且沒有直觀解釋
        - **純計算偏向** (-1.5，最高限制 3.5)：超過70%內容是計算範例，理論基礎很少
        
        **第二步：錯誤扣分**（排除自我修正的錯誤）
        - **重大事實/公式錯誤** (-0.5/項)：未修正的科學錯誤
        - **小失誤/符號不一致** (-0.2/項)：持續存在的小錯誤
        - **標題內容不符** (-1.5)：內容與標題承諾明顯偏離  
        - **缺少基礎概念** (-0.3/項)：缺少關鍵先備知識
        
        ---
        
        #### 🧩 Logic Score（邏輯分數）- 起始分數：5.0/5.0
        
        **核心定義：** 衡量「啟發性支架」(Scaffolding for Insight)
        
        **邏輯流評估（優先評估）：**
        - **具體現象 → 抽象公式**：可獲得完整 5 分（從直觀建立再引入公式）
        - **公式 → 解題**：Logic 分數上限 3.0（直接套用數字，未建立概念理解）
        
        **同樣的完整性與概念深度扣分**（與 Accuracy 相同）
        
        **邏輯錯誤扣分：**
        - **邏輯跳躍** (-0.5/項)：跳過關鍵推導步驟
        - **先決條件違反** (-0.5/項)：在定義之前使用進階概念
        - **因果不一致** (-0.4/項)：結論不被邏輯/證據支持
        - **資訊過載** (-0.2/項)：塞入過多資訊且轉換不清晰
        
        ---
        
        ### 👥 主觀評估維度 (Subjective - Per Persona)
        
        #### 🎭 Adaptability（適配性）- 1.0～5.0
        **評估重點：** 影片難度與該學生背景知識的匹配程度
        
        **評分指引：**
        - **5 分**：完美匹配該 persona 的先備知識，既不過難也不過簡單
        - **4 分**：稍有挑戰但仍可理解，或稍簡單但仍有收穫
        - **3 分**：部分內容適合，部分過難或過簡
        - **2 分**：假設過多不具備的知識，或過於簡單無法學到新東西
        - **1 分**：完全不適合該 persona 的程度
        
        **檢查清單：**
        - ☑️ 影片使用的概念是否在該 persona 的先備知識範圍內？
        - ☑️ 如果引入新概念，是否有適當的解釋？
        - ☑️ 該 persona 的學習節奏與影片節奏是否匹配？
        - ☑️ 影片的解釋風格是否符合 persona 的偏好？
        
        ---
        
        #### 💡 Engagement（參與度）- 1.0～5.0
        **評估重點：** 該 persona 完成觀看影片的動力
        
        **評分指引：**
        - **5 分**：從頭到尾保持專注，想繼續看下去
        - **4 分**：大部分時間保持興趣，只有少數時刻無聊
        - **3 分**：時而有趣時而無聊，需要意志力才能看完
        - **2 分**：大部分時間感到無聊或困惑，很難維持注意力
        - **1 分**：完全無法吸引該 persona，可能直接放棄觀看
        
        **影響因素：**
        - **認知摩擦：** 內容過難會降低 engagement
        - **呈現方式：** 視覺提示、音訊與畫面同步性、節奏控制
        - **內容相關性：** 是否與該 persona 的學習目標相關
        - **教學風格：** 是否符合該 persona 的偏好
        
        ---
        
        ### 💭 評分步驟建議
        
        **客觀維度（Accuracy/Logic）：**
        1. 觀看影片，注意內容是否符合標題、是否有推導、是否有明顯錯誤
        2. 參考右側 AI Audit Log，判斷問題是否真實存在
        3. 從 5.0 開始，依序應用完整性、概念深度、錯誤扣分
        
        **主觀維度（Adaptability/Engagement）：**
        1. 切換到對應的 Persona 標籤頁
        2. 閱讀右側 Persona 描述（學習程度、節奏、偏好風格、先備知識）
        3. 站在該 Persona 的角度思考：「如果我是這個學生，這個影片適合/吸引我嗎？」
        4. 給出分數並寫下理由
        
        ---
        
        ### ⚠️ 常見陷阱
        - ❌ 不要受 AI 分數影響過大（AI 可能誤判）
        - ❌ 區分客觀與主觀（Accuracy/Logic 是事實性的，Adaptability/Engagement 是因人而異的）
        - ❌ 注意自我修正（教師已修正的錯誤不應扣分）
        - ✅ 完整性很重要（即使沒有明顯錯誤，內容過於簡略也應扣分）
        - ✅ 邏輯流很關鍵（「公式 → 解題」的影片 Logic 上限為 3.0）
        """)

def display_ai_audit_log(json_data):
    """Display AI's potential issues in an organized manner."""
    if not json_data:
        st.warning("⚠️ No AI audit data available")
        return
    
    # Extract potential issues from the JSON structure
    # The structure is: agent1_content_analyst -> potential_issues
    agent1_data = json_data.get('agent1_content_analyst', {})
    potential_issues = agent1_data.get('potential_issues', [])
    
    if not potential_issues:
        st.success("✅ No issues detected by AI")
        st.info("The AI content analyst did not identify any accuracy or logic problems in this video.")
        return
    
    st.subheader(f"🤖 AI Audit Log ({len(potential_issues)} issues)")
    st.caption("Review these AI-detected issues. They are suggestions, not ground truth.")
    
    for idx, issue in enumerate(potential_issues, 1):
        timestamp = issue.get('timestamp', 'N/A')
        category = issue.get('category', 'unknown')
        confidence = issue.get('confidence', 0)
        description = issue.get('description', 'No description')
        evidence = issue.get('raw_evidence', '')
        evidence_type = issue.get('evidence_type', 'Unknown')
        
        # Color code by category
        if category.lower() == 'accuracy':
            icon = "🎯"
        elif category.lower() == 'logic':
            icon = "🔗"
        else:
            icon = "⚠️"
        
        # Create expander with timestamp and category
        with st.expander(f"{icon} **[{timestamp}]** {category.upper()} - {evidence_type} (conf: {confidence:.2f})", expanded=False):
            st.markdown(f"**Issue:** {description}")
            if evidence:
                st.markdown(f"**Evidence:** {evidence}")
            
            # Add visual separator
            st.divider()
            st.caption(f"Confidence: {confidence:.2f} | Type: {evidence_type}")

def main():
    # Check login status first
    if not st.session_state.logged_in:
        show_login_page()
        return
    
    st.title("🎓 Human-in-the-Loop Video Evaluation")
    st.markdown("""
    Evaluate educational videos with multiple student personas.
    - **Objective scores** (Accuracy, Logic): Rate once per video
    - **Subjective scores** (Adaptability, Engagement): Rate for each persona
    """)
    st.markdown("---")
    
    # Load data
    video_groups = load_evaluation_data()
    
    if video_groups is None or len(video_groups) == 0:
        st.error("❌ No evaluation data available. Please check the CSV file path.")
        st.info(f"Expected path: `{CSV_PATH}`")
        return
    
    # Sort videos to prioritize unevaluated ones for current user
    video_groups = sort_videos_by_user_progress(video_groups, st.session_state.username)
    
    # Sidebar: Navigation Only
    with st.sidebar:
        # User info and logout
        st.markdown(f"### 👤 Evaluator: **{st.session_state.username}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ''
            st.session_state.current_index = 0
            st.rerun()
        
        st.markdown("---")
        
        st.header("📋 Evaluation Progress")
        
        # Navigation
        total_videos = len(video_groups)
        current_idx = st.number_input(
            "Select Video",
            min_value=0,
            max_value=total_videos - 1,
            value=st.session_state.current_index,
            step=1,
            help="Jump to a specific video"
        )
        st.session_state.current_index = current_idx
        
        st.progress((current_idx + 1) / total_videos)
        st.caption(f"Video {current_idx + 1} of {total_videos}")
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Previous", disabled=current_idx == 0, use_container_width=True):
                st.session_state.current_index = max(0, current_idx - 1)
                st.rerun()
        with col2:
            if st.button("Next ➡️", disabled=current_idx == total_videos - 1, use_container_width=True):
                st.session_state.current_index = min(total_videos - 1, current_idx + 1)
                st.rerun()
        
        st.markdown("---")
        
        # Display current video info
        current_video = video_groups[current_idx]
        num_personas = len(current_video['personas'])
        
        st.caption(f"**Topic:** {current_video['category']}")
        st.caption(f"**Personas:** {num_personas}")
        st.caption(f"**Video:** {current_video['title_en'][:40]}...")
        
        st.markdown("---")
        
        # Additional info
        with st.expander("📊 Your Evaluation Statistics", expanded=False):
            if HUMAN_EVAL_CSV.exists():
                completed_df = pd.read_csv(HUMAN_EVAL_CSV)
                
                # Personal statistics for current user
                user_evals = completed_df[completed_df['evaluator'] == st.session_state.username]
                user_completed_videos = user_evals['video_url'].nunique() if len(user_evals) > 0 else 0
                user_remaining = total_videos - user_completed_videos
                
                st.markdown(f"**Your Progress:**")
                st.metric("✅ Videos You've Evaluated", user_completed_videos)
                st.metric("⏳ Videos Remaining", user_remaining)
                
                st.markdown("---")
                st.markdown(f"**Overall Progress (All Evaluators):**")
                
                # Overall statistics
                all_completed_videos = completed_df['video_url'].nunique()
                total_evaluators = completed_df['evaluator'].nunique()
                
                st.caption(f"Total Videos Evaluated: {all_completed_videos}/{total_videos}")
                st.caption(f"Total Evaluators: {total_evaluators}")
            else:
                st.caption("No evaluations completed yet")
        
        with st.expander("❓ Scoring Guidelines", expanded=False):
            st.markdown("""
            **Objective Dimensions** (same for all personas):
            - **Accuracy**: Factual correctness
            - **Logic**: Instructional flow
            
            **Subjective Dimensions** (per persona):
            - **Adaptability**: Fit for this student
            - **Engagement**: Appeal to this student
            
            **Scoring Scale:**
            - **1.0-2.0:** Major problems
            - **2.5-3.5:** Needs improvement
            - **4.0-4.5:** Good quality
            - **5.0:** Excellent
            """)
    
    # Main content area
    st.header(f"📹 {current_video['title_en']}")
    st.caption(f"Category: {current_video['category']} | {len(current_video['personas'])} personas to evaluate")
    
    # Load JSON details for AI audit log (use first persona's JSON)
    json_filename = current_video['personas'][0]['json_file']
    json_data = load_json_details(json_filename)
    
    # Main layout: Video Player (60%) | AI Analysis + Evaluation (40%)
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        # Video Player
        st.subheader("🎬 Video Player")
        
        # Check if current user has evaluated this video
        evaluated_urls = get_user_evaluated_videos(st.session_state.username)
        if current_video['video_url'] in evaluated_urls:
            st.info("✅ **You have already evaluated this video.** You can re-evaluate to update your scores.")
        
        video_url = current_video['video_url']
        video_path = get_video_path(video_url)
        
        if video_path and Path(video_path).exists():
            # Show local video file
            st.video(video_path)
        else:
            # Show YouTube embed or link
            st.info(f"📺 Local video not available. Watch on YouTube:")
            st.markdown(f"[Open in YouTube]({video_url})")
            
            # Try to embed YouTube video
            if "youtube.com/watch?v=" in video_url or "youtu.be/" in video_url:
                video_id = video_url.split("watch?v=")[-1].split("&")[0] if "watch?v=" in video_url else video_url.split("/")[-1]
                st.markdown(
                    f'<iframe width="100%" height="400" src="https://www.youtube.com/embed/{video_id}" '
                    f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
                    f'gyroscope; picture-in-picture" allowfullscreen></iframe>',
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
        
        # Display scoring criteria guide below video
        display_scoring_criteria()
    
    with col_right:
        # === TOP: AI ANALYSIS ===
        st.subheader("🤖 AI Analysis")
        display_ai_audit_log(json_data)
        
        st.markdown("---")
        
        # === BOTTOM: EVALUATION FORM ===
        st.subheader("👤 Your Evaluation")
        
        # Create form for all evaluations
        with st.form(key="evaluation_form"):
            # PART 1: Objective Evaluation (Once per video)
            st.markdown("**📐 PART 1: Objective Evaluation**")
            st.caption("Rate once per video (independent of student persona)")
            
            col_obj1, col_obj2 = st.columns(2)
            with col_obj1:
                accuracy_score = st.number_input(
                    "🎯 Accuracy",
                    min_value=1.0,
                    max_value=5.0,
                    value=3.0,
                    step=0.5,
                    help="Factual correctness"
                )
            with col_obj2:
                logic_score = st.number_input(
                    "🔗 Logic",
                    min_value=1.0,
                    max_value=5.0,
                    value=3.0,
                    step=0.5,
                    help="Instructional flow"
                )
            
            st.markdown("---")
            
            # PART 2: Subjective Evaluation (Per Persona)
            st.markdown("**🎭 PART 2: Subjective Evaluation (By Persona)**")
            st.caption("⚠️ Evaluate from each student's perspective!")
            
            # Create tabs for each persona
            persona_tabs = st.tabs([f"Persona {i+1}" for i in range(len(current_video['personas']))])
            
            # Store persona scores
            persona_scores = []
            
            for idx, (tab, persona) in enumerate(zip(persona_tabs, current_video['personas'])):
                with tab:
                    # Show Persona Profile
                    st.markdown("**📋 Student Profile:**")
                    st.info(persona['student_persona'], icon="👤")
                    
                    st.markdown("---")
                    
                    # Subjective scores
                    st.markdown("**📊 Subjective Scores:**")
                    
                    col_sub1, col_sub2 = st.columns(2)
                    with col_sub1:
                        adaptability = st.number_input(
                            "🎭 Adaptability",
                            min_value=1.0,
                            max_value=5.0,
                            value=3.0,
                            step=0.5,
                            help="Fit for this student",
                            key=f"adaptability_{idx}"
                        )
                    with col_sub2:
                        engagement = st.number_input(
                            "⚡ Engagement",
                            min_value=1.0,
                            max_value=5.0,
                            value=3.0,
                            step=0.5,
                            help="Appeal to this student",
                            key=f"engagement_{idx}"
                        )
                    
                    # Store persona evaluation data
                    persona_scores.append({
                        'persona': persona['student_persona'],
                        'adaptability': adaptability,
                        'engagement': engagement,
                        'feedback': '',
                        'json_file': persona['json_file'],
                        'ai_accuracy': persona['ai_accuracy'],
                        'ai_logic': persona['ai_logic'],
                        'ai_adaptability': persona['ai_adaptability'],
                        'ai_engagement': persona['ai_engagement']
                    })
            
            st.markdown("---")
            
            # Submit button
            submit_button = st.form_submit_button(
                "✅ Submit All Evaluations",
                use_container_width=True,
                type="primary"
            )
        
        # Handle form submission (outside form but inside col_right)
        if submit_button:
            # Save evaluation (no feedback validation needed)
            save_human_evaluation(
                video_url=current_video['video_url'],
                title_en=current_video['title_en'],
                category=current_video['category'],
                accuracy_score=accuracy_score,
                logic_score=logic_score,
                persona_scores=persona_scores,
                objective_feedback=''
            )
            
            st.success(f"✅ Evaluation saved successfully!")
            st.info(f"Saved {len(persona_scores)} persona evaluations")
            
            # Auto-advance to next video
            if current_idx < total_videos - 1:
                st.info("Moving to next video...")
                st.session_state.current_index = current_idx + 1
                st.rerun()
            else:
                st.balloons()
                st.success("🎉 All videos evaluated!")

if __name__ == "__main__":
    main()
