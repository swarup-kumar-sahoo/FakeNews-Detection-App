"""
Fact Analysis Engine
Compares input text against researched evidence.
Produces truth score, verdict, and human-readable explanations.
"""

import re
import math
from typing import List, Dict, Tuple, Optional
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from nlp_engine import TextProcessor, Summarizer, Paraphraser, ClaimExtractor, HumanReadableReport


# ── Sentiment / Tone Detector ──────────────────────────────────────────────────
EMOTIONAL_HIGH = set("""
shocking outrageous bombshell explosive scandal horrifying devastating
unbelievable insane terrifying disgusting unforgivable evil destroy
obliterate exposed cover-up conspiracy hoax scam fraud corrupt criminal
traitor liar fake rigged alarming catastrophic unprecedented
""".split())

EMOTIONAL_MED = set("""
alarming concerning troubling worrying suspicious questionable controversial
disputed alleged claimed reportedly supposedly apparently possible claimed
""".split())

NEUTRAL_INDICATORS = set("""
study research data evidence analysis published confirmed according
statistics survey peer-reviewed journal laboratory trial experiment
""".split())

CLICKBAIT_PATTERNS = [
    r"you won'?t believe",
    r"doctors hate",
    r"one (weird|simple|secret) trick",
    r"what (they|the government|media) (don'?t|won'?t) (want|tell)",
    r"wake up (people|america|sheeple)",
    r"share before (they delete|it'?s removed|censored)",
    r"mainstream media (hiding|ignoring|suppressing)",
    r"(breaking|urgent|exclusive)[\s!:]+",
    r"\bhoax\b|\bplandemic\b|\bdeepstate\b|\bfalse ?flag\b",
]

# ── Source Credibility Database ────────────────────────────────────────────────
HIGH_CRED_DOMAINS = {
    "wikipedia.org": 90, "reuters.com": 92, "apnews.com": 92,
    "bbc.com": 88, "bbc.co.uk": 88, "theguardian.com": 83,
    "nytimes.com": 85, "washingtonpost.com": 84, "economist.com": 87,
    "nature.com": 96, "science.org": 96, "thelancet.com": 95,
    "nejm.org": 96, "who.int": 90, "cdc.gov": 90, "nih.gov": 90,
    "ncbi.nlm.nih.gov": 92, "pubmed.ncbi.nlm.nih.gov": 92,
    "harvard.edu": 88, "mit.edu": 88, "oxford.ac.uk": 88,
    "stanford.edu": 88, "snopes.com": 80, "politifact.com": 80,
    "factcheck.org": 80, "fullfact.org": 80, "afp.com": 85,
    "npr.org": 82, "pbs.org": 82, "thehindu.com": 85, "indianexpress.com": 82, "hindustantimes.com": 85,
    "ndtv.com": 80
}
LOW_CRED_DOMAINS = {
    "infowars.com": 10, "naturalnews.com": 12, "breitbart.com": 25,
    "dailywire.com": 30, "thedailybeast.com": 35, "buzzfeed.com": 40,
    "blogspot.com": 30, "wordpress.com": 35, "tumblr.com": 30,
}

def get_domain_score(url: str) -> Tuple[int, str]:
    if not url:
        return 50, "unknown"
    try:
        domain = url.split("/")[2].replace("www.", "")
    except Exception:
        return 50, "unknown"
    
    for d, score in HIGH_CRED_DOMAINS.items():
        if d in domain:
            return score, "high"
    for d, score in LOW_CRED_DOMAINS.items():
        if d in domain:
            return score, "low"
    
    # .gov and .edu bonus
    if domain.endswith(".gov"): return 85, "high"
    if domain.endswith(".edu"): return 80, "high"
    if domain.endswith(".org"): return 62, "medium"
    return 50, "medium"


# ── Content Similarity Analyzer ───────────────────────────────────────────────
class ContentAnalyzer:
    """Compare input text against evidence corpus using TF-IDF similarity."""

    def __init__(self):
        self.processor = TextProcessor()

    def compute_coverage(self, input_text: str, evidence_corpus: str) -> Dict:
        """How much of the input content is covered/supported by evidence."""
        if not evidence_corpus or len(evidence_corpus) < 50:
            return {"coverage_score": 0, "matched_sentences": [], "contradiction_signals": []}

        input_sents = self.processor.split_sentences(input_text)
        evidence_sents = self.processor.split_sentences(evidence_corpus)

        if not input_sents or not evidence_sents:
            return {"coverage_score": 0, "matched_sentences": [], "contradiction_signals": []}

        try:
            all_sents = input_sents + evidence_sents
            tfidf = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=800)
            matrix = tfidf.fit_transform(all_sents)

            input_vecs = matrix[:len(input_sents)]
            evidence_vecs = matrix[len(input_sents):]

            sim_matrix = cosine_similarity(input_vecs, evidence_vecs)

            matched = []
            unmatched = []
            for i, row in enumerate(sim_matrix):
                best_sim = float(np.max(row))
                best_evidence_idx = int(np.argmax(row))
                if best_sim > 0.12:
                    matched.append({
                        "input_sentence": input_sents[i][:200],
                        "similarity": round(best_sim * 100, 1),
                        "matched_with": evidence_sents[best_evidence_idx][:200]
                    })
                else:
                    unmatched.append(input_sents[i][:150])

            coverage = len(matched) / max(len(input_sents), 1)

            # Look for contradiction signals (negation words near shared terms)
            contradiction_signals = self._detect_contradictions(input_text, evidence_corpus)

            return {
                "coverage_score": round(coverage * 100, 1),
                "matched_count": len(matched),
                "unmatched_count": len(unmatched),
                "matched_sentences": matched[:4],
                "unmatched_sentences": unmatched[:3],
                "contradiction_signals": contradiction_signals
            }

        except Exception as e:
            return {"coverage_score": 0, "matched_sentences": [], "contradiction_signals": [], "error": str(e)}

    def _detect_contradictions(self, input_text: str, evidence: str) -> List[str]:
        """Detect potential contradictions between input and evidence."""
        contradictions = []

        # Extract numbers from both
        input_nums = re.findall(r'\b\d+\.?\d*\s*(?:%|percent|million|billion)?\b', input_text)
        evidence_nums = re.findall(r'\b\d+\.?\d*\s*(?:%|percent|million|billion)?\b', evidence)

        # Flag if significant numbers in input don't appear in evidence
        for num in input_nums:
            clean_num = re.sub(r'\s+', '', num.lower())
            if len(clean_num) > 2 and clean_num not in evidence.lower().replace(" ", ""):
                contradictions.append(f"Number '{num}' from input not found in sources")
            if len(contradictions) >= 2:
                break

        # Negation check
        neg_pattern = r'\b(not|never|no|false|incorrect|wrong|contrary|opposite)\b'
        input_negations = len(re.findall(neg_pattern, input_text, re.I))
        evidence_negations = len(re.findall(neg_pattern, evidence, re.I))
        if abs(input_negations - evidence_negations) > 3:
            contradictions.append("Significant difference in negative/denial language vs sources")

        return contradictions[:3]


# ── Bias & Tone Analyzer ───────────────────────────────────────────────────────
def analyze_tone(text: str) -> Dict:
    words = text.lower().split()
    high = [w for w in words if w.strip(".,!?\"'") in EMOTIONAL_HIGH]
    medium = [w for w in words if w.strip(".,!?\"'") in EMOTIONAL_MED]
    neutral = [w for w in words if w.strip(".,!?\"'") in NEUTRAL_INDICATORS]
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 2]
    exclaims = text.count("!")
    
    # Clickbait detection
    clickbait_found = []
    for pattern in CLICKBAIT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            clickbait_found.append(m.group()[:50])

    score = len(high) * 3 + len(medium) * 1.5
    word_count = max(len(words), 1)
    normalized = min(10.0, score / word_count * 100)

    severity = "HIGH" if normalized > 3.5 else "MEDIUM" if normalized > 1.5 else "LOW"

    return {
        "high_emotion_words": list(set(high))[:5],
        "medium_emotion_words": list(set(medium))[:4],
        "neutral_indicators": list(set(neutral))[:4],
        "caps_words": caps_words[:5],
        "exclamation_count": exclaims,
        "clickbait_patterns": clickbait_found[:3],
        "emotional_score": round(normalized, 1),
        "severity": severity,
        "is_biased": severity in ("HIGH", "MEDIUM"),
        "tone_summary": _tone_summary(severity, len(neutral), len(high), clickbait_found)
    }

def _tone_summary(severity, neutral_count, high_count, clickbait):
    if clickbait:
        return "Uses clickbait tactics designed to provoke emotional response rather than inform."
    if severity == "HIGH":
        return "Highly emotional language detected. Reads more like opinion/persuasion than factual reporting."
    if severity == "MEDIUM":
        return "Some emotional language present. Partially objective but contains persuasive framing."
    if neutral_count > high_count:
        return "Largely neutral, factual tone. Uses evidence-based language."
    return "Mostly neutral tone with minor emotive elements."


# ── Main Analysis Orchestrator ─────────────────────────────────────────────────
class FactChecker:
    def __init__(self):
        self.processor = TextProcessor()
        self.summarizer = Summarizer()
        self.paraphraser = Paraphraser()
        self.claim_extractor = ClaimExtractor()
        self.content_analyzer = ContentAnalyzer()
        self.report_generator = HumanReadableReport()

    def analyze(self, input_text: str, research_results: Dict) -> Dict:
        """Full analysis pipeline."""

        # 1. Extract claims
        claims = self.claim_extractor.extract(input_text)

        # 2. Tone analysis
        tone = analyze_tone(input_text)

        # 3. Summarize input
        input_summary = self.summarizer.summarize(input_text, num_sentences=3, source_label="Your Input")

        # 4. Paraphrase
        paraphrase_result = self.paraphraser.paraphrase(
            input_summary["summary"] if len(input_text) > 500 else input_text
        )
        simplified = self.paraphraser.simplify(input_text)

        # 5. Summarize research findings
        sources = research_results.get("all_sources", [])
        corpus = research_results.get("raw_text_corpus", "")

        source_summaries = []
        for src in sources[:4]:
            if src.get("text") and len(src["text"]) > 100:
                s = self.summarizer.summarize(src["text"], num_sentences=2, source_label=src.get("title",""))
                source_summaries.append({**s, "url": src.get("url",""), "type": src.get("type","")})

        multi_summary = self.summarizer.multi_source_summary(sources[:4]) if sources else ""

        # 6. Content coverage / similarity
        coverage = self.content_analyzer.compute_coverage(input_text, corpus)

        # 7. Source credibility
        source_scores = []
        for src in sources:
            score, level = get_domain_score(src.get("url", ""))
            source_scores.append({"title": src.get("title",""), "score": score, "level": level,
                                   "url": src.get("url",""), "type": src.get("type","")})
        avg_source_cred = sum(s["score"] for s in source_scores) / max(len(source_scores), 1)

        # 8. Compute truth score
        truth_score, verdict, score_breakdown = self._compute_score(
            tone, coverage, source_scores, claims, research_results
        )

        # 9. Build issues list
        issues = self._build_issues(tone, coverage, source_scores, claims, research_results)

        # 10. Generate human explanation
        analysis_meta = {
            "truth_score": truth_score,
            "verdict": verdict,
            "issues": issues,
            "claims_count": len(claims),
            "sources_checked": len(sources),
            "wiki_coverage": len(research_results.get("wikipedia", [])) > 0,
        }
        human_explanation = self.report_generator.generate_explanation(analysis_meta)

        # 11. Format sources for display
        formatted_sources = [
            self.report_generator.format_source(src, i)
            for i, src in enumerate(sources[:6])
        ]

        return {
            "truth_score": truth_score,
            "verdict": verdict,
            "confidence_label": self.report_generator.get_confidence_label(truth_score),
            "human_explanation": human_explanation,
            "issues": issues,
            "score_breakdown": score_breakdown,
            "input_analysis": {
                "word_count": len(input_text.split()),
                "sentence_count": len(self.processor.split_sentences(input_text)),
                "summary": input_summary["summary"],
                "simplified": simplified,
                "paraphrased": paraphrase_result["paraphrased"],
                "words_changed_pct": paraphrase_result["words_changed_pct"],
                "tone": tone,
            },
            "claims": claims,
            "research": {
                "query_used": research_results.get("query_used", ""),
                "keywords": research_results.get("keywords", []),
                "total_sources": len(sources),
                "wikipedia_found": len(research_results.get("wikipedia", [])),
                "news_found": len(research_results.get("news", [])),
                "combined_summary": multi_summary,
                "source_summaries": source_summaries,
                "coverage": coverage,
            },
            "sources": formatted_sources,
            "source_credibility": {
                "average_score": round(avg_source_cred, 1),
                "scores": source_scores
            }
        }

    def _compute_score(self, tone: Dict, coverage: Dict, source_scores: List,
                       claims: List, research: Dict) -> Tuple[int, str, Dict]:
        score = 50.0
        breakdown = {}

        # Coverage signal (how much input overlaps with evidence)
        cov = coverage.get("coverage_score", 0)
        cov_pts = (cov - 40) * 0.35
        score += cov_pts
        breakdown["evidence_coverage"] = round(cov, 1)

        # Source credibility
        if source_scores:
            avg = sum(s["score"] for s in source_scores) / len(source_scores)
            high_count = sum(1 for s in source_scores if s["level"] == "high")
            cred_pts = (avg - 50) * 0.15 + high_count * 3
            score += cred_pts
            breakdown["source_credibility"] = round(avg, 1)
        else:
            score -= 5
            breakdown["source_credibility"] = 0

        # Tone penalties
        if tone["severity"] == "HIGH":
            score -= 18
        elif tone["severity"] == "MEDIUM":
            score -= 7
        if tone["clickbait_patterns"]:
            score -= 12
        breakdown["tone_penalty"] = tone["emotional_score"]

        # Research depth
        wiki_count = len(research.get("wikipedia", []))
        news_count = len(research.get("news", []))
        depth_bonus = min(8, wiki_count * 3 + news_count * 1)
        score += depth_bonus
        breakdown["research_depth_bonus"] = depth_bonus

        # Contradiction penalty
        contras = len(coverage.get("contradiction_signals", []))
        score -= contras * 5
        breakdown["contradiction_penalty"] = contras * 5

        # Caps / exclamation penalties
        if tone["exclamation_count"] > 3: score -= 5
        if len(tone["caps_words"]) > 3: score -= 5

        score = max(0, min(100, round(score)))

        if score >= 75:     verdict = "VERIFIED"
        elif score >= 60:   verdict = "LIKELY TRUE"
        elif score >= 40:   verdict = "UNCERTAIN"
        elif score >= 25:   verdict = "MISLEADING"
        elif score >= 10:   verdict = "LIKELY FALSE"
        else:               verdict = "UNVERIFIABLE"

        return score, verdict, breakdown

    def _build_issues(self, tone, coverage, source_scores, claims, research) -> List[Dict]:
        issues = []

        if tone["clickbait_patterns"]:
            issues.append({
                "type": "CLICKBAIT",
                "severity": "HIGH",
                "title": "Clickbait patterns detected",
                "detail": f"Found: '{tone['clickbait_patterns'][0]}'. This is a hallmark of misinformation."
            })

        if tone["severity"] == "HIGH":
            words = ", ".join(tone["high_emotion_words"][:4])
            issues.append({
                "type": "EMOTIONAL_LANGUAGE",
                "severity": "HIGH",
                "title": "Highly emotional language",
                "detail": f"Trigger words detected: {words}. Credible reporting uses neutral language."
            })
        elif tone["severity"] == "MEDIUM":
            issues.append({
                "type": "TONE_BIAS",
                "severity": "MEDIUM",
                "title": "Moderate emotional framing",
                "detail": "Some persuasive language present. Verify claims independently."
            })

        cov_score = coverage.get("coverage_score", 0)
        if cov_score < 20 and research.get("total_sources",0) > 0:
            issues.append({
                "type": "LOW_COVERAGE",
                "severity": "HIGH",
                "title": "Claims not found in external sources",
                "detail": f"Only {cov_score}% of the content matches anything found online. This may be fabricated or very niche."
            })
        elif cov_score < 40:
            issues.append({
                "type": "PARTIAL_COVERAGE",
                "severity": "MEDIUM",
                "title": "Partial source coverage",
                "detail": f"{cov_score}% of content corroborated by sources. Some claims lack independent verification."
            })

        for c in coverage.get("contradiction_signals", [])[:2]:
            issues.append({
                "type": "CONTRADICTION",
                "severity": "HIGH",
                "title": "Possible factual discrepancy",
                "detail": c
            })

        low_cred = [s for s in source_scores if s["level"] == "low"]
        if low_cred:
            issues.append({
                "type": "LOW_CRED_SOURCE",
                "severity": "MEDIUM",
                "title": "Low-credibility sources in results",
                "detail": "Some related sources have low credibility ratings. Seek peer-reviewed or established news coverage."
            })

        if not research.get("wikipedia", []):
            issues.append({
                "type": "NO_WIKI",
                "severity": "LOW",
                "title": "No Wikipedia coverage found",
                "detail": "No Wikipedia article matched this topic. Either very niche or not well-documented."
            })

        abs_claims = [c for c in claims if c["type"] == "absolute_claim"]
        if abs_claims:
            issues.append({
                "type": "ABSOLUTE_CLAIM",
                "severity": "MEDIUM",
                "title": "Absolute claims detected",
                "detail": f"'{abs_claims[0]['claim'][:100]}...' — words like 'never/always/everyone' are rarely accurate."
            })

        if len(tone["caps_words"]) > 3:
            issues.append({
                "type": "CAPS_ABUSE",
                "severity": "LOW",
                "title": f"{len(tone['caps_words'])} ALL-CAPS words",
                "detail": "Excessive capitalization is a common sensationalism tactic."
            })

        return issues
