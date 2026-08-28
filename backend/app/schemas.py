from pydantic import BaseModel, Field
from typing import List, Optional

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., description="Message content or SMS text to analyze")

class URLAnalysisRequest(BaseModel):
    url: str = Field(..., description="Suspicious URL to analyze")

class DetectedIndicator(BaseModel):
    category: str = Field(..., description="E.g. Urgency, Sensitive Info, Suspicious Domain")
    description: str = Field(..., description="Description of why this indicator was flagged")
    severity: str = Field("medium", description="low, medium, high, critical")

class DomainSpoofInfo(BaseModel):
    is_spoofed: bool = Field(..., description="Whether the domain appears to spoof a known brand")
    spoofed_brand: Optional[str] = Field(None, description="Name of the brand being spoofed")
    official_domain: Optional[str] = Field(None, description="The legitimate official domain for that brand")
    fake_domain_elements: List[str] = Field(default_factory=list, description="Suspicious segments found in the fake domain")
    domain_breakdown: str = Field("", description="The full domain string being analyzed")

class ScamAnalysisResponse(BaseModel):
    is_scam: bool
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0 to 100")
    risk_level: str = Field(..., description="Low, Medium, High, or Critical")
    scam_type: str = Field(..., description="Phishing, Investment Scam, Fake Job, OTP Theft, Impersonation, Safe, etc.")
    extracted_text: Optional[str] = None
    summary: str = Field(..., description="Short executive summary of the finding")
    detected_indicators: List[DetectedIndicator] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list, description="Why is this dangerous?")
    recommended_dos: List[str] = Field(default_factory=list, description="Things you SHOULD do")
    recommended_donts: List[str] = Field(default_factory=list, description="Things you MUST NOT do")
    domain_spoof: Optional[DomainSpoofInfo] = Field(None, description="Domain spoof inspection result if URL was analyzed")

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")

class ChatFollowupRequest(BaseModel):
    message: str = Field(..., description="The user's follow-up question")
    scan_context: str = Field("", description="Summary of the last scan result for context")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="Previous messages in this chat session")

class ChatFollowupResponse(BaseModel):
    reply: str = Field(..., description="The AI copilot's response")
