"""
AI Fact Checker — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import time

from web_research import research_claim, build_search_query, extract_keywords
from fact_analysis import FactChecker

app = FastAPI(title="AI Fact Checker", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

checker = FactChecker()


class AnalyzeRequest(BaseModel):
    text: str
    custom_query: Optional[str] = None


@app.get("/")
def root():
    return {"status": "AI Fact Checker API v2.0 running"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    text = req.text.strip()
    if len(text) < 30:
        raise HTTPException(400, "Text must be at least 30 characters.")
    if len(text) > 10000:
        text = text[:10000]

    t0 = time.time()

    # Step 1: Research
    research = research_claim(text, query_override=req.custom_query)

    # Step 2: Analyze
    result = checker.analyze(text, research)
    result["processing_time_ms"] = round((time.time() - t0) * 1000)

    return result


@app.post("/summarize")
def summarize_only(req: AnalyzeRequest):
    from nlp_engine import Summarizer, Paraphraser
    s = Summarizer()
    p = Paraphraser()
    summary = s.summarize(req.text, num_sentences=4)
    paraphrase = p.paraphrase(summary["summary"])
    simplified = p.simplify(req.text)
    return {
        "summary": summary,
        "paraphrase": paraphrase,
        "simplified": simplified
    }


@app.post("/keywords")
def keywords(req: AnalyzeRequest):
    kw = extract_keywords(req.text)
    query = build_search_query(req.text)
    return {"keywords": kw, "suggested_query": query}


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
