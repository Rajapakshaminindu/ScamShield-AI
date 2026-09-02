// ============================================================
// THEME TOGGLE (Light / Dark)
// ============================================================
const THEME_KEY = "scamshield_theme";

function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light") {
        document.documentElement.setAttribute("data-theme", "light");
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    if (next === "light") {
        document.documentElement.setAttribute("data-theme", "light");
    } else {
        document.documentElement.removeAttribute("data-theme");
    }
    localStorage.setItem(THEME_KEY, next);
}

// Apply saved theme immediately (before DOMContentLoaded)
initTheme();

// ============================================================
// INTRO SPLASH ANIMATION
// Plays once per browser session, then reveals the dashboard.
// The fade-out itself is driven by CSS keyframes; this only handles
// the letter reveal, the rotating boot messages and skipping.
// ============================================================
const INTRO_SEEN_KEY = "scamshield_intro_seen";
const INTRO_TITLE = "Welcome to ScamShield AI";
const INTRO_BRAND_WORDS = ["ScamShield", "AI"];
const INTRO_CHAR_START = 750;   // ms before the first letter appears
const INTRO_CHAR_STEP = 45;     // ms between letters
const INTRO_TOTAL = 3850;       // ms until the overlay is fully cleared
const INTRO_STATUS_MESSAGES = [
    "Booting multi-modal threat engine",
    "Loading heuristic scam patterns",
    "Linking Qwen AI reasoning layer",
    "Shield active — you are protected"
];

let introStatusTimer = null;
let introFinishTimer = null;

function initIntro() {
    const overlay = document.getElementById("intro-overlay");
    if (!overlay) return;

    const root = document.documentElement;

    // The inline head script already flagged a repeat visit in this session
    if (root.classList.contains("intro-skipped")) {
        overlay.remove();
        return;
    }

    try {
        sessionStorage.setItem(INTRO_SEEN_KEY, "1");
    } catch (e) {
        /* private mode — intro simply replays next time */
    }

    root.classList.add("intro-active");  // lock scrolling while it plays
    renderIntroTitle();
    startIntroStatusRotation();

    const skipBtn = document.getElementById("intro-skip");
    if (skipBtn) {
        skipBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            skipIntro();
        });
    }
    overlay.addEventListener("click", skipIntro);
    document.addEventListener("keydown", introKeyHandler);

    introFinishTimer = setTimeout(() => finishIntro(overlay), INTRO_TOTAL);
}

function renderIntroTitle() {
    const titleEl = document.getElementById("intro-title");
    if (!titleEl) return;

    let charIndex = 0;
    const html = INTRO_TITLE.split(" ").map(word => {
        const isBrand = INTRO_BRAND_WORDS.includes(word);
        const chars = word.split("").map(ch => {
            const delay = INTRO_CHAR_START + charIndex * INTRO_CHAR_STEP;
            charIndex++;
            return `<span class="intro-char" style="animation-delay:${delay}ms">${ch}</span>`;
        }).join("");
        return `<span class="intro-word${isBrand ? " intro-brand" : ""}">${chars}</span>`;
    }).join(" ");   // real spaces so the headline stays selectable/readable

    titleEl.innerHTML = html;
}

function startIntroStatusRotation() {
    const statusEl = document.getElementById("intro-status-text");
    if (!statusEl) return;

    let i = 0;
    introStatusTimer = setInterval(() => {
        i++;
        if (i >= INTRO_STATUS_MESSAGES.length) {
            clearInterval(introStatusTimer);
            introStatusTimer = null;
            return;
        }
        statusEl.textContent = INTRO_STATUS_MESSAGES[i];
    }, 700);
}

function introKeyHandler(e) {
    if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
        skipIntro();
    }
}

function skipIntro() {
    const overlay = document.getElementById("intro-overlay");
    if (!overlay) return;
    document.documentElement.classList.add("intro-done");
    if (introFinishTimer) clearTimeout(introFinishTimer);
    introFinishTimer = setTimeout(() => finishIntro(overlay), 420);
}

function finishIntro(overlay) {
    if (introStatusTimer) clearInterval(introStatusTimer);
    document.removeEventListener("keydown", introKeyHandler);
    document.documentElement.classList.remove("intro-active");
    if (overlay && overlay.parentNode) overlay.remove();
}

// Start the intro as soon as the markup is parsed (script sits at end of body)
initIntro();

// ============================================================
// USER MENU (Login state / Logout)
// ============================================================
function getUserToken() {
    return localStorage.getItem('scamshield_token');
}

function getLoggedUser() {
    try {
        return JSON.parse(localStorage.getItem('scamshield_user'));
    } catch { return null; }
}

function renderUserMenu() {
    const menu = document.getElementById('user-menu');
    if (!menu) return;
    const user = getLoggedUser();
    const token = getUserToken();

    if (user && token) {
        let html = `<div class="user-menu-info">
            <span class="user-menu-name">${user.username}</span>
            <span class="user-menu-role">${user.role === 'admin' ? 'Admin' : 'User'}</span>
        </div>`;
        if (user.role === 'admin') {
            html += `<a href="/admin" class="btn-link">Dashboard</a>`;
        }
        html += `<button class="btn-logout" onclick="logoutUser()">Logout</button>`;
        menu.innerHTML = html;
    } else {
        menu.innerHTML = `<a href="/login" class="btn-link">Sign In</a>`;
    }
}

function logoutUser() {
    localStorage.removeItem('scamshield_token');
    localStorage.removeItem('scamshield_user');
    renderUserMenu();
    window.location.href = '/login';
}

function authHeaders() {
    const token = getUserToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

// ============================================================
// LIVE COMMUNITY THREAT RADAR
// ============================================================
const THREAT_ALERTS = [
    { icon: "\u{1F6A8}", label: "Electricity Bill Cutoff WhatsApp Scam", text: "Dear consumer, your electricity connection will be disconnected today at 6 PM due to pending bill. Pay immediately by clicking http://electricity-bill-pay.xyz and enter your card details to avoid disconnection." },
    { icon: "\u26A0\uFE0F", label: "Fake Customs Tax SMS", text: "Your international parcel is held at customs. Pay Rs. 2,500 duty immediately at http://india-customs-duty-pay.com to release your package. Failure to pay within 2 hours will result in confiscation." },
    { icon: "\u{1F6A8}", label: "HDFC Bank KYC Update Phishing", text: "URGENT: Your HDFC Bank account has been blocked due to pending KYC. Update immediately at http://hdfc-kyc-verify.xyz or your account will be permanently closed within 24 hours." },
    { icon: "\u{1F6A8}", label: "SBI ATM Card Blocked Scam", text: "Dear SBI Customer, your ATM card has been blocked. Verify your identity by entering OTP at http://sbi-verify-card.in within 30 minutes or face permanent account freeze." },
    { icon: "\u26A0\uFE0F", label: "IRCTC Ticket Refund Fraud", text: "Your IRCTC train ticket has been cancelled. Claim your full refund of Rs. 1,850 by visiting http://irctc-refund-claim.co.in and entering your bank account and IFSC code." },
    { icon: "\u{1F6A8}", label: "Aadhaar-PAN Linking Scam", text: "MANDATORY: Link your Aadhaar with PAN card before deadline. Visit http://uidai-aadhaar-link-pan.com and pay Rs. 50 processing fee to complete linking. Penalty applies if delayed." },
    { icon: "\u{1F4B0}", label: "Part-Time Job Task Scam on Telegram", text: "Earn Rs. 5000-15000 daily from home! Simple YouTube like tasks. No experience needed. Join Telegram channel http://t.co/fakeEarningTask for instant payment via UPI. Limited slots available!" },
    { icon: "\u{1F381}", label: "Kaun Banega Crorepati Lucky Draw", text: "CONGRATULATIONS! Your mobile number won Rs. 25,00,000 in KBC Lucky Draw 2025! Send your name, bank account number, and IFSC code to claim your prize. Contact +91-98XXXX via WhatsApp." }
];

function initThreatTicker() {
    const track = document.getElementById('ticker-track');
    if (!track) return;
    // Build items twice for seamless infinite scroll
    const buildItems = () => THREAT_ALERTS.map((alert, i) =>
        `<button class="ticker-item" onclick="loadThreatAlert(${i})">${alert.icon} ${alert.label}</button>`
    ).join('');
    track.innerHTML = buildItems() + buildItems();
}

function loadThreatAlert(index) {
    const alert = THREAT_ALERTS[index];
    if (!alert) return;
    // Switch to text tab
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.querySelector('[data-tab="text-tab"]').classList.add('active');
    document.getElementById('text-tab').classList.add('active');
    // Fill the textarea
    const textarea = document.getElementById('text-input');
    textarea.value = alert.text;
    textarea.style.borderColor = 'var(--accent-cyan)';
    setTimeout(() => { textarea.style.borderColor = ''; }, 800);
    // Scroll to input
    textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ============================================================
// CYBER SAFETY TIPS
// ============================================================
const CYBER_SAFETY_TIPS = [
    "Bank staff will NEVER ask for your OTP or card PIN over phone, SMS, or email. Hang up and call the official number.",
    "Never click links in unsolicited messages claiming your account is blocked. Always visit the bank's website directly.",
    "Government agencies like the Income Tax Department will never demand payment via gift cards, crypto, or UPI to unknown accounts.",
    "If a job offers 'easy money' for simple tasks on Telegram or WhatsApp, it's a scam. Real jobs have formal hiring processes.",
    "Always check the URL carefully before entering credentials. Phishing sites often use hyphens and misspellings (e.g., hdfc-bank-verify.xyz).",
    "Enable two-factor authentication (2FA) on all your important accounts — banking, email, and social media.",
    "If you receive a call claiming to be from your bank, hang up and dial the official customer care number printed on your card.",
    "Never share screenshots of your banking apps or payment confirmations with strangers on messaging apps.",
    "Report all cyber fraud immediately to the National Cybercrime Helpline: 1930 or visit cybercrime.gov.in.",
    "Before investing, verify the platform with SEBI. Unregistered investment schemes offering 'guaranteed returns' are always scams."
];

let currentTipIndex = 0;
let tipRotationInterval = null;

function initCyberTips() {
    currentTipIndex = Math.floor(Math.random() * CYBER_SAFETY_TIPS.length);
    showCurrentTip();
    // Auto-rotate every 8 seconds
    tipRotationInterval = setInterval(() => {
        currentTipIndex = (currentTipIndex + 1) % CYBER_SAFETY_TIPS.length;
        showCurrentTip();
    }, 8000);
}

function showCurrentTip() {
    const tipEl = document.getElementById('tip-text');
    if (!tipEl) return;
    tipEl.style.opacity = '0';
    setTimeout(() => {
        tipEl.textContent = `"${CYBER_SAFETY_TIPS[currentTipIndex]}"`;
        tipEl.style.opacity = '1';
    }, 200);
}

function rotateTipNext() {
    currentTipIndex = (currentTipIndex + 1) % CYBER_SAFETY_TIPS.length;
    showCurrentTip();
    // Reset auto-rotation timer
    if (tipRotationInterval) clearInterval(tipRotationInterval);
    tipRotationInterval = setInterval(() => {
        currentTipIndex = (currentTipIndex + 1) % CYBER_SAFETY_TIPS.length;
        showCurrentTip();
    }, 8000);
}

// ============================================================
// TAB SWITCHING
// ============================================================
// Tab Switching Logic
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        button.classList.add('active');
        const targetId = button.getAttribute('data-tab');
        document.getElementById(targetId).classList.add('active');
    });
});

// Demo Presets
const PRESETS = {
    bank: "URGENT: Your HDFC Bank account has been blocked due to suspicious activity. Update your KYC immediately by visiting http://hdfc-kyc-verify.xyz and verify your OTP within 10 minutes to avoid permanent suspension.",
    lottery: "CONGRATULATIONS! Your mobile number has won $50,000 in the International Coca-Cola Lucky Draw! Send your full name, bank account number, and 4-digit security PIN to claim-prize@promo-reward.online to receive your cash.",
    job: "Work from home and earn $200-$500 per day! Complete simple YouTube video like tasks. No experience required. Join our Telegram channel http://t.co/fakeTaskJob to get paid instantly via crypto.",
    safe: "Your order #82910 from Amazon has been shipped via Courier Express. Track delivery on the official Amazon app. No action is required."
};

function loadPreset(key) {
    const textInput = document.getElementById('text-input');
    if (PRESETS[key]) {
        textInput.value = PRESETS[key];
        // Visual feedback flash
        textInput.style.borderColor = 'var(--accent-cyan)';
        setTimeout(() => { textInput.style.borderColor = ''; }, 600);
    }
}

// File Selection Feedback
let selectedImageFile = null;
let selectedVoiceFile = null;

function handleImageSelected(event) {
    const file = event.target.files[0];
    if (file) {
        selectedImageFile = file;
        document.getElementById('image-upload-title').innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }
}

function handleVoiceSelected(event) {
    const file = event.target.files[0];
    if (file) {
        selectedVoiceFile = file;
        document.getElementById('voice-upload-title').innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }
}

// Clear / Refresh all inputs
function clearActiveInput() {
    // Clear text input
    const textInput = document.getElementById('text-input');
    if (textInput) textInput.value = '';

    // Clear URL input
    const urlInput = document.getElementById('url-input');
    if (urlInput) urlInput.value = '';

    // Reset file inputs
    const screenshotFile = document.getElementById('screenshot-file');
    if (screenshotFile) screenshotFile.value = '';
    selectedImageFile = null;
    const imgTitle = document.getElementById('image-upload-title');
    if (imgTitle) imgTitle.innerText = 'Click or Drag & Drop screenshot';

    const voiceFile = document.getElementById('voice-file');
    if (voiceFile) voiceFile.value = '';
    selectedVoiceFile = null;
    const voiceTitle = document.getElementById('voice-upload-title');
    if (voiceTitle) voiceTitle.innerText = 'Upload voice recording or audio message';

    // Visual feedback: spin the refresh icon
    const btn = document.getElementById('refresh-input-btn');
    if (btn) {
        const svg = btn.querySelector('svg');
        if (svg) {
            svg.style.transition = 'transform 0.5s ease';
            svg.style.transform = 'rotate(-360deg)';
            setTimeout(() => {
                svg.style.transition = 'none';
                svg.style.transform = 'rotate(0deg)';
            }, 500);
        }
    }
}

// ============================================================
// SCAN HISTORY (localStorage)
// ============================================================
const SCAN_HISTORY_KEY = "scamshield_scan_history";
const MAX_HISTORY = 5;
let currentScanData = null;
let currentScanMeta = { inputType: "", input: "", timestamp: "" };

function saveToHistory(data) {
    const entry = {
        timestamp: new Date().toISOString(),
        inputType: currentScanMeta.inputType,
        input: currentScanMeta.input,
        data: data
    };
    const history = loadHistory();
    history.unshift(entry); // newest first
    // Keep only last MAX_HISTORY
    while (history.length > MAX_HISTORY) history.pop();
    localStorage.setItem(SCAN_HISTORY_KEY, JSON.stringify(history));
    renderHistoryBar();
}

function loadHistory() {
    try {
        const raw = localStorage.getItem(SCAN_HISTORY_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function renderHistoryBar() {
    const scroll = document.getElementById('history-scroll');
    const empty = document.getElementById('history-empty');
    if (!scroll) return;

    const history = loadHistory();
    // Clear existing cards
    scroll.querySelectorAll('.history-card').forEach(c => c.remove());

    if (history.length === 0) {
        if (empty) empty.style.display = 'block';
        return;
    }
    if (empty) empty.style.display = 'none';

    history.forEach((entry, i) => {
        const card = document.createElement('div');
        card.className = 'history-card';
        const d = entry.data;
        const ts = new Date(entry.timestamp);
        const timeStr = ts.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' + ts.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

        let riskColor = '#10B981';
        if (d.risk_score >= 80) riskColor = '#EF4444';
        else if (d.risk_score >= 60) riskColor = '#F97316';
        else if (d.risk_score >= 30) riskColor = '#FBBF24';

        card.innerHTML = `
            <div class="history-score" style="border-color:${riskColor};color:${riskColor}">${d.risk_score}</div>
            <div class="history-info">
                <span class="history-type">${d.scam_type || 'Scan'}</span>
                <span class="history-time">${timeStr}</span>
            </div>
        `;
        card.addEventListener('click', () => {
            displayResults(d);
        });
        scroll.appendChild(card);
    });
}

function clearHistory() {
    localStorage.removeItem(SCAN_HISTORY_KEY);
    renderHistoryBar();
}

// ============================================================
// INCIDENT REPORT DOWNLOAD
// ============================================================
function downloadIncidentReport() {
    if (!currentScanData) {
        alert('No scan data available. Run a scan first.');
        return;
    }
    const d = currentScanData;
    const now = new Date();
    const ts = now.toISOString().replace('T', ' ').substring(0, 19);
    const fileTs = now.getFullYear() + '-' +
        String(now.getMonth()+1).padStart(2,'0') + '-' +
        String(now.getDate()).padStart(2,'0') + '_' +
        String(now.getHours()).padStart(2,'0') +
        String(now.getMinutes()).padStart(2,'0') +
        String(now.getSeconds()).padStart(2,'0');

    let report = '';
    report += '================================================================\n';
    report += '           SCAMSHIELD AI - INCIDENT REPORT\n';
    report += '================================================================\n';
    report += `Report Generated: ${ts}\n`;
    report += `Input Type: ${currentScanMeta.inputType || 'N/A'}\n`;
    report += '----------------------------------------------------------------\n\n';

    report += '--- RISK ASSESSMENT ---\n';
    report += `Risk Score: ${d.risk_score} / 100\n`;
    report += `Risk Level: ${d.risk_level}\n`;
    report += `Scam Type:  ${d.scam_type || 'N/A'}\n\n`;

    report += '--- SUMMARY ---\n';
    report += `${d.summary}\n\n`;

    if (currentScanMeta.input) {
        report += '--- ORIGINAL INPUT ---\n';
        report += `${currentScanMeta.input}\n\n`;
    }

    report += '--- DETECTED RED FLAGS ---\n';
    if (d.detected_indicators && d.detected_indicators.length > 0) {
        d.detected_indicators.forEach((ind, i) => {
            report += `  ${i+1}. [${ind.severity.toUpperCase()}] ${ind.description}\n`;
            report += `     Category: ${ind.category}\n`;
        });
    } else {
        report += '  No suspicious indicators detected.\n';
    }
    report += '\n';

    if (d.explanation && d.explanation.length > 0) {
        report += '--- WHY IS THIS DANGEROUS? ---\n';
        d.explanation.forEach((exp, i) => {
            report += `  ${i+1}. ${exp}\n`;
        });
        report += '\n';
    }

    report += '--- SAFETY RECOMMENDATIONS ---\n';
    report += '  DO:\n';
    (d.recommended_dos || []).forEach((item, i) => {
        report += `    ${i+1}. ${item}\n`;
    });
    report += '  DO NOT:\n';
    (d.recommended_donts || []).forEach((item, i) => {
        report += `    ${i+1}. ${item}\n`;
    });
    report += '\n';

    if (d.domain_spoof && d.domain_spoof.is_spoofed) {
        report += '--- DOMAIN SPOOF DETAILS ---\n';
        report += `  Spoofed Brand:   ${d.domain_spoof.spoofed_brand}\n`;
        report += `  Fake Domain:     ${d.domain_spoof.domain_breakdown}\n`;
        report += `  Official Domain: ${d.domain_spoof.official_domain}\n\n`;
    }

    report += '================================================================\n';
    report += 'This report was generated by ScamShield AI for informational\n';
    report += 'purposes. It can be submitted as supporting evidence when filing\n';
    report += 'a complaint with your bank, cybercrime cell, or local police.\n';
    report += 'National Cybercrime Helpline: 1930 | cybercrime.gov.in\n';
    report += '================================================================\n';

    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `incident_report_${fileTs}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================================
// UI STATE MANAGEMENT
// ============================================================
function showLoading(show) {
    const loader = document.getElementById('loading-state');
    loader.style.display = show ? 'flex' : 'none';
}

function displayResults(data) {
    currentScanData = data;
    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.style.display = 'none';
    const content = document.getElementById('results-content');
    content.style.display = 'block';
    // Apply fade-in animation
    content.classList.remove('fade-in');
    void content.offsetWidth; // Force reflow to restart animation
    content.classList.add('fade-in');

    // Show download button
    const dlBtn = document.getElementById('download-report-btn');
    if (dlBtn) dlBtn.style.display = 'flex';

    // 1. Gauge & Risk Badge
    const score = data.risk_score;
    const scoreElem = document.getElementById('gauge-score');
    const circleElem = document.getElementById('gauge-circle');
    const badgeElem = document.getElementById('risk-badge');
    const titleElem = document.getElementById('scam-type-title');
    const summaryElem = document.getElementById('summary-text');

    scoreElem.innerText = score;
    titleElem.innerText = data.scam_type || "Analysis Result";
    summaryElem.innerText = data.summary;
    badgeElem.innerText = `${data.risk_level.toUpperCase()} RISK`;

    // Set colors based on risk
    let riskColor = '#10B981'; // Green
    if (score >= 80) riskColor = '#EF4444'; // Red
    else if (score >= 60) riskColor = '#F97316'; // Orange
    else if (score >= 30) riskColor = '#FBBF24'; // Yellow

    circleElem.style.borderColor = riskColor;
    circleElem.style.boxShadow = `0 0 24px ${riskColor}55`;
    badgeElem.style.color = riskColor;
    badgeElem.style.borderColor = `${riskColor}66`;
    badgeElem.style.backgroundColor = `${riskColor}1A`;

    // 2. Extracted Text (for Image/Voice)
    const extractedBox = document.getElementById('extracted-box');
    const extractedContent = document.getElementById('extracted-text-content');
    if (data.extracted_text && data.extracted_text !== document.getElementById('text-input').value) {
        extractedBox.style.display = 'block';
        extractedContent.innerText = data.extracted_text;
    } else {
        extractedBox.style.display = 'none';
    }

    // 3. Indicators
    const indicatorsList = document.getElementById('indicators-list');
    indicatorsList.innerHTML = '';
    if (data.detected_indicators && data.detected_indicators.length > 0) {
        data.detected_indicators.forEach(ind => {
            const chip = document.createElement('div');
            chip.className = `ind-chip ${ind.severity || 'medium'}`;
            chip.innerText = `⚠️ ${ind.description}`;
            indicatorsList.appendChild(chip);
        });
    } else {
        indicatorsList.innerHTML = '<span style="color:#9CA3AF; font-size:13px;">No suspicious red flags found.</span>';
    }

    // 4. Why Dangerous (Explanation)
    const explanationList = document.getElementById('explanation-list');
    explanationList.innerHTML = '';
    if (data.explanation && data.explanation.length > 0) {
        data.explanation.forEach(exp => {
            const li = document.createElement('li');
            li.innerText = exp;
            explanationList.appendChild(li);
        });
    }

    // 5. Dos and Don'ts
    const dosList = document.getElementById('dos-list');
    const dontsList = document.getElementById('donts-list');
    dosList.innerHTML = '';
    dontsList.innerHTML = '';

    (data.recommended_dos || []).forEach(item => {
        const li = document.createElement('li');
        li.innerText = item;
        dosList.appendChild(li);
    });

    (data.recommended_donts || []).forEach(item => {
        const li = document.createElement('li');
        li.innerText = item;
        dontsList.appendChild(li);
    });

    // 6. Domain Spoof Breakdown
    const domainCard = document.getElementById('domain-breakdown-card');
    const domainVisual = document.getElementById('domain-visual');
    const domainRef = document.getElementById('domain-ref');
    if (domainCard) domainCard.style.display = 'none';

    if (data.domain_spoof && data.domain_spoof.is_spoofed) {
        if (domainCard) domainCard.style.display = 'block';
        if (domainVisual) {
            const spoof = data.domain_spoof;
            const fullDomain = spoof.domain_breakdown;
            const fakeElements = (spoof.fake_domain_elements || []).map(e => e.toLowerCase());
            // Split domain by dots and hyphens, color each segment
            const parts = fullDomain.split(/([.-])/);
            let html = '';
            parts.forEach(part => {
                if (part === '.' || part === '-') {
                    html += `<span class="domain-sep">${part}</span>`;
                } else if (fakeElements.some(fe => part.toLowerCase().includes(fe.toLowerCase()) || fe.toLowerCase().includes(part.toLowerCase()))) {
                    html += `<span class="domain-segment fake">${part}</span>`;
                } else {
                    html += `<span class="domain-segment">${part}</span>`;
                }
            });
            domainVisual.innerHTML = html;
        }
        if (domainRef) {
            domainRef.innerHTML = `<span class="official-ref">\u2705 Official domain: <strong>${data.domain_spoof.official_domain}</strong></span>`;
        }
    }

    // 7. Save to history
    saveToHistory(data);
}

// API Callers
async function submitTextAnalysis() {
    const text = document.getElementById('text-input').value.trim();
    if (!text) {
        alert('Please enter a message to analyze.');
        return;
    }

    showLoading(true);
    currentScanMeta = { inputType: "Text / SMS", input: text, timestamp: new Date().toISOString() };
    try {
        const response = await fetch('/api/analyze/text', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ text })
        });
        const data = await response.json();
        displayResults(data);
    } catch (err) {
        console.error(err);
        alert('Error connecting to backend API: ' + err.message);
    } finally {
        showLoading(false);
    }
}

async function submitUrlAnalysis() {
    const url = document.getElementById('url-input').value.trim();
    if (!url) {
        alert('Please enter a URL to inspect.');
        return;
    }

    showLoading(true);
    currentScanMeta = { inputType: "URL / Link", input: url, timestamp: new Date().toISOString() };
    try {
        const response = await fetch('/api/analyze/url', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ url })
        });
        const data = await response.json();
        displayResults(data);
    } catch (err) {
        console.error(err);
        alert('Error connecting to backend API: ' + err.message);
    } finally {
        showLoading(false);
    }
}

async function submitScreenshotAnalysis() {
    if (!selectedImageFile) {
        alert('Please select or drop a screenshot first.');
        return;
    }

    showLoading(true);
    currentScanMeta = { inputType: "Screenshot", input: selectedImageFile ? selectedImageFile.name : "", timestamp: new Date().toISOString() };
    try {
        const formData = new FormData();
        formData.append('file', selectedImageFile);

        const response = await fetch('/api/analyze/screenshot', {
            method: 'POST',
            headers: getUserToken() ? { 'Authorization': `Bearer ${getUserToken()}` } : {},
            body: formData
        });
        const data = await response.json();
        displayResults(data);
    } catch (err) {
        console.error(err);
        alert('Error analyzing screenshot: ' + err.message);
    } finally {
        showLoading(false);
    }
}

async function submitVoiceAnalysis() {
    if (!selectedVoiceFile) {
        alert('Please select an audio file first.');
        return;
    }

    showLoading(true);
    currentScanMeta = { inputType: "Voice Audio", input: selectedVoiceFile ? selectedVoiceFile.name : "", timestamp: new Date().toISOString() };
    try {
        const formData = new FormData();
        formData.append('file', selectedVoiceFile);

        const response = await fetch('/api/analyze/voice', {
            method: 'POST',
            headers: getUserToken() ? { 'Authorization': `Bearer ${getUserToken()}` } : {},
            body: formData
        });
        const data = await response.json();
        displayResults(data);
    } catch (err) {
        console.error(err);
        alert('Error analyzing audio: ' + err.message);
    } finally {
        showLoading(false);
    }
}

// ============================================================
// AI COPILOT CHAT
// ============================================================
let chatHistory = []; // { role: 'user'|'assistant', content: string }
let copilotVisible = false;

function buildScanContext() {
    if (!currentScanData) return "";
    const d = currentScanData;
    let ctx = `Risk Score: ${d.risk_score}/100 | Risk Level: ${d.risk_level} | Scam Type: ${d.scam_type || 'N/A'}\n`;
    ctx += `Summary: ${d.summary}\n`;
    if (d.detected_indicators && d.detected_indicators.length > 0) {
        ctx += `Detected Indicators: ${d.detected_indicators.map(i => i.description).join('; ')}\n`;
    }
    if (d.domain_spoof && d.domain_spoof.is_spoofed) {
        ctx += `Domain Spoof: ${d.domain_spoof.domain_breakdown} impersonates ${d.domain_spoof.spoofed_brand} (official: ${d.domain_spoof.official_domain})\n`;
    }
    if (currentScanMeta.input) {
        ctx += `Original Input: ${currentScanMeta.input.substring(0, 200)}`;
    }
    return ctx;
}

function formatCopilotText(text) {
    // Convert **bold** to <strong>
    let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Split into paragraphs by double newlines
    const paragraphs = html.split(/\n\n+/);
    let result = '';
    for (const para of paragraphs) {
        const lines = para.split('\n');
        // Check if lines are list items (bullet or numbered)
        const isBulletList = lines.every(l => l.trim().startsWith('•') || l.trim() === '');
        const isNumberedList = lines.every(l => /^\d+\.\s/.test(l.trim()) || l.trim() === '');
        if (isBulletList && lines.some(l => l.trim().startsWith('•'))) {
            result += '<ul class="bubble-list">';
            lines.forEach(l => {
                const trimmed = l.trim();
                if (trimmed.startsWith('•')) {
                    result += `<li>${trimmed.substring(1).trim()}</li>`;
                }
            });
            result += '</ul>';
        } else if (isNumberedList && lines.some(l => /^\d+\.\s/.test(l.trim()))) {
            result += '<ol class="bubble-list">';
            lines.forEach(l => {
                const trimmed = l.trim();
                const match = trimmed.match(/^\d+\.\s(.+)/);
                if (match) result += `<li>${match[1]}</li>`;
            });
            result += '</ol>';
        } else {
            // Regular paragraph with single line breaks
            const content = lines.map(l => l.trim()).filter(l => l).join('<br>');
            if (content) result += `<p>${content}</p>`;
        }
    }
    return result;
}

function addChatBubble(role, text) {
    const container = document.getElementById('copilot-messages');
    if (!container) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role === 'user' ? 'user-bubble' : 'bot-bubble'} fade-in`;

    const avatarSvg = role === 'user'
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`;

    // Format text: rich formatting for bot, plain for user
    const formatted = role === 'user'
        ? `<p>${text.replace(/\n/g, '<br>')}</p>`
        : formatCopilotText(text);

    bubble.innerHTML = `
        <div class="bubble-avatar ${role === 'user' ? 'user-avatar' : 'bot-avatar'}">${avatarSvg}</div>
        <div class="bubble-content">${formatted}</div>
    `;
    container.appendChild(bubble);
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

async function sendChatMessage() {
    const input = document.getElementById('copilot-input');
    const message = input.value.trim();
    if (!message) return;

    // Clear input and disable send while processing
    input.value = '';
    input.disabled = true;

    // Add user bubble
    addChatBubble('user', message);
    chatHistory.push({ role: 'user', content: message });

    // Show typing indicator with label
    const typing = document.getElementById('copilot-typing');
    if (typing) {
        typing.style.display = 'flex';
        typing.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Build scan context
    const scanContext = buildScanContext();

    try {
        const response = await fetch('/api/chat/followup', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                message: message,
                scan_context: scanContext,
                chat_history: chatHistory.slice(-10) // last 10 messages
            })
        });
        const data = await response.json();
        if (typing) typing.style.display = 'none';
        addChatBubble('assistant', data.reply || "I'm sorry, I couldn't generate a response. Please try again.");
        chatHistory.push({ role: 'assistant', content: data.reply });
    } catch (err) {
        if (typing) typing.style.display = 'none';
        addChatBubble('assistant', "Connection error. Please check that the backend server is running and try again.");
        console.error('Chat error:', err);
    } finally {
        input.disabled = false;
        input.focus();
    }
}

function askQuickQuestion(question) {
    document.getElementById('copilot-input').value = question;
    sendChatMessage();
}

function showCopilot() {
    const section = document.getElementById('copilot-section');
    if (section) {
        section.style.display = 'block';
        section.classList.remove('fade-in');
        void section.offsetWidth;
        section.classList.add('fade-in');
        copilotVisible = true;
    }
}

function toggleCopilot() {
    const section = document.getElementById('copilot-section');
    const toggle = document.getElementById('copilot-toggle');
    if (!section) return;
    if (copilotVisible) {
        // Minimize: hide messages/quick/input but keep header
        section.classList.add('copilot-minimized');
        copilotVisible = false;
        if (toggle) toggle.classList.add('minimized');
    } else {
        section.classList.remove('copilot-minimized');
        copilotVisible = true;
        if (toggle) toggle.classList.remove('minimized');
    }
}

// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initThreatTicker();
    renderHistoryBar();
    initCyberTips();
    initDragDrop();
    renderUserMenu();
    // Copilot is always visible
    copilotVisible = true;
    // Copilot input: send on Enter key
    const copilotInput = document.getElementById('copilot-input');
    if (copilotInput) {
        copilotInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
});

// ============================================================
// DRAG & DROP VISUAL FEEDBACK
// ============================================================
function initDragDrop() {
    const zones = [
        { el: document.getElementById('image-dropzone'), input: 'screenshot-file' },
        { el: document.getElementById('voice-dropzone'), input: 'voice-file' }
    ];
    zones.forEach(({ el, input }) => {
        if (!el) return;
        ['dragenter', 'dragover'].forEach(evt => {
            el.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                el.classList.add('drag-over');
            });
        });
        ['dragleave', 'drop'].forEach(evt => {
            el.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                el.classList.remove('drag-over');
            });
        });
        el.addEventListener('drop', (e) => {
            const fileInput = document.getElementById(input);
            if (e.dataTransfer.files.length > 0 && fileInput) {
                fileInput.files = e.dataTransfer.files;
                // Trigger the onchange
                const event = new Event('change');
                fileInput.dispatchEvent(event);
            }
        });
    });
}
