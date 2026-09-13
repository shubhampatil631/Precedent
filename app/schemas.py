from typing import Literal, Optional
from pydantic import BaseModel, Field

class HandleMessageRequest(BaseModel):
    customer_text: str = Field(..., description="Inbound customer message")

class RetrievedExample(BaseModel):
    thread_id: str
    customer_text: str
    brand_text: str
    similarity: float

class HandleMessageResponse(BaseModel):
    intent: str
    confidence: float
    retrieved: list[RetrievedExample] = []
    draft_reply: str
    cited_thread_ids: list[str] = []
    decision: Literal["auto_handle", "escalate"]
    reason: str
    rule_fired: Optional[str] = None
    system_name: Optional[str] = "full"
    latency_ms: Optional[float] = None
    cost_estimate: Optional[float] = None
