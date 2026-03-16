"""
NLP Engine — Custom Summarizer, Paraphraser, Claim Extractor
No external AI APIs. Pure Python + scikit-learn + numpy.
"""

import re
import math
import json
import heapq
import string
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ── Stopwords (built-in, no NLTK needed) ──────────────────────────────────────
STOPWORDS = set("""
a about above after again against all also am an and any are aren't as at
be because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further get got had hadn't has hasn't have haven't having he he'd he'll
he's her here here's hers herself him himself his how how's i i'd i'll i'm
i've if in into is isn't it it's its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves out
over own same shan't she she'd she'll she's should shouldn't so some such
than that that's the their theirs them themselves then there there's these
they they'd they'll they're they've this those through to too under until up
very was wasn't we we'd we'll we're we've were weren't what what's when
when's where where's which while who who's whom why why's will with won't
would wouldn't you you'd you'll you're you've your yours yourself yourselves
said says also just like even still yet already always never often sometimes
""".split())

# ── Synonym map for paraphrasing ──────────────────────────────────────────────
SYNONYM_MAP = {
    "said": ["stated", "noted", "reported", "indicated", "declared"],
    "says": ["states", "notes", "reports", "indicates", "claims"],
    "show": ["demonstrate", "reveal", "indicate", "suggest", "establish"],
    "shows": ["demonstrates", "reveals", "indicates", "suggests", "establishes"],
    "found": ["discovered", "identified", "determined", "established", "observed"],
    "find": ["discover", "identify", "determine", "observe", "establish"],
    "think": ["believe", "consider", "suggest", "argue", "contend"],
    "thinks": ["believes", "considers", "argues", "contends"],
    "big": ["significant", "major", "substantial", "considerable", "large"],
    "small": ["minor", "limited", "modest", "minimal", "slight"],
    "good": ["positive", "beneficial", "favorable", "effective", "strong"],
    "bad": ["negative", "harmful", "unfavorable", "problematic", "concerning"],
    "many": ["numerous", "multiple", "several", "various", "a number of"],
    "few": ["limited", "several", "some", "a handful of"],
    "important": ["significant", "crucial", "key", "essential", "critical"],
    "help": ["assist", "support", "aid", "facilitate", "enable"],
    "helps": ["assists", "supports", "aids", "facilitates"],
    "use": ["utilize", "employ", "apply", "leverage"],
    "used": ["utilized", "employed", "applied"],
    "make": ["create", "produce", "generate", "develop", "form"],
    "makes": ["creates", "produces", "generates", "develops"],
    "increase": ["rise", "grow", "expand", "climb", "surge"],
    "increases": ["rises", "grows", "expands", "climbs"],
    "decrease": ["decline", "drop", "fall", "reduce", "diminish"],
    "cause": ["lead to", "result in", "trigger", "produce", "bring about"],
    "causes": ["leads to", "results in", "triggers", "produces"],
    "according": ["based on", "as per", "per", "citing"],
    "however": ["nevertheless", "yet", "that said", "even so", "still"],
    "therefore": ["thus", "consequently", "as a result", "hence", "accordingly"],
    "because": ["since", "as", "given that", "due to the fact that"],
    "although": ["even though", "while", "despite the fact that", "though"],
    "also": ["additionally", "furthermore", "moreover", "in addition"],
    "but": ["however", "yet", "though", "nonetheless", "that said"],
    "study": ["research", "investigation", "analysis", "examination", "inquiry"],
    "studies": ["research", "investigations", "analyses"],
    "data": ["evidence", "information", "findings", "results"],
    "new": ["recent", "latest", "novel", "emerging", "current"],
    "high": ["elevated", "substantial", "significant", "considerable"],
    "low": ["reduced", "limited", "minimal", "modest"],
    "problem": ["issue", "challenge", "concern", "difficulty"],
    "problems": ["issues", "challenges", "concerns", "difficulties"],
    "result": ["outcome", "finding", "conclusion", "consequence"],
    "results": ["outcomes", "findings", "conclusions"],
    "researchers": ["scientists", "investigators", "experts", "scholars"],
    "scientists": ["researchers", "experts", "investigators", "scholars"],
    "experts": ["researchers", "specialists", "authorities", "analysts"],
    "report": ["document", "study", "publication", "paper", "analysis"],
    "reports": ["documents", "studies", "publications", "papers"],
    "suggest": ["indicate", "imply", "point to", "hint at", "propose"],
    "suggests": ["indicates", "implies", "points to", "proposes"],
    "evidence": ["proof", "data", "findings", "information", "support"],
    "significant": ["substantial", "considerable", "meaningful", "notable"],
    "conducted": ["carried out", "performed", "undertaken", "executed"],
    "published": ["released", "issued", "disseminated"],
    "confirmed": ["verified", "validated", "established", "proven"],
}

# Transition phrases for paraphrasing sentence starts
TRANSITIONS = {
    "According to": ["Based on information from", "As reported by", "Per findings from", "Drawing from"],
    "The study": ["This research", "The investigation", "The analysis", "This examination"],
    "Researchers": ["Scientists", "Experts", "Investigators", "The research team"],
    "Scientists": ["Researchers", "Experts", "The scientific community", "Investigators"],
    "The report": ["This publication", "The document", "This analysis", "The findings"],
    "Studies show": ["Research indicates", "Evidence suggests", "Findings reveal", "Data demonstrates"],
    "It is": ["This is", "That represents", "This constitutes"],
    "There is": ["Evidence points to", "Data indicates", "This suggests"],
    "There are": ["Several", "Multiple factors show", "Evidence reveals"],
}


# ────────────────────────────────────────────────────────────────────────────────
class TextProcessor:
    """Sentence splitter, tokenizer, cleaner."""

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        text = re.sub(r'\s+', ' ', text.strip())
        # Handle common abbreviations to avoid splitting on them
        text = re.sub(r'\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|i\.e|e\.g|Fig|No)\.\s', r'\1@@@ ', text)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        sentences = [s.replace('@@@', '.').strip() for s in sentences if len(s.strip()) > 15]
        return sentences

    @staticmethod
    def tokenize(text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return [w for w in text.split() if w and w not in STOPWORDS and len(w) > 2]

    @staticmethod
    def word_freq(text: str) -> Counter:
        return Counter(TextProcessor.tokenize(text))

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r'\[[\d,\s]+\]', '', text)   # remove citation brackets [1][2]
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'={2,}.*?={2,}', '', text)  # remove wiki section headers
        return text.strip()


# ────────────────────────────────────────────────────────────────────────────────
class Summarizer:
    """
    Extractive summarizer using TF-IDF sentence scoring.
    Picks the most informationally dense sentences.
    """

    def __init__(self):
        self.processor = TextProcessor()

    def _score_sentences(self, sentences: List[str], full_text: str) -> List[Tuple[float, int, str]]:
        if not sentences:
            return []

        # TF-IDF over all sentences
        try:
            tfidf = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
            matrix = tfidf.fit_transform(sentences)
        except Exception:
            # fallback: word frequency scoring
            freq = self.processor.word_freq(full_text)
            scored = []
            for i, s in enumerate(sentences):
                words = self.processor.tokenize(s)
                score = sum(freq[w] for w in words) / max(len(words), 1)
                scored.append((score, i, s))
            return scored

        # Sentence score = sum of TF-IDF weights of its terms
        scores = []
        arr = matrix.toarray()
        for i, row in enumerate(arr):
            score = float(np.sum(row))
            # Bonus for sentences with numbers/statistics
            if re.search(r'\d+\.?\d*\s*(%|percent|million|billion|thousand)', sentences[i], re.I):
                score *= 1.3
            # Slight preference for earlier sentences (lead paragraph)
            position_weight = 1.0 - (i / max(len(sentences), 1)) * 0.15
            score *= position_weight
            scores.append((score, i, sentences[i]))

        return scores

    def summarize(self, text: str, num_sentences: int = 4, source_label: str = "") -> Dict:
        text = self.processor.clean_text(text)
        sentences = self.processor.split_sentences(text)

        if len(sentences) <= num_sentences:
            summary = " ".join(sentences)
            return {
                "summary": summary,
                "sentences_used": len(sentences),
                "total_sentences": len(sentences),
                "compression_ratio": 1.0,
                "source_label": source_label
            }

        scored = self._score_sentences(sentences, text)
        # Pick top N by score, but preserve original order
        top = sorted(scored, key=lambda x: x[0], reverse=True)[:num_sentences]
        top_ordered = sorted(top, key=lambda x: x[1])  # restore order

        summary = " ".join(s for _, _, s in top_ordered)
        compression = round(num_sentences / len(sentences), 2)

        return {
            "summary": summary,
            "sentences_used": num_sentences,
            "total_sentences": len(sentences),
            "compression_ratio": compression,
            "source_label": source_label
        }

    def multi_source_summary(self, sources: List[Dict]) -> str:
        """Merge + deduplicate sentences from multiple sources into one summary."""
        all_sentences = []
        all_text = ""

        for src in sources:
            text = self.processor.clean_text(src.get("text", ""))
            all_text += " " + text
            sents = self.processor.split_sentences(text)
            for s in sents:
                all_sentences.append((s, src.get("title", "Source")))

        if not all_sentences:
            return "No content available to summarize."

        # Deduplicate near-identical sentences using cosine similarity
        unique = []
        seen_texts = []
        if len(all_sentences) > 1:
            try:
                tfidf = TfidfVectorizer(stop_words='english')
                texts_only = [s for s, _ in all_sentences]
                mat = tfidf.fit_transform(texts_only)
                for i, (s, title) in enumerate(all_sentences):
                    is_dup = False
                    for j in range(max(0, i-5), i):
                        sim = cosine_similarity(mat[i], mat[j])[0][0]
                        if sim > 0.7:
                            is_dup = True
                            break
                    if not is_dup:
                        unique.append((s, title))
            except Exception:
                unique = list(dict.fromkeys(all_sentences))
        else:
            unique = all_sentences

        # Score unique sentences
        unique_texts = [s for s, _ in unique]
        scored = self._score_sentences(unique_texts, all_text)

        top_n = min(6, len(scored))
        top = sorted(scored, key=lambda x: x[0], reverse=True)[:top_n]
        top_ordered = sorted(top, key=lambda x: x[1])

        return " ".join(s for _, _, s in top_ordered)


# ────────────────────────────────────────────────────────────────────────────────
class Paraphraser:
    """
    Rule-based paraphraser using synonym replacement + sentence restructuring.
    Produces human-readable rewordings without changing meaning.
    """

    def __init__(self):
        self.processor = TextProcessor()

    def _replace_synonyms(self, text: str, intensity: float = 0.4) -> str:
        """Replace words with synonyms based on intensity (0-1)."""
        words = text.split()
        result = []
        i = 0
        used_positions = set()

        while i < len(words):
            word = words[i]
            # Strip punctuation for lookup
            clean = word.lower().strip(string.punctuation)
            suffix_punct = word[len(clean):] if word.lower().startswith(clean) else ""

            replaced = False
            if clean in SYNONYM_MAP and i not in used_positions:
                # Use deterministic replacement based on word position
                synonyms = SYNONYM_MAP[clean]
                idx = i % len(synonyms)
                if (i / max(len(words), 1)) < intensity or clean in ["said", "says", "found", "show", "shows"]:
                    replacement = synonyms[idx]
                    # Preserve capitalization
                    if word[0].isupper():
                        replacement = replacement[0].upper() + replacement[1:]
                    result.append(replacement + suffix_punct)
                    used_positions.add(i)
                    replaced = True

            if not replaced:
                result.append(word)
            i += 1

        return " ".join(result)

    def _restructure_sentence(self, sentence: str) -> str:
        """Apply transition phrase replacements."""
        for original, alternatives in TRANSITIONS.items():
            if sentence.startswith(original):
                replacement = alternatives[hash(sentence) % len(alternatives)]
                return replacement + sentence[len(original):]
        return sentence

    def paraphrase(self, text: str) -> Dict:
        """Paraphrase full text, sentence by sentence."""
        sentences = self.processor.split_sentences(text)
        paraphrased_sents = []

        for i, sent in enumerate(sentences):
            # Step 1: Replace transition phrases
            s = self._restructure_sentence(sent)
            # Step 2: Synonym replacement (higher intensity for later sentences)
            intensity = 0.35 + (i % 3) * 0.1
            s = self._replace_synonyms(s, intensity)
            paraphrased_sents.append(s)

        paraphrased = " ".join(paraphrased_sents)

        # Calculate how different the result is
        orig_words = set(text.lower().split())
        para_words = set(paraphrased.lower().split())
        overlap = len(orig_words & para_words) / max(len(orig_words), 1)
        change_pct = round((1 - overlap) * 100, 1)

        return {
            "original": text,
            "paraphrased": paraphrased,
            "words_changed_pct": change_pct,
            "sentence_count": len(sentences)
        }

    def simplify(self, text: str) -> str:
        """Produce a plain-English, simplified version of the text."""
        sentences = self.processor.split_sentences(text)
        simplified = []

        for sent in sentences[:5]:  # limit to 5 sentences for simplification
            # Remove parenthetical asides
            s = re.sub(r'\([^)]{0,80}\)', '', sent).strip()
            # Remove heavy academic phrasing
            s = re.sub(r'\b(aforementioned|hitherto|heretofore|thereof|hereby|wherein|whereby)\b', '', s, flags=re.I)
            s = re.sub(r'\b(notwithstanding|pursuant to|in accordance with)\b', 'based on', s, flags=re.I)
            s = re.sub(r'\b(utilize|utilization)\b', 'use', s, flags=re.I)
            s = re.sub(r'\b(approximately)\b', 'about', s, flags=re.I)
            s = re.sub(r'\b(demonstrate|demonstrates)\b', 'show', s, flags=re.I)
            s = re.sub(r'\b(substantial|substantially)\b', 'significant', s, flags=re.I)
            s = re.sub(r'\s+', ' ', s).strip()
            if len(s) > 15:
                simplified.append(s)

        return " ".join(simplified)


# ────────────────────────────────────────────────────────────────────────────────
class ClaimExtractor:
    """Extracts verifiable factual claims from text."""

    CLAIM_PATTERNS = [
        (r'\b(proves?|confirms?|shows?|reveals?|demonstrates?|establishes?)\s+that\b', 'factual_assertion'),
        (r'\b(is|are|was|were)\s+(the\s+)?(first|only|largest|smallest|highest|lowest|most|least)\b', 'superlative_claim'),
        (r'\b\d+(\.\d+)?\s*(%|percent)\b', 'statistical_claim'),
        (r'\b\d+\s*(million|billion|trillion|thousand)\b', 'numerical_claim'),
        (r'\b(causes?|leads?\s+to|results?\s+in|linked\s+to|associated\s+with)\b', 'causal_claim'),
        (r'\b(never|always|all|none|every|no\s+one|everyone|impossible|certain)\b', 'absolute_claim'),
        (r'\b(scientists?|researchers?|experts?|doctors?|study|studies|research)\s+(say|says|found|shows?|confirms?|reports?)\b', 'expert_claim'),
        (r'\b(increased?|decreased?|rose|fell|doubled|tripled|grew)\s+by\s+\d+', 'change_claim'),
        (r'\bin\s+(19|20)\d{2}\b', 'historical_claim'),
        (r'\b(discovered|invented|created|founded|established)\s+(in|by|at)\b', 'origin_claim'),
    ]

    def extract(self, text: str) -> List[Dict]:
        processor = TextProcessor()
        sentences = processor.split_sentences(text)
        claims = []
        seen = set()

        for sent in sentences:
            for pattern, claim_type in self.CLAIM_PATTERNS:
                if re.search(pattern, sent, re.IGNORECASE):
                    key = sent[:60].lower()
                    if key not in seen:
                        seen.add(key)
                        # Extract key entities/numbers for the claim
                        numbers = re.findall(r'\d+\.?\d*\s*(?:%|percent|million|billion)?', sent)
                        claims.append({
                            "claim": sent.strip()[:250],
                            "type": claim_type,
                            "key_numbers": numbers[:3],
                            "checkable": claim_type in ('statistical_claim', 'causal_claim', 'expert_claim', 'factual_assertion', 'numerical_claim'),
                            "priority": 1 if claim_type in ('causal_claim', 'statistical_claim', 'superlative_claim') else 2
                        })
                    break  # one type per sentence

        # Sort by priority
        claims.sort(key=lambda x: x['priority'])
        return claims[:8]


# ────────────────────────────────────────────────────────────────────────────────
class HumanReadableReport:
    """Generates plain-English fact-check reports a human can actually understand."""

    VERDICT_EXPLANATIONS = {
        "VERIFIED": "The core claims in this text are supported by credible, independent sources. Multiple reliable references confirm the key facts.",
        "LIKELY TRUE": "Most claims appear accurate based on available sources, though minor details may be unverified or context may be missing.",
        "UNCERTAIN": "Some claims could be verified, but the full picture is unclear. Independent sources partially support this, but important context is missing.",
        "MISLEADING": "While parts of this may be factually accurate, the framing, emphasis, or omissions create a false impression. The whole truth is more nuanced.",
        "LIKELY FALSE": "Key claims in this text contradict information from credible sources. This content appears to contain significant inaccuracies.",
        "UNVERIFIABLE": "The specific claims made here could not be confirmed or denied through available sources. This does not mean it is false.",
    }

    CONFIDENCE_LABELS = {
        (80, 100): "High confidence",
        (60, 80): "Moderate confidence",
        (40, 60): "Low confidence",
        (0, 40): "Very uncertain",
    }

    def get_confidence_label(self, score: int) -> str:
        for (lo, hi), label in self.CONFIDENCE_LABELS.items():
            if lo <= score <= hi:
                return label
        return "Uncertain"

    def generate_explanation(self, analysis: Dict) -> str:
        """Generate a plain-English paragraph explaining the analysis result."""
        score = analysis.get("truth_score", 50)
        verdict = analysis.get("verdict", "UNCERTAIN")
        issues = analysis.get("issues", [])
        claims_found = analysis.get("claims_count", 0)
        sources_checked = analysis.get("sources_checked", 0)
        wiki_match = analysis.get("wiki_coverage", False)

        parts = []

        # Opening verdict sentence
        base = self.VERDICT_EXPLANATIONS.get(verdict, "The analysis produced a mixed result.")
        parts.append(base)

        # What we found
        if sources_checked > 0:
            parts.append(
                f"To reach this conclusion, the system searched {sources_checked} independent source{'s' if sources_checked != 1 else ''} "
                f"and cross-referenced {claims_found} specific claim{'s' if claims_found != 1 else ''} extracted from your text."
            )
        if wiki_match:
            parts.append("Wikipedia articles on related topics were found and compared against the submitted content.")

        # Key issues
        if issues:
            issue_titles = [i["title"] if isinstance(i, dict) else i for i in issues[:2]]
            issue_text = "; ".join(issue_titles).rstrip(".")
            parts.append(f"The main concerns flagged were: {issue_text.lower()}.")

        # Confidence framing
        conf = self.get_confidence_label(score)
        parts.append(
            f"Overall, this assessment carries {conf.lower()} ({score}/100). "
            "Remember: automated fact-checking is a tool to guide further research, not a final verdict."
        )

        return " ".join(parts)

    def format_source(self, source: Dict, index: int) -> Dict:
        """Format a source into human-readable form."""
        title = source.get("title", "Unknown Source")
        url = source.get("url", "")
        snippet = source.get("snippet", "")
        source_type = source.get("type", "web")

        credibility_note = ""
        domain = url.split("/")[2] if url.count("/") >= 2 else url
        domain = domain.replace("www.", "")

        HIGH_CRED = ["wikipedia.org", "reuters.com", "bbc.com", "bbc.co.uk", "apnews.com",
                     "nature.com", "science.org", "nih.gov", "cdc.gov", "who.int",
                     "nytimes.com", "washingtonpost.com", "theguardian.com", "economist.com",
                     "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "gov", "edu"]
        LOW_CRED = ["blogspot", "wordpress.com", "medium.com", "substack.com", "tumblr.com"]

        if any(h in domain for h in HIGH_CRED):
            credibility_note = "High credibility source"
            cred_level = "high"
        elif any(l in domain for l in LOW_CRED):
            credibility_note = "Blog / opinion platform"
            cred_level = "low"
        else:
            credibility_note = "Independent source"
            cred_level = "medium"

        return {
            "index": index + 1,
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": snippet[:300] if snippet else "",
            "credibility_note": credibility_note,
            "cred_level": cred_level,
            "type": source_type
        }
