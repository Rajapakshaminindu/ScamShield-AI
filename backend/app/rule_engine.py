import re
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
from backend.app.schemas import DetectedIndicator, DomainSpoofInfo

# Sensitive data indicators
SENSITIVE_PATTERNS = [
    (r"\b(otp|one time password|verification code)\b", "Requests One-Time Password (OTP)", "critical"),
    (r"\b(cvv|pin|card number|expiry date|expiration date)\b", "Requests credit/debit card PIN or CVV", "critical"),
    (r"\b(password|passcode|secret key|seed phrase|private key)\b", "Requests confidential password or security key", "critical"),
    (r"\b(social security|ssn|aadhaar|id number|passport number)\b", "Demands national identification number", "high"),
]

# Social engineering & urgency tactics
URGENCY_PATTERNS = [
    (r"\b(immediately|within 24 hours|urgent|urgently|action required|act now|expires soon)\b", "Creates artificial urgency to panic the victim", "high"),
    (r"\b(account suspended|account blocked|deactivated|restricted|frozen|unauthorized access)\b", "Uses fear of account suspension or penalty", "high"),
    (r"\b(arrest warrant|police|court legal action|law enforcement|fbi|irs|tax penalty)\b", "Impersonates law enforcement or legal authorities", "critical"),
]

# Bank account / financial data requests  ->  Critical (+40)
BANK_ACCOUNT_PATTERNS = [
    (r"\b(bank account|account number|routing number|bank details|ifsc code)\b", "Requests bank account or routing details", "critical"),
    (r"\b(send money|transfer (?:fund|amount|payment)|deposit (?:fee|amount)|wire transfer)\b", "Requests money transfer or deposit", "critical"),
    (r"\b(processing fee|service charge|advance fee|registration fee|tax fee)\b", "Demands upfront payment or fee", "critical"),
    (r"\b(pay (?:via|by|through) (?:upi|neft|rtgs|imps|crypto|bitcoin|gift card))\b", "Directs payment through untraceable methods", "critical"),
]

# Personal identification requests  ->  High (+30)
PERSONAL_ID_PATTERNS = [
    (r"\b(full name|complete name|your name as per (?:aadhaar|pan|bank))\b", "Requests full legal name", "high"),
    (r"\b(phone number|mobile number|contact number|registered mobile)\b", "Requests phone / mobile number", "high"),
    (r"\b(date of birth|dob|birth date|age)\b", "Requests date of birth", "high"),
    (r"\b(home address|residential address|mailing address|full address)\b", "Requests residential address", "high"),
    (r"\b(id card|identity card|government id|pan card|voter id|driving license|passport)\b", "Requests government-issued ID details", "high"),
]

# Prize / Investment / Job lures
LURE_PATTERNS = [
    (r"\b(congratulations|won a lottery|lottery winner|cash prize|claim your prize|lucky draw)\b", "Uses unrealistic prize or lottery lure", "high"),
    (r"\b(guaranteed return|double your money|crypto investment|daily profit|zero risk)\b", "Promises unrealistic investment returns", "high"),
    (r"\b(part-time job|earn \$[0-9]+ daily|work from home earn|telegram task)\b", "Uses fake task / job scam pattern", "high"),
]

# Suspicious URL shorteners & TLDs
SUSPICIOUS_DOMAINS = [
    "bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "rb.gy", "shorturl.at", "ow.ly"
]

# Trusted brand domains for spoof detection
TRUSTED_DOMAINS: Dict[str, str] = {
    # Indian Banks
    "hdfc": "hdfcbank.com",
    "sbi": "sbi.co.in",
    "icici": "icicibank.com",
    "axis": "axisbank.com",
    "kotak": "kotak.com",
    "pnb": "pnbindia.in",
    "bob": "bankofbaroda.com",
    "bankofbaroda": "bankofbaroda.com",
    "canara": "canarabank.com",
    "idbi": "idbibank.in",
    "yesbank": "yesbank.in",
    "indusind": "indusind.com",
    "federal": "federalbank.co.in",
    # Indian Financial / Gov Services
    "paytm": "paytm.com",
    "phonepe": "phonepe.com",
    "googlepay": "pay.google.com",
    "irctc": "irctc.co.in",
    "uidai": "uidai.gov.in",
    "aadhaar": "uidai.gov.in",
    "incometax": "incometax.gov.in",
    "epfo": "epfindia.gov.in",
    "lic": "licindia.in",
    # E-commerce & Tech
    "amazon": "amazon.in",
    "flipkart": "flipkart.com",
    "meesho": "meesho.com",
    "google": "google.com",
    "microsoft": "microsoft.com",
    "apple": "apple.com",
    "whatsapp": "whatsapp.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "telegram": "telegram.org",
}

FINANCIAL_SPOOF_KEYWORDS = {
    "bank", "banking", "netbanking", "online", "login", "portal", "verify",
    "secure", "security", "update", "kyc", "alert", "support", "help", "pay",
    "card", "service", "services", "india", "yono", "otp", "auth", "account",
    "bonus", "reward", "cash", "app", "official", "check", "confirm", "claim",
    "free", "gift", "baroda"
}

SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".buzz", ".club", ".work", ".cfd", ".icu", ".rest", ".online"
]

def analyze_text_heuristics(text: str) -> Tuple[int, List[DetectedIndicator], List[str]]:
    """
    Applies rule-based regex analysis on text.
    Returns (calculated_heuristic_score, list_of_indicators, extracted_urls).
    """
    text_lower = text.lower()
    indicators: List[DetectedIndicator] = []
    base_score = 0

    # 1. Sensitive Data Check
    for pattern, desc, severity in SENSITIVE_PATTERNS:
        if re.search(pattern, text_lower):
            indicators.append(DetectedIndicator(
                category="Sensitive Information Request",
                description=desc,
                severity=severity
            ))
            base_score += 35

    # 2. Urgency Check
    for pattern, desc, severity in URGENCY_PATTERNS:
        if re.search(pattern, text_lower):
            indicators.append(DetectedIndicator(
                category="Psychological Urgency & Fear",
                description=desc,
                severity=severity
            ))
            base_score += 25

    # 3. Lure Check
    lure_found = False
    for pattern, desc, severity in LURE_PATTERNS:
        if re.search(pattern, text_lower):
            indicators.append(DetectedIndicator(
                category="Unrealistic Reward / Lure",
                description=desc,
                severity=severity
            ))
            base_score += 25
            lure_found = True

    # 4. Bank Account / Financial Data Requests  (+40 each, critical)
    bank_info_found = False
    for pattern, desc, severity in BANK_ACCOUNT_PATTERNS:
        if re.search(pattern, text_lower):
            indicators.append(DetectedIndicator(
                category="Financial Data / Money Request",
                description=desc,
                severity=severity
            ))
            base_score += 40
            bank_info_found = True

    # 5. Personal Identification Requests  (+30 each, high)
    personal_info_found = False
    for pattern, desc, severity in PERSONAL_ID_PATTERNS:
        if re.search(pattern, text_lower):
            indicators.append(DetectedIndicator(
                category="Personal Information Request",
                description=desc,
                severity=severity
            ))
            base_score += 30
            personal_info_found = True

    # 6. Extract URLs
    url_pattern = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
    urls = re.findall(url_pattern, text)

    for u in urls:
        parsed = urlparse(u if u.startswith("http") else f"http://{u}")
        domain = parsed.netloc.lower()

        # Check shortener
        if any(short in domain for short in SUSPICIOUS_DOMAINS):
            indicators.append(DetectedIndicator(
                category="Obfuscated / Shortened URL",
                description=f"Uses URL shortening service ({domain}) to hide final destination.",
                severity="high"
            ))
            base_score += 20

        # Check suspicious TLD
        if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
            indicators.append(DetectedIndicator(
                category="High-Risk Domain Extension",
                description=f"Domain ends in a high-risk TLD commonly linked to fraud ({domain}).",
                severity="high"
            ))
            base_score += 20

        # Check IP address as domain
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$", domain):
            indicators.append(DetectedIndicator(
                category="Direct IP Host URL",
                description="Uses raw IP address instead of a legitimate registered domain.",
                severity="critical"
            ))
            base_score += 35

    # 7. Advance-Fee Scam Multiplier:
    #    If BOTH a lure (prize/lottery/job) AND a bank/personal info/money request
    #    are present, enforce a minimum score of 90 (Critical).
    score = min(100, base_score)
    if lure_found and (bank_info_found or personal_info_found) and score < 90:
        score = 90

    return score, indicators, urls

def analyze_url_heuristics(url_str: str) -> Tuple[int, List[DetectedIndicator]]:
    """Analyzes a standalone URL."""
    score, indicators, _ = analyze_text_heuristics(url_str)
    return score, indicators


def inspect_domain_spoof(url: str) -> Optional[DomainSpoofInfo]:
    """
    Inspects a URL to check if its domain is spoofing a known trusted brand.
    Returns DomainSpoofInfo if a brand match is found, otherwise None.
    Uses token-boundary matching to prevent false positives on common words
    (e.g., 'click.com', 'public.com', 'bobsburgers.com').
    """
    try:
        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
        full_domain = parsed.netloc.lower()
    except Exception:
        return None

    if not full_domain:
        return None

    # Strip port if present
    if ":" in full_domain:
        full_domain = full_domain.split(":")[0]

    # Strip www. prefix
    if full_domain.startswith("www."):
        full_domain = full_domain[4:]

    # Extract second-level domain + TLD (e.g. "hdfc-bank-verify.xyz" from "login.hdfc-bank-verify.xyz")
    parts = full_domain.split(".")
    # For multi-part TLDs like .co.in, .co.uk keep last 3 parts
    if len(parts) > 2 and parts[-2] in ("co", "com", "org", "net", "gov", "ac"):
        registered_domain = ".".join(parts[-3:])
        tld_suffix = ".".join(parts[-2:])
    elif len(parts) >= 2:
        registered_domain = ".".join(parts[-2:])
        tld_suffix = parts[-1]
    else:
        registered_domain = full_domain
        tld_suffix = ""

    # Strip TLD to get the brand-like portion for matching
    # e.g. "hdfc-bank-verify.xyz" -> "hdfc-bank-verify"
    sld = registered_domain.split(".")[0]  # second-level domain part

    # Split SLD into segments by hyphens
    sld_segments = sld.split("-")

    # Non-TLD hostname for token analysis (e.g. "login.hdfc-bank-verify")
    host_without_tld = full_domain
    if tld_suffix and host_without_tld.endswith("." + tld_suffix):
        host_without_tld = host_without_tld[:-len("." + tld_suffix)]

    tokens = [t for t in re.split(r"[^a-z0-9]+", host_without_tld) if t]

    matched_brand = None
    matched_official = None

    for brand_key, official_domain in TRUSTED_DOMAINS.items():
        # Legitimate official domain or official subdomain (e.g. "mail.google.com")
        if registered_domain == official_domain or full_domain == official_domain:
            continue
        if full_domain.endswith(f".{official_domain}"):
            continue
        # State Bank of India official .sbi gTLD
        if brand_key == "sbi" and (full_domain.endswith(".sbi") or full_domain == "sbi"):
            continue

        is_match = False
        if brand_key == "bob":
            # For Bank of Baroda acronym 'bob', require banking context to prevent false positives on general names
            has_bob = ("bob" in tokens) or any(t.startswith("bob") and (t[3:] in FINANCIAL_SPOOF_KEYWORDS or t[3:].isdigit()) for t in tokens)
            has_context = any(t in FINANCIAL_SPOOF_KEYWORDS for t in tokens)
            if has_bob and has_context:
                is_match = True
        elif brand_key in tokens:
            is_match = True
        else:
            for token in tokens:
                if len(brand_key) >= 5 and brand_key in token:
                    is_match = True
                    break
                if token.startswith(brand_key):
                    rem = token[len(brand_key):]
                    if rem in FINANCIAL_SPOOF_KEYWORDS or rem.isdigit():
                        is_match = True
                        break
                elif token.endswith(brand_key):
                    rem = token[:-len(brand_key)]
                    if rem in FINANCIAL_SPOOF_KEYWORDS or rem.isdigit():
                        is_match = True
                        break

        if is_match:
            matched_brand = brand_key
            matched_official = official_domain
            break

    if matched_brand is None:
        return None

    # Identify fake elements: segments that mimic the brand + suspicious add-ons
    fake_elements = []
    for seg in sld_segments:
        if matched_brand in seg.lower():
            fake_elements.append(seg)
        elif seg.lower() in FINANCIAL_SPOOF_KEYWORDS or seg.lower() in (
            "signin", "net", "web"
        ):
            fake_elements.append(seg)

    # If no specific fake elements found, mark all segments
    if not fake_elements:
        fake_elements = sld_segments

    return DomainSpoofInfo(
        is_spoofed=True,
        spoofed_brand=matched_brand.upper(),
        official_domain=matched_official,
        fake_domain_elements=fake_elements,
        domain_breakdown=full_domain
    )
