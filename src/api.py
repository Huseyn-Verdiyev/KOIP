"""
RetentionAI — FastAPI Backend
Run: uvicorn src.api:app --reload --port 8000
"""

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent))

from analyzer import analyze_feedback
from offer_generator import generate_special_offer

app = FastAPI(title="RetentionAI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (our HTML UI)
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

DATA_PATH = Path(__file__).parent.parent / "data" / "customers.json"


# ── Models ──────────────────────────────────────────

class RunRequest(BaseModel):
    customer_id: str


# ── Routes ──────────────────────────────────────────

@app.get("/")
def serve_ui():
    """Serve the main HTML UI."""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/customers")
def get_customers():
    """Return all customer profiles categorized."""
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _find_customer(customer_id: str):
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return next((c for c in data if c["customer_id"] == customer_id), None)
    all_cust = data.get("corporate", []) + data.get("individual", [])
    return next((c for c in all_cust if c["customer_id"] == customer_id), None)


@app.post("/api/run")
def run_retention(req: RunRequest):
    """
    Run both pathways for a single customer.
    Returns analysis + Luma offer + offer_params.
    """
    customer = _find_customer(req.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {req.customer_id} not found")

    try:
        analysis = analyze_feedback(customer["feedback"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyzer error: {e}")

    try:
        offer_result = generate_special_offer(
            text=customer["feedback"],
            analysis=analysis,
            customer_data=customer,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Offer generator error: {e}")

    return {
        "customer": customer,
        "analysis": analysis,
        "offer": offer_result["message"],
        "offer_params": offer_result["offer_params"],
    }


@app.post("/api/run-all")
def run_all():
    """Run retention pipeline for all customers."""
    with open(DATA_PATH, encoding="utf-8") as f:
        customers = json.load(f)

    results = []
    for customer in customers:
        try:
            analysis = analyze_feedback(customer["feedback"])
            offer_result = generate_special_offer(
                text=customer["feedback"],
                analysis=analysis,
                customer_data=customer,
            )
            results.append({
                "customer": customer,
                "analysis": analysis,
                "offer": offer_result["message"],
                "offer_params": offer_result["offer_params"],
                "status": "success",
            })
        except Exception as e:
            results.append({
                "customer": customer,
                "status": "error",
                "error": str(e),
            })

    return {"results": results}
