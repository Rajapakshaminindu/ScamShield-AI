# 🛡️ ScamShield AI
> **Detect. Explain. Protect.**  
> *An AI-powered Multimodal Platform that detects financial scams, explains the deceptive tactics, and guides users with actionable protection steps.*

---

## 🌟 Key Capabilities
- ✉️ **Text & SMS Analysis**: Detects psychological urgency, fear manipulation, fake lottery lures, and banking impersonations.
- 🖼️ **Screenshot / Image OCR**: Extracts text from WhatsApp, SMS, and email screenshots and scans for visual and textual scam signals.
- 🔗 **URL & Domain Intelligence**: Uncovers shortened links, spoofed banking domains, and high-risk TLDs.
- 🎙️ **Voice / Audio Scam Scan**: Analyzes voice call recordings and audio clips for voice phishing (*vishing*).
- 🧠 **Dual-Layer Intelligence**: Combines instant heuristic pattern checks with **Alibaba Cloud Model Studio (Qwen)** LLM reasoning.
- 📊 **Explainable AI (XAI)**: Generates clear, consumer-friendly explanations showing *why* a message is dangerous along with concrete **Do's and Don'ts**.

---

## 🏗️ Technology Stack
- **AI Engine**: Alibaba Cloud Qwen (`qwen-plus`, `qwen-vl-plus`)
- **Backend API**: Python 3.13 + FastAPI + Uvicorn + Pydantic
- **Frontend Dashboard**: Responsive Single-Page Application (HTML5, Modern CSS3, Vanilla JavaScript)

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ installed

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required packages
pip install -r backend/requirements.txt
```

### 3. Configure API Key (Optional)
Copy `.env.example` to `.env` inside `backend/` or project root:
```bash
cp backend/.env.example .env
```
Add your **Alibaba Cloud DashScope API Key**:
```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```
*(Note: If no API key is provided, the platform automatically runs in smart **Heuristic Fallback Mode**, allowing full offline testing without crashing!)*

### 4. Run the Application
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```
Open your browser and navigate to:  
👉 **`http://localhost:8000`**

---

## 🛠️ Using with Qoder IDE
1. Open this workspace in **Qoder IDE**.
2. Qoder will automatically read `.qoder/rules.md` to follow our architecture.
3. Open **Sidebar Chat (`Ctrl+L`)** or **Quest** to explore, refine, or extend features.
