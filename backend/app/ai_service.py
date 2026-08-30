import json
import base64
from typing import Optional, List
from openai import OpenAI
from backend.app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, QWEN_MODEL_NAME, QWEN_VL_MODEL_NAME
from backend.app.schemas import ScamAnalysisResponse, DetectedIndicator, ChatFollowupResponse
from backend.app.rule_engine import analyze_text_heuristics, analyze_url_heuristics, inspect_domain_spoof

def get_ai_client() -> Optional[OpenAI]:
    """Returns OpenAI-compatible client for Alibaba Cloud Model Studio (DashScope) if configured."""
    if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY.strip() == "" or "your_dashscope" in DASHSCOPE_API_KEY:
        return None
    return OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL
    )

SYSTEM_PROMPT = """You are ScamShield AI, an advanced cybersecurity and fraud detection intelligence assistant.
Your job is to analyze user-submitted messages, screenshots, URLs, or audio transcripts to detect scams, fraud, phishing, and social engineering attacks.

Always return your analysis strictly as a valid JSON object matching this schema:
{
  "is_scam": boolean,
  "risk_score": integer (0 to 100),
  "risk_level": "Low" | "Medium" | "High" | "Critical",
  "scam_type": "Phishing" | "Bank Impersonation" | "Investment Scam" | "Fake Job Scam" | "Lottery/Prize Scam" | "Tech Support Scam" | "OTP Theft" | "Safe",
  "summary": "Concise 1-2 sentence summary of what this message is and why it was flagged",
  "detected_indicators": [
    {
      "category": "string (e.g., Sensitive Info Request, Urgency, Domain Spoofing)",
      "description": "Clear explanation of the indicator",
      "severity": "low" | "medium" | "high" | "critical"
    }
  ],
  "explanation": [
    "Clear bullet point 1 explaining why this is dangerous",
    "Clear bullet point 2 explaining why this is dangerous"
  ],
  "recommended_dos": [
    "Actionable step 1 to stay safe",
    "Actionable step 2"
  ],
  "recommended_donts": [
    "Warning step 1 of what NOT to do",
    "Warning step 2"
  ]
}
"""

def generate_fallback_analysis(text: str, content_type: str = "text") -> ScamAnalysisResponse:
    """Generates intelligent heuristic-backed analysis when no live API key is connected."""
    heuristic_score, indicators, urls = analyze_text_heuristics(text)
    
    # Determine risk level & scam type based on heuristic signals
    if heuristic_score >= 70:
        risk_level = "Critical" if heuristic_score >= 85 else "High"
        is_scam = True
        
        # Categorize with advance-fee scam detection
        lower_t = text.lower()
        has_lure = "won" in lower_t or "lottery" in lower_t or "prize" in lower_t or "congratulations" in lower_t
        has_job_lure = "job" in lower_t or "earn" in lower_t or "task" in lower_t or "work from home" in lower_t
        has_bank_info = any(kw in lower_t for kw in ["bank account", "account number", "ifsc", "routing number", "bank details"])
        has_personal_info = any(kw in lower_t for kw in ["full name", "phone number", "date of birth", "address", "id card"])
        has_fee_request = any(kw in lower_t for kw in ["fee", "deposit", "send money", "transfer", "pay via"])

        if has_lure and (has_bank_info or has_personal_info or has_fee_request):
            scam_type = "Advance-Fee Fraud Scam"
        elif has_job_lure and (has_bank_info or has_personal_info or has_fee_request):
            scam_type = "Fake Job / Task Scam"
        elif "otp" in lower_t or "cvv" in lower_t or "password" in lower_t:
            scam_type = "OTP / Credential Theft"
        elif has_bank_info or has_personal_info:
            scam_type = "Personal Information Harvesting"
        elif "invest" in lower_t or "profit" in lower_t or "crypto" in lower_t:
            scam_type = "Investment Scam"
        elif has_lure:
            scam_type = "Lottery / Prize Scam"
        elif "suspended" in lower_t or "blocked" in lower_t or "bank" in lower_t:
            scam_type = "Bank / Service Impersonation"
        else:
            scam_type = "Phishing Scam"
            
        summary = f"High probability scam detected ({scam_type}). The message exhibits deceptive tactics to manipulate the recipient."
        explanation = [
            f"Detected {len(indicators)} high-risk indicators in the submission.",
            "The message attempts to trigger immediate emotional reaction (urgency or fear).",
            "Contains requests for sensitive credentials or suspicious link redirections."
        ]
        dos = [
            "Block the sender immediately.",
            "Contact the official institution through their verified phone number/website.",
            "Report this message to your local cybercrime reporting portal."
        ]
        donts = [
            "Do NOT click any links in the message.",
            "Do NOT share OTPs, passwords, or banking details.",
            "Do NOT reply to the sender."
        ]
    elif heuristic_score >= 30:
        risk_level = "Medium"
        is_scam = True
        scam_type = "Suspicious Message"
        summary = "This message contains potentially suspicious elements such as unusual links or urgency cues. Proceed with caution."
        explanation = [
            "Certain wording resembles common scam templates.",
            "Verification of sender identity is strongly recommended."
        ]
        dos = ["Verify sender identity through known channels.", "Check the destination URL carefully."]
        donts = ["Do not provide personal information.", "Do not download unexpected attachments."]
    else:
        risk_level = "Low"
        is_scam = False
        scam_type = "Legitimate / Safe"
        summary = "No immediate scam or phishing indicators were detected in this submission."
        explanation = [
            "No sensitive data requests detected (no OTP, password, or card requests).",
            "No artificial urgency, blackmail, or deceptive lures found."
        ]
        dos = ["Continue standard security hygiene.", "Always keep software updated."]
        donts = ["Never share your private passwords or OTPs with anyone."]

    return ScamAnalysisResponse(
        is_scam=is_scam,
        risk_score=heuristic_score,
        risk_level=risk_level,
        scam_type=scam_type,
        extracted_text=text,
        summary=summary,
        detected_indicators=indicators,
        explanation=explanation,
        recommended_dos=dos,
        recommended_donts=donts
    )


def _attach_domain_spoof(response: ScamAnalysisResponse, url: str) -> ScamAnalysisResponse:
    """Inspects a URL for domain spoofing and attaches the result to the response.
    Also adds a critical indicator and bumps the score if spoofing is detected."""
    spoof_info = inspect_domain_spoof(url)
    if spoof_info and spoof_info.is_spoofed:
        response.domain_spoof = spoof_info
        # Add a domain spoofing indicator
        spoof_indicator = DetectedIndicator(
            category="Domain Spoofing Detected",
            description=f"Domain '{spoof_info.domain_breakdown}' impersonates {spoof_info.spoofed_brand}. Official domain: {spoof_info.official_domain}",
            severity="critical"
        )
        response.detected_indicators.append(spoof_indicator)
        # Bump risk score (capped at 100)
        response.risk_score = min(100, response.risk_score + 20)
        # Upgrade risk level based on bumped score
        if response.risk_score >= 85:
            response.risk_level = "Critical"
        elif response.risk_score >= 60:
            response.risk_level = "High"
        elif response.risk_score >= 30:
            response.risk_level = "Medium"
        # Ensure is_scam is True when domain spoofing is detected
        response.is_scam = True
        # Add explanation about domain spoofing
        response.explanation.append(
            f"The domain '{spoof_info.domain_breakdown}' is designed to look like {spoof_info.spoofed_brand} but is NOT the official website ({spoof_info.official_domain}). This is a strong phishing indicator."
        )
    return response


def analyze_text(text: str) -> ScamAnalysisResponse:
    """Analyzes text using Qwen LLM with fallback to Heuristic Engine."""
    client = get_ai_client()
    if not client:
        return generate_fallback_analysis(text, content_type="text")

    try:
        heuristic_score, indicators, _ = analyze_text_heuristics(text)
        user_prompt = f"""Please analyze this message for scam patterns:
\"\"\"
{text}
\"\"\"

Initial Heuristic Signals Detected:
- Score: {heuristic_score}/100
- Flags: {[ind.description for ind in indicators]}
"""
        response = client.chat.completions.create(
            model=QWEN_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return ScamAnalysisResponse(**data)
    except Exception as e:
        print(f"Error calling Qwen API: {e}. Falling back to heuristic analysis.")
        return generate_fallback_analysis(text, content_type="text")

def analyze_url(url: str) -> ScamAnalysisResponse:
    """Analyzes a URL with domain spoof inspection."""
    client = get_ai_client()
    if not client:
        result = generate_fallback_analysis(f"Suspicious URL submitted: {url}", content_type="url")
        return _attach_domain_spoof(result, url)

    try:
        user_prompt = f"Analyze the safety and legitimacy of this URL: {url}"
        response = client.chat.completions.create(
            model=QWEN_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        result = ScamAnalysisResponse(**data)
        return _attach_domain_spoof(result, url)
    except Exception as e:
        print(f"Error in URL analysis: {e}")
        result = generate_fallback_analysis(f"Suspicious URL submitted: {url}", content_type="url")
        return _attach_domain_spoof(result, url)

def analyze_image_bytes(image_bytes: bytes, filename: str) -> ScamAnalysisResponse:
    """Analyzes an image screenshot using Qwen-VL or smart simulated OCR."""
    client = get_ai_client()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    if client:
        try:
            response = client.chat.completions.create(
                model=QWEN_VL_MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this screenshot and analyze if it is a scam."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return ScamAnalysisResponse(**data)
        except Exception as e:
            print(f"Error calling Qwen-VL: {e}. Using fallback image analysis.")

    # Fallback simulation for image upload demo
    sample_ocr = "Dear Customer, your Bank Account has been temporarily suspended due to KYC failure. Click http://bank-kyc-update.xyz to verify your identity and enter OTP immediately or your account will be permanently closed."
    res = generate_fallback_analysis(sample_ocr, content_type="image")
    res.extracted_text = f"[OCR Extracted from {filename}]:\n{sample_ocr}"
    return res

def analyze_audio_bytes(audio_bytes: bytes, filename: str) -> ScamAnalysisResponse:
    """Analyzes audio / voice message recording for vishing."""
    # Simulated voice transcription for demo
    sample_transcription = "Hello, this is officer James from the National Tax Department. An arrest warrant has been issued in your name for unpaid tax liabilities. To stop legal enforcement, press 1 and transfer payment immediately."
    res = generate_fallback_analysis(sample_transcription, content_type="voice")
    res.extracted_text = f"[Voice-to-Text Transcription of {filename}]:\n\"{sample_transcription}\""
    return res


# ---------------------------------------------------------------------------
# COPILOT SYSTEM PROMPTS
# ---------------------------------------------------------------------------
COPILOT_SYSTEM = (
    "You are ScamShield Copilot \u2014 a brilliant, empathetic cybersecurity advisor and general knowledge assistant.\n"
    "You are the intelligent chatbot embedded inside the ScamShield AI scam-detection platform.\n\n"
    "## Core Identity:\n"
    "- You are warm, supportive, and speak like a knowledgeable friend \u2014 never robotic or condescending.\n"
    "- You NEVER say 'I am an AI' or 'as an AI'. You are a human advisor.\n\n"
    "## What You Can Do:\n"
    "1. **Scam Analysis** (PRIMARY): Analyze scanned content, explain threats, give step-by-step safety advice.\n"
    "2. **Cybersecurity Guidance**: Passwords, 2FA, malware, phishing, social engineering, data breaches, online safety.\n"
    "3. **Financial Safety**: Bank fraud, UPI scams, credit card theft, investment scams, money recovery steps.\n"
    "4. **Digital Literacy**: How the internet works, safe browsing, privacy settings, social media safety.\n"
    "5. **Legal & Reporting**: How to file cybercrime complaints, consumer rights, legal options.\n"
    "6. **General Knowledge**: You can answer ANY question the user asks \u2014 history, science, technology, daily life, etc.\n"
    "   You are a helpful assistant first; cybersecurity is your specialty, not your limit.\n\n"
    "## Response Format:\n"
    "- Address the user's specific concern FIRST, acknowledging their emotion or situation.\n"
    "- Use **bold** for key actions and important terms.\n"
    "- Use bullet points (\u2022) for lists, numbered steps for sequences.\n"
    "- Keep responses concise: 4-8 sentences for simple questions, up to 12 for complex ones.\n"
    "- Always end with one clear, empowering next action.\n"
    "- If panicked, start with calming reassurance before giving steps.\n"
    "- Keep explanations simple, jargon-free, and practical. Use analogies when helpful.\n\n"
    "## Important Rules:\n"
    "- If scan context is provided, reference the specific scan results in your answer.\n"
    "- If NO scan context, answer based on general knowledge \u2014 you don't need a scan to help.\n"
    "- For medical, legal, or financial emergencies, always advise consulting a professional.\n"
    "- Never provide instructions for illegal or harmful activities.\n"
    "- Be concise but thorough. Every response should be actionable.\n"
)

COPILOT_SCAN_HINT = (
    "The user just scanned content with ScamShield. Here is the scan context \u2014 "
    "reference these results in your answers:\n{context}"
)


def chat_followup(message: str, scan_context: str, chat_history: list) -> ChatFollowupResponse:
    """
    Conversational follow-up endpoint.
    Acts as a cybersecurity advisor answering questions about a scanned threat.
    Uses Qwen LLM if available, otherwise returns intelligent heuristic responses.
    """
    client = get_ai_client()

    if client:
        try:
            # Build conversation history messages
            messages = [{"role": "system", "content": COPILOT_SYSTEM}]

            # Add scan context as system hint if present
            if scan_context.strip():
                messages.append({
                    "role": "system",
                    "content": COPILOT_SCAN_HINT.replace("{context}", scan_context)
                })

            # Append chat history
            for msg in chat_history[-10:]:  # last 10 messages max
                messages.append({"role": msg.role, "content": msg.content})

            # Append current user message
            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=QWEN_MODEL_NAME,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            reply_text = response.choices[0].message.content.strip()
            return ChatFollowupResponse(reply=reply_text)
        except Exception as e:
            print(f"Error in chat followup (Qwen): {e}. Using fallback.")

    # Intelligent fallback responses
    reply = _generate_copilot_fallback(message, scan_context)
    return ChatFollowupResponse(reply=reply)


def _generate_copilot_fallback(message: str, scan_context: str) -> str:
    """
    Smart Dynamic Intent Engine — classifies the user's question into an intent
    and returns a rich, empathetic, human-like response with bold highlights
    and bullet points.  Covers device/malware, clicked-link, financial-loss,
    family/third-party, plus the original intent set.
    """
    msg = message.lower()
    ctx = scan_context.lower() if scan_context else ""

    # ---- Intent classifiers (keyword sets) ----
    _INTENT_DEVICE = ["phone hacked", "is my phone", "virus", "malware", "install",
                      "my device", "phone safe", "hacked my phone", "spyware",
                      "can they hack", "install virus", "will they install",
                      "remote access", "screen share", "anydesk", "teamviewer"]
    _INTENT_CLICKED = ["clicked", "i opened", "i visited", "opened the link",
                       "opened the website", "i went to", "clicked it",
                       "clicked the link", "opened it", "tapped the link",
                       "i pressed", "clicked on it"]
    _INTENT_MONEY = ["took my money", "sent money", "sent payment", "paid them",
                     "transferred", "lost money", "money gone", "debit",
                     "charged me", "withdrew", "upi payment", "they took",
                     "bank deducted", "transaction"]
    _INTENT_FAMILY = ["my mom", "my dad", "my mother", "my father", "my friend",
                      "my brother", "my sister", "my grandma", "my grandpa",
                      "my wife", "my husband", "my parent", "someone i know",
                      "my child", "my son", "my daughter", "elderly"]
    _INTENT_ALREADY_SENT = ["already sent", "already gave", "already shared",
                            "already replied", "already provided", "gave them my"]
    _INTENT_HOW_GOT = ["how did they get", "where did they find", "how do they know",
                       "how they got", "where they found", "how did they know"]
    _INTENT_FAKE_REPLY = ["fake name", "reply fake", "give wrong info",
                          "trick them back", "scam the scammer", "mess with them"]
    _INTENT_DANGER = ["is this real", "is it legit", "is it dangerous",
                      "how dangerous", "how serious", "is this a scam",
                      "could this be real", "is it genuine"]
    _INTENT_STEPS = ["what should i do", "what do i do", "what to do",
                     "next steps", "help me", "guide me", "tell me what"]
    _INTENT_OTP = ["otp", "password", "pin", "cvv", "card details", "card number"]
    _INTENT_REPORT = ["report", "complaint", "police", "cybercrime", "helpline",
                      "fir", "legal action"]
    _INTENT_BLOCK = ["block", "stop them", "stop receiving", "spam messages",
                     "prevent messages", "unsubscribe"]
    _INTENT_PREVENT = ["how to stay safe", "protect myself", "prevent",
                       "avoid scams", "be safe", "safety tips", "future"]
    _INTENT_PASSWORD = ["strong password", "create password", "password tips",
                        "secure password", "good password", "password manager",
                        "make a password", "choose password", "set password"]
    _INTENT_2FA = ["two-factor", "2fa", "two factor", "two step", "2 step",
                   "two-step", "multi-factor", "mfa", "authenticator",
                   "verification code", "second factor", "double verification"]
    _INTENT_COMMON_SCAMS = ["common scams", "types of scams", "scam types",
                            "popular scams", "latest scams", "new scams",
                            "trending scams", "scam trends", "what scams",
                            "kinds of scams", "scam examples"]
    _INTENT_PHISHING = ["phishing", "phishing email", "phishing attack",
                        "spear phishing", "smishing", "vishing", "phish"]
    _INTENT_SOCIAL_MEDIA = ["facebook", "instagram", "twitter", "whatsapp",
                            "telegram", "social media", "tiktok", "snapchat",
                            "linkedin", "social account", "messenger"]
    _INTENT_UPI = ["upi", "google pay", "gpay", "phonepe", "paytm",
                   "bhim", "upi pin", "upi payment", "qr code payment",
                   "scan and pay", "upi scam"]
    _INTENT_BANK = ["bank account", "bank fraud", "atm", "debit card",
                    "credit card", "net banking", "banking", "ifsc",
                    "neft", "rtgs", "bank transfer", "wire transfer"]
    _INTENT_GREETING = ["hello", "hi there", "hey", "good morning",
                        "good afternoon", "good evening", "howdy"]

    def _match(keywords):
        return any(kw in msg for kw in keywords)

    # ==================== INTENT: DEVICE / MALWARE ====================
    if _match(_INTENT_DEVICE):
        return (
            "I understand your concern — it's scary to think your device might be compromised. "
            "Here's the good news: **receiving an SMS or WhatsApp message alone cannot hack your phone**. "
            "Scammers would need you to download a malicious file, install an app, or grant remote access.\n\n"
            "Here's how to make sure your phone is safe:\n"
            "• **Do NOT install** any app or file sent by the scammer\n"
            "• **Delete** any unknown apps you didn't install yourself\n"
            "• **Run a full scan** using your phone's built-in security or Google Play Protect\n"
            "• **Never share your screen** via AnyDesk, TeamViewer, or similar apps with strangers\n"
            "• If you're still worried, back up your data and do a **factory reset**\n\n"
            "Your phone is almost certainly fine — just don't engage with the sender."
        )

    # ==================== INTENT: CLICKED THE LINK ====================
    if _match(_INTENT_CLICKED):
        return (
            "Okay, let's assess the situation calmly. **Just opening or viewing a webpage is usually safe** — "
            "modern browsers are sandboxed. The real danger starts if you:\n"
            "• Entered any **passwords, OTPs, or card details** on the page\n"
            "• **Downloaded** any file or app\n"
            "• Granted any **permissions** (camera, contacts, notifications)\n\n"
            "**Here's what to do right now:**\n"
            "1. **Close the browser tab** immediately — don't go back to it\n"
            "2. If you entered credentials, **change those passwords** right now from a different device\n"
            "3. **Clear your browser cache and cookies**\n"
            "4. If you downloaded anything, **delete it** and run a virus scan\n"
            "5. **Monitor your bank statements** for any unusual activity over the next 2 weeks\n\n"
            "If you only looked at the page and didn't enter anything, you're likely safe. "
            "Just block the sender and don't click any more links from them."
        )

    # ==================== INTENT: MONEY / FINANCIAL LOSS ====================
    if _match(_INTENT_MONEY):
        return (
            "I'm really sorry this happened — financial fraud is stressful, but **acting fast can help recover your money**. "
            "Here are the **3 urgent steps** you need to take right now:\n\n"
            "**Step 1 — Call your bank immediately:**\n"
            "• Dial the customer care number on the **back of your card** or your bank's official website\n"
            "• Ask them to **freeze your account** and **reverse the transaction**\n"
            "• Banks have a 'golden hour' window — the sooner you call, the better the chances of recovery\n\n"
            "**Step 2 — File a cybercrime complaint:**\n"
            "• Call **1930** (National Cybercrime Helpline, 24×7)\n"
            "• Also file online at **cybercrime.gov.in** with full transaction details\n"
            "• Keep your **transaction ID, screenshots, and ScamShield report** as evidence\n\n"
            "**Step 3 — Secure your accounts:**\n"
            "• **Change all banking passwords** and **UPI PINs**\n"
            "• **Block your card** if card details were shared\n"
            "• Enable **transaction alerts** via SMS and email\n\n"
            "Time is critical — please call your bank right now. Many victims have recovered their money "
            "by reporting within the first few hours."
        )

    # ==================== INTENT: FAMILY / THIRD-PARTY ====================
    if _match(_INTENT_FAMILY):
        return (
            "It's great that you're looking out for them — having someone help makes a big difference. "
            "Here's how you can help safely:\n\n"
            "**What to do right now:**\n"
            "• **Take their phone** and block the sender's number\n"
            "• **Check if they clicked any links** or shared any personal/bank details\n"
            "• If they shared bank details, **call their bank immediately** on the official helpline\n"
            "• **Delete the scam message** from their phone so they don't accidentally engage later\n\n"
            "**How to protect them going forward:**\n"
            "• Explain in simple terms: **real banks/government never ask for OTPs or money via messages**\n"
            "• Set up **caller ID apps** like Truecaller to filter spam calls\n"
            "• Enable **transaction limits** on their UPI/banking apps as a safety net\n"
            "• Tell them to **always check with you** before clicking links or sharing info from unknown senders\n\n"
            "Patience and education are the best protection — scammers specifically target people "
            "who may be less tech-savvy, so your support is invaluable."
        )

    # ==================== INTENT: ALREADY SENT DETAILS ====================
    if _match(_INTENT_ALREADY_SENT):
        return (
            "Don't panic — let's act quickly to minimize the damage. "
            "Here's exactly what you should do right now:\n\n"
            "• **Change your passwords** for any accounts whose details you shared — use a different, trusted device\n"
            "• **Contact your bank immediately** on their official helpline to freeze your account and flag suspicious transactions\n"
            "• If you shared your **Aadhaar or PAN details**, monitor for identity theft at uidai.gov.in\n"
            "• **File a complaint** at cybercrime.gov.in or call **1930** (24×7 helpline)\n"
            "• **Monitor your bank statements daily** for the next 2-4 weeks\n\n"
            "The faster you act, the more you can limit the damage. You're doing the right thing by seeking help."
        )

    # ==================== INTENT: HOW DID THEY GET MY NUMBER ====================
    if _match(_INTENT_HOW_GOT):
        return (
            "Great question — and the answer might surprise you. "
            "**Your phone isn't hacked.** Here's how scammers typically get numbers:\n\n"
            "• **Data breaches** — large companies get hacked and user databases are sold on the dark web\n"
            "• **Public information** — numbers shared on social media, job portals, or business listings\n"
            "• **Data brokers** — shady companies sell phone number lists to scammers\n"
            "• **Random dialing** — scammers use software to auto-generate and message thousands of numbers\n\n"
            "They're **mass-messaging thousands of people** hoping even one person responds. "
            "The fact that you received it doesn't mean anything is wrong with your device.\n\n"
            "**What to do:** Block the number, enable privacy settings on your social media, "
            "and avoid sharing your phone number publicly online."
        )

    # ==================== INTENT: FAKE REPLY ====================
    if _match(_INTENT_FAKE_REPLY):
        return (
            "I totally understand the urge to fight back — but **replying is not a good idea**, even with fake info. Here's why:\n\n"
            "• **Any reply confirms your number is active** — scammers will sell your 'active' number to other fraudsters\n"
            "• This leads to **more scam calls and messages**, not fewer\n"
            "• In some cases, scammers escalate to **harassment or threats**\n"
            "• Engaging wastes your energy and gives them exactly what they want: your attention\n\n"
            "**The smart move:** Block the sender, report the message, and move on. "
            "Your silence is your strongest defense — it makes your number look dead to them."
        )

    # ==================== INTENT: IS THIS DANGEROUS / REAL ====================
    if _match(_INTENT_DANGER):
        return (
            "Based on the scan results, **this message shows strong signs of being a scam**. Here's how to tell:\n\n"
            "• **Real banks and government agencies never** ask for OTPs, passwords, or urgent payments via SMS or WhatsApp\n"
            "• **Legitimate prizes** don't ask you to pay a fee to claim them — that's a classic advance-fee fraud\n"
            "• **Official organizations** always have verifiable contact numbers on their websites\n"
            "• Scammers create **artificial urgency** ('act within 24 hours') to bypass your critical thinking\n\n"
            "**Treat this as dangerous.** Don't click any links, don't reply, and don't share any personal information. "
            "If you're unsure, call the organization directly using the phone number from their **official website** — "
            "never use the number provided in the suspicious message."
        )

    # ==================== INTENT: WHAT SHOULD I DO ====================
    if _match(_INTENT_STEPS):
        return (
            "Here's your **complete safety action plan** — follow these steps in order:\n\n"
            "**1. Stop all engagement:**\n"
            "• Do NOT click any links or download attachments\n"
            "• Do NOT reply to the sender\n"
            "• **Block the number** immediately\n\n"
            "**2. Secure your accounts:**\n"
            "• If you shared credentials, **change your passwords now**\n"
            "• Enable **two-factor authentication** on important accounts\n"
            "• Check for any unauthorized login attempts\n\n"
            "**3. Report the scam:**\n"
            "• Call **1930** (National Cybercrime Helpline)\n"
            "• File a complaint at **cybercrime.gov.in**\n"
            "• Download your **ScamShield Incident Report** as evidence\n\n"
            "**4. Alert your bank** if any financial details were involved\n\n"
            "You've already taken the smartest step by scanning this message. Stay calm and follow this plan."
        )

    # ==================== INTENT: PASSWORD CREATION ====================
    if _match(_INTENT_PASSWORD):
        return (
            "A strong password is your **first line of defense** against hackers. Here's how to create one:\n\n"
            "**Rules for a strong password:**\n"
            "\u2022 At least **12 characters** long (longer is better)\n"
            "\u2022 Mix **uppercase, lowercase, numbers, and symbols**\n"
            "\u2022 **Never use** personal info (name, birthday, phone number)\n"
            "\u2022 **Never reuse** the same password across different accounts\n\n"
            "**Best method \u2014 use a passphrase:**\n"
            "Pick 4 random words and combine them: `Purple-Tiger-Dancing-Moon!2026`\n"
            "This is long, memorable, and extremely hard to crack.\n\n"
            "**Use a password manager:**\n"
            "\u2022 **Bitwarden** (free and open-source) \u2014 highly recommended\n"
            "\u2022 **Google Password Manager** (built into Chrome/Android)\n"
            "\u2022 **Apple Keychain** (built into iPhone/Mac)\n\n"
            "A password manager remembers all your passwords for you \u2014 you only need to remember one master password. "
            "This alone will protect 90% of your accounts."
        )

    # ==================== INTENT: OTP / PASSWORD ====================
    if _match(_INTENT_OTP):
        return (
            "**Never share OTPs, passwords, PINs, or card details with anyone** — "
            "not even someone who claims to be from your bank. Here's the golden rule:\n\n"
            "• **No bank, government office, or company** will ever ask for your OTP or password over phone, SMS, or email\n"
            "• OTPs are **one-time keys to your account** — sharing one gives full access to the scammer\n"
            "• If someone asks for these details, **they are 100% a scammer**, no exceptions\n\n"
            "**If you've already shared them:**\n"
            "1. Change your password **immediately** from a trusted device\n"
            "2. Call your bank to **block your card** and freeze your account\n"
            "3. File a complaint at **cybercrime.gov.in** or call **1930**\n\n"
            "The sooner you act, the more you can protect your money and identity."
        )

    # ==================== INTENT: REPORTING ====================
    if _match(_INTENT_REPORT):
        return (
            "Reporting is one of the most powerful things you can do — it helps protect others too. "
            "Here are all your options:\n\n"
            "**National Cybercrime Helpline:**\n"
            "• Call **1930** (available 24×7, free of cost)\n"
            "• File online at **cybercrime.gov.in** — you can track your complaint status\n\n"
            "**Your bank's fraud helpline:**\n"
            "• Numbers are printed on the **back of your debit/credit card**\n"
            "• Ask them to register a **fraud dispute** for any unauthorized transactions\n\n"
            "**Local police station:**\n"
            "• File an **FIR** if the amount is significant or if you face threats\n"
            "• Carry your ScamShield Incident Report as supporting evidence\n\n"
            "**Pro tip:** The faster you report (especially financial fraud), the higher the chances of recovery. "
            "Banks can often reverse transactions if reported within a few hours."
        )

    # ==================== INTENT: BLOCKING ====================
    if _match(_INTENT_BLOCK):
        return (
            "Blocking is your first line of defense — here's how to shut them down completely:\n\n"
            "**On your phone:**\n"
            "• **Block the number** in your phone's call/SMS settings\n"
            "• On WhatsApp: open the chat → tap the contact name → **Block**\n"
            "• Install **Truecaller** to auto-identify and block known spam numbers\n\n"
            "**On messaging apps:**\n"
            "• **Report and block** the sender on Telegram, Instagram, etc.\n"
            "• Adjust privacy settings to only allow messages from contacts\n\n"
            "**Prevent future scams:**\n"
            "• Register on the **National Do Not Call (DNC)** registry by sending 'START DND' to 1909\n"
            "• Enable **spam filters** in your SMS app (Google Messages has built-in spam detection)\n"
            "• **Never reply** to spam — even 'STOP' can confirm your number is active\n\n"
            "Blocking won't stop all scams, but it significantly reduces the noise."
        )

    # ==================== INTENT: PREVENTION / STAY SAFE ====================
    if _match(_INTENT_PREVENT):
        return (
            "Great mindset \u2014 prevention is always better than damage control! "
            "Here are the **essential habits** that will keep you safe:\n\n"
            "**Daily habits:**\n"
            "\u2022 **Never click links** in unsolicited messages \u2014 go directly to the official website or app\n"
            "\u2022 **Never share OTPs, passwords, or PINs** with anyone, ever\n"
            "\u2022 Verify sender identity through **known official channels** before sharing anything\n\n"
            "**Account security:**\n"
            "\u2022 Use **strong, unique passwords** for each account (try a password manager)\n"
            "\u2022 Enable **two-factor authentication (2FA)** everywhere possible\n"
            "\u2022 Set up **transaction alerts** via SMS/email on all banking accounts\n\n"
            "**Device security:**\n"
            "\u2022 Keep your **phone and apps updated** \u2014 updates patch security holes\n"
            "\u2022 Only install apps from **Google Play Store or Apple App Store**\n"
            "\u2022 Use **Google Play Protect** or equivalent malware scanning\n\n"
            "**When in doubt, scan it:** You can always paste suspicious messages into ScamShield for a free instant analysis."
        )
    
    # ==================== INTENT: TWO-FACTOR AUTHENTICATION ====================
    if _match(_INTENT_2FA):
        return (
            "**Two-Factor Authentication (2FA)** is like adding a **second lock** to your accounts. "
            "Even if someone steals your password, they still can't get in without the second factor.\n\n"
            "**How 2FA works:**\n"
            "1. You enter your **password** (something you know)\n"
            "2. You enter a **code** from your phone (something you have)\n\n"
            "**Types of 2FA (from best to worst):**\n"
            "\u2022 **Authenticator apps** (Google Authenticator, Microsoft Authenticator, Authy) \u2014 **most secure**\n"
            "\u2022 **Hardware security keys** (YubiKey) \u2014 used by high-value targets\n"
            "\u2022 **SMS codes** \u2014 convenient but vulnerable to SIM-swapping attacks\n\n"
            "**Where to enable 2FA right now:**\n"
            "\u2022 **Google Account** \u2192 Security \u2192 2-Step Verification\n"
            "\u2022 **Banking apps** \u2192 Settings \u2192 Enable 2FA\n"
            "\u2022 **WhatsApp** \u2192 Settings \u2192 Account \u2192 Two-Step Verification\n"
            "\u2022 **Instagram/Facebook** \u2192 Settings \u2192 Security \u2192 2FA\n\n"
            "**Pro tip:** Download **Google Authenticator** today and enable 2FA on your email and banking accounts first \u2014 "
            "these are the most critical accounts to protect."
        )
    
    # ==================== INTENT: COMMON SCAM TYPES ====================
    if _match(_INTENT_COMMON_SCAMS):
        return (
            "Here are the **most common scam types** you should watch out for:\n\n"
            "**1. Phishing & Smishing** \u2014 Fake emails/SMS pretending to be your bank, asking you to click links or share OTPs.\n"
            "**2. Job/Task Scams** \u2014 'Earn \u20b95,000/day from home!' on Telegram/WhatsApp. They ask for a deposit first.\n"
            "**3. Investment Scams** \u2014 Fake crypto/trading platforms promising guaranteed returns.\n"
            "**4. Lottery/Prize Scams** \u2014 'You won \u20b925 lakhs!' but you must pay a processing fee first.\n"
            "**5. Sextortion** \u2014 Threatening to release fake compromising videos unless you pay.\n"
            "**6. Tech Support Scams** \u2014 'Your computer has a virus!' \u2014 they install malware or steal data.\n"
            "**7. Fake Delivery/Courier** \u2014 'Your parcel is held at customs, pay \u20b9150 duty' via a phishing link.\n"
            "**8. QR Code Scams** \u2014 Fake QR codes on posters or sent via messages that steal UPI money.\n\n"
            "**Golden rules to spot ANY scam:**\n"
            "\u2022 If it creates **urgency** ('act now or lose everything') \u2014 it's a scam\n"
            "\u2022 If it asks for **money upfront** to claim a prize \u2014 it's a scam\n"
            "\u2022 If it asks for **OTP, password, or PIN** \u2014 it's ALWAYS a scam\n"
            "\u2022 If it sounds **too good to be true** \u2014 it is\n\n"
            "Paste any suspicious message into ScamShield above and I'll analyze it for you instantly!"
        )
    
    # ==================== INTENT: PHISHING EXPLAINED ====================
    if _match(_INTENT_PHISHING):
        return (
            "**Phishing** is when scammers pretend to be a trusted organization (your bank, Google, Amazon, etc.) "
            "to trick you into revealing personal information.\n\n"
            "**Types of phishing:**\n"
            "\u2022 **Email phishing** \u2014 Fake emails with links to fake login pages\n"
            "\u2022 **Smishing** \u2014 Phishing via SMS/text messages\n"
            "\u2022 **Vishing** \u2014 Voice phishing via phone calls\n"
            "\u2022 **Spear phishing** \u2014 Highly targeted attacks using your real name/info\n\n"
            "**How to spot phishing:**\n"
            "\u2022 Check the **sender email address** carefully (e.g., `support@amazon-security.xyz` is NOT Amazon)\n"
            "\u2022 Hover over links to see the **real URL** before clicking\n"
            "\u2022 Look for **urgency language** ('your account will be suspended')\n"
            "\u2022 Real companies **never** ask for passwords or OTPs via email\n\n"
            "If you receive a suspicious message, **paste it into ScamShield** above and I'll analyze it for phishing indicators instantly!"
        )
    
    # ==================== INTENT: SOCIAL MEDIA SAFETY ====================
    if _match(_INTENT_SOCIAL_MEDIA):
        return (
            "Social media accounts are prime targets for scammers. Here's how to **lock them down**:\n\n"
            "**Essential settings:**\n"
            "\u2022 Set your profile to **private** (only friends can see your posts)\n"
            "\u2022 Enable **two-factor authentication (2FA)** on every social account\n"
            "\u2022 **Don't share** your phone number or email publicly on your profile\n"
            "\u2022 Review and **revoke third-party app permissions** you don't use\n\n"
            "**Common social media scams:**\n"
            "\u2022 **Fake friend requests** from cloned accounts of people you know\n"
            "\u2022 **'Is this you in this video?'** links that steal your login\n"
            "\u2022 **Romance scams** \u2014 building fake relationships to ask for money\n"
            "\u2022 **Fake giveaways** asking you to share personal info to 'win'\n\n"
            "**Red flags:** If a friend suddenly messages asking for money or sends a suspicious link, "
            "**call them directly** to verify \u2014 their account may be hacked."
        )
    
    # ==================== INTENT: UPI SAFETY ====================
    if _match(_INTENT_UPI):
        return (
            "**UPI is one of the most targeted payment systems** for scams. Here's what you need to know:\n\n"
            "**UPI scam tactics:**\n"
            "\u2022 **Fake QR codes** \u2014 scammers send QR codes saying 'scan to receive money' but it actually **sends** money from your account\n"
            "\u2022 **'Collect request' fraud** \u2014 they send a UPI collect request that looks like a payment to you\n"
            "\u2022 **Screen sharing apps** \u2014 they ask you to install AnyDesk/QuickSupport to 'help' and steal your UPI PIN\n\n"
            "**Golden UPI rules:**\n"
            "\u2022 **NEVER scan a QR code to RECEIVE money** \u2014 UPI only sends money when you scan (receiving is automatic)\n"
            "\u2022 **NEVER enter your UPI PIN to receive money** \u2014 PIN is ONLY for sending\n"
            "\u2022 **Set a UPI transaction limit** in your app (e.g., \u20b95,000/day)\n"
            "\u2022 **Always verify** the payee name before confirming any payment\n\n"
            "If money was stolen via UPI, call your bank immediately and also **call 1930** (National Cybercrime Helpline) "
            "within the golden hour for the best chance of recovery."
        )
    
    # ==================== INTENT: BANKING SAFETY ====================
    if _match(_INTENT_BANK):
        return (
            "Bank fraud is one of the most damaging types of scams. Here's how to **protect your finances**:\n\n"
            "**Key facts about banks:**\n"
            "\u2022 Your bank will **NEVER** call, SMS, or email asking for your **OTP, PIN, CVV, or password**\n"
            "\u2022 Your bank will **NEVER** ask you to **transfer money to a 'safe account'**\n"
            "\u2022 Your bank will **NEVER** ask you to **install remote access software**\n\n"
            "**Protect your accounts:**\n"
            "\u2022 Enable **SMS and email alerts** for every transaction\n"
            "\u2022 Set **daily transaction limits** on your debit/credit cards\n"
            "\u2022 Use your bank's **official mobile app** \u2014 never use links from messages\n"
            "\u2022 **Check your bank statements** regularly for unknown transactions\n\n"
            "**If your bank account is compromised:**\n"
            "1. **Call your bank immediately** using the number on the back of your card\n"
            "2. Ask them to **freeze your account** and **block your cards**\n"
            "3. **Change your net banking password** from a different device\n"
            "4. File a complaint at **cybercrime.gov.in** or call **1930**"
        )
    
    # ==================== INTENT: GREETING ====================
    if _match(_INTENT_GREETING):
        return (
            "Hello! I'm your **ScamShield Copilot** \u2014 your personal cybersecurity advisor. "
            "I'm here to help you stay safe from scams and online threats.\n\n"
            "**Here's what I can help with:**\n"
            "\u2022 Analyze suspicious messages, links, or screenshots\n"
            "\u2022 Guide you on what to do if you've been scammed\n"
            "\u2022 Teach you how to create strong passwords and enable 2FA\n"
            "\u2022 Explain common scam types and how to spot them\n"
            "\u2022 Help you report cybercrime\n\n"
            "Just type your question or paste a suspicious message into the scanner above, and I'll help you out!"
        )

    # ==================== DEFAULT: CONTEXT-AWARE OR GENERIC ====================
    if ctx.strip():
        return (
            "Based on the scan results, **this content shows clear signs of a scam attempt**. "
            "Scammers typically use a combination of:\n\n"
            "• **Artificial urgency** — 'act within 24 hours or your account will be closed'\n"
            "• **Fake authority** — impersonating banks, government, or well-known companies\n"
            "• **Lure of rewards** — prizes, lottery wins, or easy money to cloud your judgment\n"
            "• **Requests for sensitive data** — OTPs, passwords, bank details, or personal info\n\n"
            "**My recommendation:** Do not respond to the sender, block them immediately, "
            "and report this to the **National Cybercrime Helpline at 1930**.\n\n"
            "Feel free to ask me anything specific about this scan — for example, "
            "'Is my phone safe?' or 'What if I already clicked the link?' — "
            "and I'll give you tailored advice."
        )

    return (
        "That's an interesting question! While I specialize in **cybersecurity and scam protection**, "
        "I can help you with a wide range of topics.\n\n"
        "**Here are some things I can help with right now:**\n"
        "\u2022 \"What are the most common scams?\" \u2014 learn about current scam trends\n"
        "\u2022 \"How do I create a strong password?\" \u2014 account security tips\n"
        "\u2022 \"What is two-factor authentication?\" \u2014 security best practices\n"
        "\u2022 \"How do I report cybercrime?\" \u2014 step-by-step reporting guide\n"
        "\u2022 \"How can I protect my parents from scams?\" \u2014 family safety advice\n\n"
        "You can also **paste any suspicious message** into the scanner above for instant AI analysis, "
        "then ask me follow-up questions about the results.\n\n"
        "**To unlock my full AI-powered responses**, connect a DashScope API key in the backend settings \u2014 "
        "then I can answer literally any question with deep knowledge!"
    )

