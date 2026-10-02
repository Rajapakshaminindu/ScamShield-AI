# 🛡️ ScamShield AI
> **Detect. Explain. Protect.**  
> *A scam-awareness platform with text and URL checks, practical safety guidance, and optional AI-assisted analysis.*

---

## 🌟 Key Capabilities
- ✉️ **Text & SMS Analysis**: Detects psychological urgency, fear manipulation, fake lottery lures, and banking impersonations.
- 🖼️ **Screenshot Analysis (optional)**: Requires a configured vision-model service. If one is unavailable, screenshot analysis returns an explicit unavailable message rather than a simulated result.
- 🔗 **URL & Domain Intelligence**: Uncovers shortened links, spoofed banking domains, and high-risk TLDs.
- 🎙️ **Audio Analysis**: Not currently supported. The UI explains this and the API rejects audio uploads rather than showing a fabricated transcript.
- 🧠 **Optional AI Assistance**: Combines heuristic pattern checks with an optional OpenAI-compatible language-model provider, configured through environment variables.
- 📊 **Explainable AI (XAI)**: Generates clear, consumer-friendly explanations showing *why* a message is dangerous along with concrete **Do's and Don'ts**.
- 📚 **Public Learning Center**: Original scam-safety guidance, trusted resources, and the site's About, Privacy, Terms, and Contact information at `/learn`.

> **Important:** Automated results can be incomplete or incorrect. Verify important requests directly with the relevant organization. Do not submit passwords, one-time codes, payment-card details, or private recovery links.

## AdSense and Publisher Content

The public learning center at [`/learn`](https://scamshield-ai-24t3.onrender.com/learn) is the site's primary editorial and publisher-information page. It is accessible without signing in and contains practical guides for checking suspicious messages and links, steps to take after a suspected scam, an explanation of the scanner's limitations, trusted external resources, and About, Privacy, Terms, and Contact sections.

The AdSense loader is included on the public learning page only; it is intentionally omitted from the scanner, login, and private admin screens so ads are not placed on utility, navigation, or account-management surfaces. The scanner labels sample messages as examples and avoids unsupported accuracy, latency, and protection claims. `frontend/ads.txt` carries the publisher record, while `/robots.txt` and `/sitemap.xml` help crawlers discover public pages and avoid private/API routes.

The site's existing Render deployment is [https://scamshield-ai-24t3.onrender.com](https://scamshield-ai-24t3.onrender.com). Public guides: [https://scamshield-ai-24t3.onrender.com/learn](https://scamshield-ai-24t3.onrender.com/learn). A code update does not guarantee AdSense approval; confirm the live deployment, publisher details, consent and privacy obligations for your visitors' locations, and Google's current policies before requesting review.

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

## ☁️ Publish a Public Link (Render)

This repo ships a [`render.yaml`](render.yaml) blueprint, so Render provisions the service for you.

1. Sign in at **[dashboard.render.com](https://dashboard.render.com)** with your GitHub account.
2. Go to **Blueprints → New Blueprint Instance**, pick the `ScamShield-AI` repo and click **Apply**.
3. Render prompts for the values marked `sync: false`. Fill them in:
   | Variable | Value |
   |---|---|
   | `DASHSCOPE_API_KEY` | Your Qwen key (leave blank to run in heuristic fallback mode) |
   | `ADMIN_USERNAME` | Your admin login name |
   | `ADMIN_PASSWORD` | **A strong password** — never leave this as the default |
4. Wait for the first build (~3-4 min). Your public link appears at the top of the service page, e.g.
   `https://scamshield-ai-24t3.onrender.com`

**Free-tier notes**
- The instance sleeps after 15 minutes of inactivity, so the first visit after a pause takes ~50 seconds to wake up. Warm it up before a demo.
- The SQLite file lives on ephemeral disk: registered users and scan logs reset on every redeploy. Scanning, the Copilot and the intro animation are unaffected.
- `JWT_SECRET` is auto-generated by Render, so the placeholder secret in this public repo cannot be used to forge tokens.

---

## 🛠️ Using with Qoder IDE
1. Open this workspace in **Qoder IDE**.
2. Qoder will automatically read `.qoder/rules.md` to follow our architecture.
3. Open **Sidebar Chat (`Ctrl+L`)** or **Quest** to explore, refine, or extend features.
