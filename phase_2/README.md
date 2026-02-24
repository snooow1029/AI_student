# VibeTech – Human Evaluation Interface

Multi-user web application for evaluating educational video quality across different student personas.

## 📱 Live Demo
Deploy this app on [Streamlit Community Cloud](https://streamlit.io/cloud)

## ✨ Features
- 🔐 **Multi-user Login System**: Track evaluations by evaluator name
- 📊 **Progress Tracking**: Auto-prioritize unevaluated videos
- 🎯 **Multi-Persona Evaluation**: Rate videos for different student types
- 📈 **Personal Statistics**: Track your evaluation progress
- ♻️ **Re-evaluation Support**: Update scores for already-evaluated videos
- 💾 **Auto-save**: All evaluations saved to CSV

## 🚀 Quick Start (Local)

```bash
cd phase_2
pip install -r requirements.txt
streamlit run human_eval_app.py
```

### Network Deployment (Local Network)

```bash
cd phase_2
./run_human_eval_network.sh
```

Share the displayed network URL with team members on the same network.

## 📦 Deployment on Streamlit Community Cloud

### Prerequisites
1. GitHub account
2. Code pushed to GitHub repository
3. [Streamlit Community Cloud account](https://streamlit.io/cloud) (free)

### Steps

1. **Push code to GitHub** (if not already done)
   ```bash
   cd /path/to/vibe_teach
   git add phase_2/
   git commit -m "Add human evaluation interface"
   git push origin master
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository: `snooow1029/AI_student` (or your repo)
   - Set:
     - **Branch**: `master` (or your branch)
     - **Main file path**: `phase_2/human_eval_app.py`
   - Click "Deploy"

3. **Wait for deployment** (~2-3 minutes)

4. **Share the URL** with your team members

### Important Notes

⚠️ **CSV File Persistence**: Streamlit Cloud has limitations with file writes:
- By default, files are **ephemeral** (lost on restart)
- For production use, consider:
  - Using Streamlit Cloud's secrets for database connection
  - Migrating to SQLite/PostgreSQL database
  - Using cloud storage (AWS S3, Google Cloud Storage)

**Current Setup (CSV)**: Works for demonstration and small-scale testing. Results are saved but may be lost on app restart.

**Recommended for Production**: See [Database Migration Guide](#database-migration) below.

## 📊 Evaluation Workflow

1. **Login**: Enter your evaluator name
2. **Select Video**: Navigate through videos (unevaluated shown first)
3. **Watch & Analyze**: Review video and AI analysis
4. **Score**: Rate across 4 dimensions
   - Accuracy (Objective)
   - Logic (Objective)
   - Adaptability (Per-persona)
   - Engagement (Per-persona)
5. **Submit**: Auto-advances to next video
6. **Track Progress**: View statistics in sidebar

## 🗂️ Data Files

- `merged_small_scale_summaries_20260224_014339.csv`: Video metadata and AI scores (26KB)
- `eval_results/`: JSON files with detailed AI analysis (1.8MB)
- `human_eval_results.csv`: Human evaluation results (output)

## 📖 Documentation

- [Scoring Criteria Guide](SCORING_CRITERIA.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md) (detailed network/remote deployment)
- [Usage Guide](USAGE.md)

## 🔧 Configuration

Edit `human_eval_app.py` constants:
```python
CSV_PATH = Path("merged_small_scale_summaries_20260224_014339.csv")
HUMAN_EVAL_CSV = Path("human_eval_results.csv")
BASE_DIR = Path(__file__).parent
```

## 🛠️ Troubleshooting

### App won't deploy on Streamlit Cloud

**Error**: "The app's code is not connected to a remote GitHub repository"

**Solution**: 
```bash
cd phase_2
git add .
git commit -m "Prepare for deployment"
git push origin master
```

Then retry deployment on Streamlit Cloud.

### Can't write to CSV

**On Streamlit Cloud**: File writes work but may not persist across restarts.

**Solution**: For production, migrate to database (see below).

### Other users can't access (local network)

1. Check firewall: `sudo ufw allow 8501/tcp`
2. Verify IP address: `hostname -I`
3. Ensure same network: `ping <your-ip>`
4. Use network script: `./run_human_eval_network.sh`

## 🚀 Database Migration (Optional, for Production)

To persist data reliably on Streamlit Cloud, migrate from CSV to database:

### Option 1: SQLite (Simplest)
```python
import sqlite3
# Replace CSV operations with SQLite
conn = sqlite3.connect('evaluations.db')
```

### Option 2: PostgreSQL (Recommended for Production)
Use Streamlit secrets + Supabase/Railway free tier:
```python
import psycopg2
# Connection via st.secrets["postgres"]
```

### Option 3: Cloud Storage
Store CSV in Google Cloud Storage or AWS S3.

## 📞 Support

For issues or questions, refer to:
- [Streamlit Documentation](https://docs.streamlit.io)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

## 📄 License

Educational use - VibeTech Project

---

**Built with Streamlit** 🎈
