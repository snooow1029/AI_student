# Prompts 目錄說明

這個目錄包含了三個 AI Agent 的 prompt 模板,用於視頻評估系統。

## 文件說明

### 1. agent1_prompt.md
**Agent 1: Educational Content Analyst (教育內容分析專家)**

- **任務**: 分析視頻內容,提取內容地圖並識別潛在問題
- **模型**: Gemini 2.5 Pro (VLM - 視覺語言模型)
- **輸入**: 視頻文件 + 標題
- **輸出**: JSON 格式,包含:
  - `content_map`: 時間戳標註的內容地圖
  - `potential_issues`: 潛在的準確性和邏輯問題
  - `teaching_mode`: 教學模式識別(概念型/程序型)

**占位符:**
- `{video_title}`: 視頻標題

### 2. agent2_prompt.md
**Agent 2: Gap Analysis Judge (差距分析評審)**

- **任務**: 根據 Agent 1 的報告進行評分
- **模型**: Gemini 2.5 Flash (純 LLM)
- **輸入**: Agent 1 的完整報告
- **輸出**: JSON 格式,包含:
  - `accuracy_score`: 準確性分數 (1-5)
  - `logic_score`: 邏輯性分數 (1-5)
  - `completeness_analysis`: 完整性分析
  - `verified_errors`: 驗證後的錯誤列表

**占位符:**
- `{video_title}`: 視頻標題
- `{agent1_output}`: Agent 1 的完整 JSON 報告

### 3. subjective_prompt.md
**Agent 3: Subjective Simulation (主觀體驗模擬)**

- **任務**: 從特定學生的角度評估視頻
- **模型**: Gemini 2.5 Flash (VLM)
- **輸入**: 視頻文件 + Persona 資料 + 客觀分數
- **輸出**: JSON 格式,包含:
  - `student_monologue`: 學生的第一人稱體驗敘述
  - `subjective_scores`: 主觀分數(適應性、參與度、清晰度)
  - `engagement_curve`: 各階段參與度曲線
  - `cognitive_friction`: 認知摩擦程度

**占位符:**
- `{persona_desc}`: Persona 描述
- `{persona_attr}`: 學生特徵
- `{preferred_style}`: 偏好的學習風格
- `{accuracy_score}`: Agent 2 的準確性分數
- `{logic_score}`: Agent 2 的邏輯性分數
- `{error_list}`: 驗證後的錯誤列表
- `{content_map_summary}`: 內容地圖摘要

## 如何修改 Prompt

### 1. 直接編輯 Markdown 文件

你可以直接編輯這三個 `.md` 文件來修改 prompt:

```bash
# 使用你喜歡的編輯器
vim prompts/agent1_prompt.md
code prompts/agent2_prompt.md
nano prompts/subjective_prompt.md
```

### 2. 保留占位符

修改時請確保保留所有的占位符 `{variable_name}`,這些會在運行時被實際值替換:

```markdown
# 正確 ✅
**{video_title}**

# 錯誤 ❌ - 移除了占位符
**Video Title Here**
```

### 3. 測試修改

修改後重新啟動 API 服務,prompt 會自動重新載入:

```bash
# 方法 1: 使用啟動腳本
bash run_api.sh

# 方法 2: 直接運行
python api_main.py

# API 會在啟動時顯示:
# Loading prompt templates...
# ✓ Prompts loaded successfully
```

### 4. 調試 Prompt

如果遇到問題:

1. **檢查文件是否存在**:
   ```bash
   ls -la prompts/
   ```

2. **檢查占位符拼寫**:
   - Agent 1: `{video_title}`
   - Agent 2: `{video_title}`, `{agent1_output}`
   - Agent 3: `{persona_desc}`, `{persona_attr}`, `{preferred_style}`, `{accuracy_score}`, `{logic_score}`, `{error_list}`, `{content_map_summary}`

3. **查看 API 日誌**:
   ```bash
   # API 會顯示 prompt 載入狀態
   Loading prompt templates...
   ✓ Prompts loaded successfully
   ```

## Prompt 設計原則

### 1. 結構化清晰
使用 Markdown 標題和分節:
- `#` 主要任務
- `##` 主要步驟  
- `**粗體**` 重要指令

### 2. 明確的輸出格式
總是包含 JSON schema 範例

### 3. 邊界條件處理
- 明確說明什麼應該做
- 明確說明什麼不應該做

### 4. 範例和反例
提供具體的例子幫助 AI 理解

## 版本控制建議

建議使用 Git 追蹤 prompt 的修改:

```bash
# 提交 prompt 修改
git add prompts/
git commit -m "Update agent1 prompt: improve error detection"

# 查看修改歷史
git log -- prompts/

# 回滾到之前的版本
git checkout <commit-hash> -- prompts/agent1_prompt.md
```

## 進階用法

### 多語言支持

如果需要支持多語言,可以創建不同的 prompt 文件:

```
prompts/
├── en/
│   ├── agent1_prompt.md
│   ├── agent2_prompt.md
│   └── subjective_prompt.md
├── zh-tw/
│   ├── agent1_prompt.md
│   ├── agent2_prompt.md
│   └── subjective_prompt.md
└── README.md
```

然後修改 `api_main.py` 中的 `load_prompt()` 函數來支持語言參數。

### A/B 測試

可以創建不同版本的 prompt 進行對比測試:

```
prompts/
├── v1/
│   └── agent1_prompt.md
├── v2/
│   └── agent1_prompt.md  (修改後的版本)
└── README.md
```

## 相關文件

- [API_README.md](../API_README.md) - API 服務總覽
- [API_USAGE_GUIDE.md](../API_USAGE_GUIDE.md) - API 使用指南
- [api_main.py](../api_main.py) - API 主程序
- [eval.py](../eval.py) - 原始評估腳本(參考用)

## 問題排查

### FileNotFoundError: Prompt file not found

**原因**: prompt 文件不存在或路徑錯誤

**解決方法**:
```bash
# 確認文件存在
ls prompts/agent1_prompt.md
ls prompts/agent2_prompt.md  
ls prompts/subjective_prompt.md

# 確認文件有讀取權限
chmod +r prompts/*.md
```

### format() missing required argument

**原因**: prompt 模板中有占位符但未提供對應的值

**解決方法**: 檢查 `api_main.py` 中的 `.format()` 調用是否包含所有必需的參數。

### Unexpected model output format

**原因**: 修改 prompt 後 AI 輸出格式改變

**解決方法**: 確保 prompt 末尾的 JSON schema 保持完整。
