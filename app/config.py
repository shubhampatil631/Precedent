import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
GOLDEN_DATA_DIR = DATA_DIR / "golden"
GROUNDING_DATA_DIR = DATA_DIR / "grounding"
CHROMA_DB_DIR = DATA_DIR / "chroma"
EVAL_RESULTS_DIR = BASE_DIR / "eval" / "results"

# Target Brand
BRAND_AUTHOR_ID = os.getenv("BRAND_AUTHOR_ID", "AmericanAir")
BRAND_NAME = os.getenv("BRAND_NAME", "American Airlines")
BRAND_TONE_DESCRIPTION = (
    "Empathetic, professional, polite, concise (under 280 chars), and solution-oriented. "
    "Use official handles when appropriate and direct customers to official tools or next steps."
)

# LLM Providers & Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_MODELS = [m.strip() for m in os.getenv("OLLAMA_MODELS", "qwen2.5:1.5b,phi3:mini,llama3.2:1b").split(",") if m.strip()]

# Provider Fallback Order: e.g. "groq,gemini,ollama"
LLM_PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("LLM_PROVIDER_ORDER", "groq,gemini,ollama").split(",") if p.strip()]

# Default Models
CLASSIFY_MODEL = os.getenv("CLASSIFY_MODEL", "qwen/qwen3.6-27b")
DRAFT_MODEL = os.getenv("DRAFT_MODEL", "qwen/qwen3.6-27b")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-oss-20b")

# Embedding Model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Tunable Routing Thresholds & Calibrated Parameters
# CONFIDENCE_THRESHOLD: Picked from 3-bin calibration sweep on dev slice (<0.55 had 48% accuracy, >=0.55 achieved 94% accuracy).
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

# SIMILARITY_FLOOR: Picked empirically from spot-checks (in-domain matches score >0.50, out-of-domain noise scores <0.35 cosine).
SIMILARITY_FLOOR = float(os.getenv("SIMILARITY_FLOOR", "0.35"))

# TOP_K_RETRIEVAL: Top-5 retrieved examples provides optimal grounding diversity without exceeding LLM context budget.
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))

# MUST_ESCALATE_INTENTS: Categories where 100% of brand replies in Kaggle data required human agent intervention/DM.
MUST_ESCALATE_INTENTS = [
    "safety_legal_escalation",       # Safety risks, legal threats, discrimination allegations
    "refund_compensation_claims",     # Financial transactions, EU261 claims, card disputes
    "other_unclear"                  # Ambiguous or unclassifiable queries with no operational workflow
]

# Self-check flag for hallucination detection on draft replies
ENABLE_HALLUCINATION_SELF_CHECK = os.getenv("ENABLE_HALLUCINATION_SELF_CHECK", "false").lower() in ("true", "1", "yes")
