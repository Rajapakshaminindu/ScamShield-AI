"""
Tests for rule-based heuristics and detection indicators.
"""
import pytest
from backend.app.rule_engine import (
    analyze_text_heuristics,
    analyze_url_heuristics,
    inspect_domain_spoof,
)

def test_benign_text():
    text = "Hello Minindu, hope you are having a wonderful day! Let us meet tomorrow at 10 AM."
    score, indicators, urls = analyze_text_heuristics(text)
    assert score == 0
    assert len(indicators) == 0
    assert len(urls) == 0

def test_sensitive_info_detection():
    text = "Please enter your OTP and credit card cvv to confirm your order."
    score, indicators, urls = analyze_text_heuristics(text)
    assert score >= 35
    categories = [i.category for i in indicators]
    assert "Sensitive Information Request" in categories

def test_urgency_detection():
    text = "Action required immediately! Your account is blocked due to unauthorized access."
    score, indicators, urls = analyze_text_heuristics(text)
    assert score >= 25
    categories = [i.category for i in indicators]
    assert "Psychological Urgency & Fear" in categories

def test_advance_fee_scam_multiplier():
    text = "Congratulations! You won a lottery cash prize of $50,000. Send processing fee deposit to claim."
    score, indicators, urls = analyze_text_heuristics(text)
    assert score >= 90

def test_shortened_url_indicator():
    url = "https://bit.ly/claim-prize-now"
    score, indicators = analyze_url_heuristics(url)
    assert score >= 20
    descriptions = [i.description for i in indicators]
    assert any("shortening service" in d for d in descriptions)

def test_suspicious_tld_indicator():
    url = "https://verify-banking-account.xyz"
    score, indicators = analyze_url_heuristics(url)
    assert score >= 20
    descriptions = [i.description for i in indicators]
    assert any("high-risk TLD" in d for d in descriptions)

def test_raw_ip_address_indicator():
    url = "http://192.168.1.100/login"
    score, indicators = analyze_url_heuristics(url)
    assert score >= 35
    descriptions = [i.description for i in indicators]
    assert any("raw IP address" in d for d in descriptions)

def test_official_domains_not_spoofed():
    assert inspect_domain_spoof("https://google.com") is None
    assert inspect_domain_spoof("https://mail.google.com") is None
    assert inspect_domain_spoof("https://hdfcbank.com") is None
