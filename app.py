"""
Real-World Fact Checker — Streamlit Frontend (Redesigned)
Run: streamlit run app.py
Requires backend running: uvicorn main:app --reload --port 8000
"""

import streamlit as st
import requests
import json
import time
import re
from typing import Optional

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactCheck AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme init ─────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

IS_DARK = st.session_state.theme == "dark"

# ── Consolidated theme tokens ──────────────────────────────────────────────────
if IS_DARK:
    T = {
        # backgrounds
        "bg":            "#0b0d12",
        "surface":       "#111318",
        "surface2":      "#161a22",
        "surface3":      "#1c2130",
        "border":        "#252d3d",
        "border2":       "#1e2637",
        # text
        "text":          "#e8edf5",
        "text2":         "#8b96ab",
        "text3":         "#4d5a72",
        "text4":         "#2e3a50",
        # accents
        "cyan":          "#38bdf8",
        "cyan_dim":      "#0c3d5e",
        "purple":        "#a78bfa",
        "purple_dim":    "#2d1f6e",
        "green":         "#34d399",
        "green_dim":     "#0d3d2c",
        "amber":         "#fbbf24",
        "amber_dim":     "#3d2c0a",
        "red":           "#f87171",
        "red_dim":       "#3d1515",
        "blue":          "#60a5fa",
        "blue_dim":      "#112244",
        # gradients
        "grad":          "linear-gradient(135deg, #0b0d12 0%, #0d1019 50%, #0b0f16 100%)",
        "grad_card":     "linear-gradient(145deg, rgba(28,33,48,.9), rgba(17,19,24,.95))",
        "grad_accent":   "linear-gradient(90deg, #38bdf8, #a78bfa)",
        "scrollbar":     "#252d3d",
        "scrollbar_h":   "#38bdf8",
        "theme_icon":    "☀️",
        "theme_label":   "Light mode",
    }
    VERDICT_COLORS = {
        "VERIFIED":     {"score":"#34d399","bg":"rgba(52,211,153,.07)","border":"rgba(52,211,153,.22)","pill":"rgba(52,211,153,.12)","text":"#34d399"},
        "LIKELY TRUE":  {"score":"#6ee7b7","bg":"rgba(110,231,183,.07)","border":"rgba(110,231,183,.22)","pill":"rgba(110,231,183,.12)","text":"#6ee7b7"},
        "UNCERTAIN":    {"score":"#fbbf24","bg":"rgba(251,191,36,.07)","border":"rgba(251,191,36,.22)","pill":"rgba(251,191,36,.12)","text":"#fbbf24"},
        "MISLEADING":   {"score":"#fb923c","bg":"rgba(251,146,60,.07)","border":"rgba(251,146,60,.22)","pill":"rgba(251,146,60,.12)","text":"#fb923c"},
        "LIKELY FALSE": {"score":"#f87171","bg":"rgba(248,113,113,.07)","border":"rgba(248,113,113,.22)","pill":"rgba(248,113,113,.12)","text":"#f87171"},
        "UNVERIFIABLE": {"score":"#94a3b8","bg":"rgba(148,163,184,.07)","border":"rgba(148,163,184,.22)","pill":"rgba(148,163,184,.12)","text":"#94a3b8"},
    }
    SEV_COLORS = {
        "HIGH":   {"bar":"#f87171","bg":"rgba(248,113,113,.06)","border":"rgba(248,113,113,.18)","text":"#f87171"},
        "MEDIUM": {"bar":"#fbbf24","bg":"rgba(251,191,36,.06)","border":"rgba(251,191,36,.18)","text":"#fbbf24"},
        "LOW":    {"bar":"#60a5fa","bg":"rgba(96,165,250,.06)","border":"rgba(96,165,250,.18)","text":"#60a5fa"},
    }
else:
    T = {
        "bg":            "#f4f6fb",
        "surface":       "#ffffff",
        "surface2":      "#f8faff",
        "surface3":      "#eef2ff",
        "border":        "#dde3f0",
        "border2":       "#e8edf8",
        "text":          "#0f172a",
        "text2":         "#475569",
        "text3":         "#94a3b8",
        "text4":         "#cbd5e1",
        "cyan":          "#0284c7",
        "cyan_dim":      "#e0f2fe",
        "purple":        "#7c3aed",
        "purple_dim":    "#ede9fe",
        "green":         "#059669",
        "green_dim":     "#d1fae5",
        "amber":         "#d97706",
        "amber_dim":     "#fef3c7",
        "red":           "#dc2626",
        "red_dim":       "#fee2e2",
        "blue":          "#2563eb",
        "blue_dim":      "#dbeafe",
        "grad":          "linear-gradient(135deg, #eef2ff 0%, #f8faff 50%, #f0f4ff 100%)",
        "grad_card":     "linear-gradient(145deg, rgba(255,255,255,.97), rgba(248,250,255,.99))",
        "grad_accent":   "linear-gradient(90deg, #0284c7, #7c3aed)",
        "scrollbar":     "#dde3f0",
        "scrollbar_h":   "#0284c7",
        "theme_icon":    "🌙",
        "theme_label":   "Dark mode",
    }
    VERDICT_COLORS = {
        "VERIFIED":     {"score":"#059669","bg":"rgba(5,150,105,.06)","border":"rgba(5,150,105,.28)","pill":"rgba(5,150,105,.1)","text":"#059669"},
        "LIKELY TRUE":  {"score":"#10b981","bg":"rgba(16,185,129,.06)","border":"rgba(16,185,129,.28)","pill":"rgba(16,185,129,.1)","text":"#10b981"},
        "UNCERTAIN":    {"score":"#d97706","bg":"rgba(217,119,6,.06)","border":"rgba(217,119,6,.28)","pill":"rgba(217,119,6,.1)","text":"#d97706"},
        "MISLEADING":   {"score":"#ea580c","bg":"rgba(234,88,12,.06)","border":"rgba(234,88,12,.28)","pill":"rgba(234,88,12,.1)","text":"#ea580c"},
        "LIKELY FALSE": {"score":"#dc2626","bg":"rgba(220,38,38,.06)","border":"rgba(220,38,38,.28)","pill":"rgba(220,38,38,.1)","text":"#dc2626"},
        "UNVERIFIABLE": {"score":"#64748b","bg":"rgba(100,116,139,.06)","border":"rgba(100,116,139,.28)","pill":"rgba(100,116,139,.1)","text":"#64748b"},
    }
    SEV_COLORS = {
        "HIGH":   {"bar":"#dc2626","bg":"rgba(220,38,38,.05)","border":"rgba(220,38,38,.2)","text":"#dc2626"},
        "MEDIUM": {"bar":"#d97706","bg":"rgba(217,119,6,.05)","border":"rgba(217,119,6,.2)","text":"#d97706"},
        "LOW":    {"bar":"#2563eb","bg":"rgba(37,99,235,.05)","border":"rgba(37,99,235,.2)","text":"#2563eb"},
    }

CLAIM_COLORS = {
    "statistical_claim":  T["cyan"],
    "causal_claim":       T["red"],
    "expert_claim":       T["green"],
    "superlative_claim":  T["amber"],
    "absolute_claim":     T["red"],
    "historical_claim":   T["purple"],
    "origin_claim":       T["purple"],
    "numerical_claim":    T["green"],
    "factual_assertion":  T["blue"],
}

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

/* ── Reset & base ─────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [class*="css"] {{
    font-family: 'DM Sans', -apple-system, sans-serif !important;
}}

code, pre, .mono {{
    font-family: 'Space Mono', Consolas, monospace !important;
}}

.stApp {{
    background: {T["grad"]};
    min-height: 100vh;
}}

#MainMenu, footer, header {{ visibility: hidden; }}

.block-container {{
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1280px !important;
}}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {T["scrollbar"]}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {T["scrollbar_h"]}; }}

/* ── Header ───────────────────────────────────────────────── */
.fc-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 2rem 2.5rem;
    background: {T["surface"]};
    border: 1px solid {T["border"]};
    border-radius: 20px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}}
.fc-header::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: {T["grad_accent"]};
}}
.fc-logo {{
    display: flex;
    align-items: center;
    gap: 14px;
}}
.fc-logo-icon {{
    width: 44px; height: 44px;
    border-radius: 12px;
    background: {T["grad_accent"]};
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    flex-shrink: 0;
}}
.fc-title {{
    font-size: clamp(1.4rem, 3vw, 1.9rem);
    font-weight: 700;
    color: {T["text"]};
    letter-spacing: -0.03em;
    margin: 0;
    line-height: 1;
}}
.fc-title span {{
    background: {T["grad_accent"]};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.fc-sub {{
    font-size: 0.73rem;
    color: {T["text3"]};
    letter-spacing: 0.02em;
    margin-top: 4px;
    font-family: 'Space Mono', monospace;
}}
.fc-pills {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 10px;
}}
.pill {{
    font-size: 0.65rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.04em;
    border: 1px solid;
}}
.pill-cyan   {{ color:{T["cyan"]}; background:{T["cyan_dim"]}; border-color:{T["cyan"]}33; }}
.pill-purple {{ color:{T["purple"]}; background:{T["purple_dim"]}; border-color:{T["purple"]}33; }}
.pill-green  {{ color:{T["green"]}; background:{T["green_dim"]}; border-color:{T["green"]}33; }}
.pill-amber  {{ color:{T["amber"]}; background:{T["amber_dim"]}; border-color:{T["amber"]}33; }}

/* ── Verdict card ─────────────────────────────────────────── */
.verdict-wrap {{
    border-radius: 16px;
    padding: 2rem 2.5rem;
    border: 1px solid;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}}
.verdict-wrap::after {{
    content: '';
    position: absolute; top: 0; right: 0;
    width: 200px; height: 200px;
    border-radius: 50%;
    opacity: 0.04;
    background: currentColor;
    transform: translate(40%, -40%);
    pointer-events: none;
}}
.verdict-grid {{
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2rem;
    align-items: center;
}}
.verdict-score-block {{
    text-align: center;
    min-width: 110px;
}}
.verdict-num {{
    font-family: 'Space Mono', monospace;
    font-size: clamp(3.5rem, 7vw, 5rem);
    font-weight: 700;
    line-height: 1;
    letter-spacing: -4px;
}}
.verdict-label {{
    font-size: 0.6rem;
    letter-spacing: 0.18em;
    color: {T["text3"]};
    text-transform: uppercase;
    margin-top: 2px;
    font-weight: 600;
}}
.verdict-badge {{
    display: inline-block;
    margin-top: 8px;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    border: 1px solid;
}}
.verdict-conf {{
    font-size: 0.65rem;
    color: {T["text3"]};
    letter-spacing: 0.06em;
    font-family: 'Space Mono', monospace;
    margin-bottom: 10px;
    text-transform: uppercase;
}}
.verdict-expl {{
    font-size: 0.83rem;
    line-height: 1.75;
    color: {T["text2"]};
    padding-left: 14px;
    border-left: 3px solid;
    margin-bottom: 14px;
}}
.verdict-bar-track {{
    height: 5px;
    border-radius: 3px;
    background: {T["border"]};
    overflow: hidden;
}}
.verdict-bar-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.8s cubic-bezier(.4,0,.2,1);
}}

/* ── Metric cards ─────────────────────────────────────────── */
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 1.5rem;
}}
@media (max-width: 900px) {{
    .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .verdict-grid {{ grid-template-columns: 1fr; gap: 1rem; }}
}}
@media (max-width: 540px) {{
    .metrics-grid {{ grid-template-columns: 1fr; }}
}}
.metric-card {{
    background: {T["surface"]};
    border: 1px solid {T["border"]};
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    display: flex;
    flex-direction: column;
    gap: 2px;
    transition: border-color .2s, transform .2s;
}}
.metric-card:hover {{ border-color: {T["cyan"]}55; transform: translateY(-1px); }}
.metric-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}}
.metric-icon {{
    font-size: 1rem;
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 8px;
    background: {T["surface2"]};
    border: 1px solid {T["border"]};
}}
.metric-val {{
    font-family: 'Space Mono', monospace;
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1;
}}
.metric-name {{
    font-size: 0.7rem;
    font-weight: 600;
    color: {T["text3"]};
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.metric-note {{
    font-size: 0.65rem;
    color: {T["text3"]};
    margin-top: 2px;
    font-family: 'Space Mono', monospace;
}}

/* ── Section containers ───────────────────────────────────── */
.fc-card {{
    background: {T["surface"]};
    border: 1px solid {T["border"]};
    border-radius: 16px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1rem;
    height: 100%;
}}
.section-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 1.25rem;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid {T["border2"]};
}}
.section-icon {{
    width: 28px; height: 28px;
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem;
    flex-shrink: 0;
}}
.section-title {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T["text"]};
}}
.section-count {{
    margin-left: auto;
    font-size: 0.62rem;
    font-family: 'Space Mono', monospace;
    color: {T["text3"]};
    background: {T["surface2"]};
    border: 1px solid {T["border"]};
    padding: 2px 8px;
    border-radius: 10px;
}}

/* ── Issue items ──────────────────────────────────────────── */
.issue-card {{
    display: flex;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 10px;
    margin-bottom: 8px;
    border: 1px solid;
    transition: transform .15s;
}}
.issue-card:hover {{ transform: translateX(2px); }}
.issue-stripe {{
    width: 3px;
    border-radius: 2px;
    flex-shrink: 0;
    align-self: stretch;
}}
.issue-title {{
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 3px;
}}
.issue-detail {{
    font-size: 0.7rem;
    line-height: 1.6;
    color: {T["text2"]};
}}
.issue-foot {{
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 5px;
}}
.issue-type {{
    font-size: 0.58rem;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.06em;
    padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid;
    opacity: 0.7;
}}

/* ── Claim items ──────────────────────────────────────────── */
.claim-card {{
    padding: 11px 14px;
    border-radius: 10px;
    border: 1px solid {T["border"]};
    border-left: 3px solid;
    margin-bottom: 8px;
    background: {T["surface2"]};
    transition: border-color .15s;
}}
.claim-card:hover {{ border-color: {T["border"]}; }}
.claim-type {{
    font-size: 0.58rem;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 5px;
    font-weight: 700;
}}
.claim-text {{
    font-size: 0.75rem;
    line-height: 1.65;
    color: {T["text2"]};
}}
.claim-nums {{
    font-size: 0.6rem;
    font-family: 'Space Mono', monospace;
    color: {T["text3"]};
    margin-top: 5px;
}}
.checkable-badge {{
    display: inline-block;
    margin-top: 5px;
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    padding: 2px 8px;
    border-radius: 10px;
    background: {T["amber_dim"]};
    color: {T["amber"]};
    border: 1px solid {T["amber"]}33;
}}

/* ── Text panels ──────────────────────────────────────────── */
.text-panel {{
    background: {T["surface2"]};
    border: 1px solid {T["border2"]};
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-size: 0.78rem;
    line-height: 1.85;
    color: {T["text2"]};
}}
.text-panel-label {{
    font-size: 0.58rem;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T["text3"]};
    margin-bottom: 8px;
    display: block;
}}

/* ── Coverage bars ────────────────────────────────────────── */
.cov-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}}
.cov-label {{
    font-size: 0.68rem;
    color: {T["text2"]};
    width: 150px;
    flex-shrink: 0;
    font-weight: 500;
}}
.cov-track {{
    flex: 1;
    height: 6px;
    background: {T["border"]};
    border-radius: 3px;
    overflow: hidden;
}}
.cov-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width .6s cubic-bezier(.4,0,.2,1);
}}
.cov-val {{
    font-size: 0.62rem;
    font-family: 'Space Mono', monospace;
    color: {T["text3"]};
    width: 36px;
    text-align: right;
}}

/* ── Keywords ─────────────────────────────────────────────── */
.kw-wrap {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 1.25rem;
}}
.kw-tag {{
    font-size: 0.68rem;
    padding: 4px 11px;
    border-radius: 6px;
    background: {T["cyan_dim"]};
    color: {T["cyan"]};
    border: 1px solid {T["cyan"]}33;
    font-weight: 500;
}}
.kw-query {{
    font-family: 'Space Mono', monospace;
    font-size: 0.63rem;
    padding: 4px 11px;
    border-radius: 6px;
    border: 1px dashed {T["border"]};
    color: {T["text3"]};
}}

/* ── Sources ──────────────────────────────────────────────── */
.source-card {{
    background: {T["surface2"]};
    border: 1px solid {T["border2"]};
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color .2s, transform .15s;
}}
.source-card:hover {{
    border-color: {T["cyan"]}44;
    transform: translateX(2px);
}}
.source-head {{
    display: flex;
    gap: 12px;
    align-items: flex-start;
}}
.source-idx {{
    font-family: 'Space Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: {T["border"]};
    line-height: 1;
    flex-shrink: 0;
    padding-top: 2px;
}}
.source-title {{
    font-size: 0.8rem;
    font-weight: 600;
    color: {T["cyan"]};
    margin-bottom: 3px;
    line-height: 1.4;
}}
.source-meta {{
    font-size: 0.63rem;
    font-family: 'Space Mono', monospace;
    color: {T["text3"]};
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}}
.source-snippet {{
    font-size: 0.72rem;
    line-height: 1.65;
    color: {T["text2"]};
}}
.source-cred {{
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 10px;
    border: 1px solid;
    margin-top: 8px;
}}

/* ── Empty state ──────────────────────────────────────────── */
.empty-state {{
    text-align: center;
    padding: 3rem 2rem;
    color: {T["text3"]};
}}
.empty-icon {{
    font-size: 2.5rem;
    margin-bottom: 10px;
    opacity: .4;
}}
.empty-text {{
    font-size: 0.75rem;
    opacity: .7;
}}
.empty-hint {{
    font-size: 0.65rem;
    font-family: 'Space Mono', monospace;
    margin-top: 6px;
    color: {T["cyan"]};
    opacity: .5;
}}

/* ── Tone table ───────────────────────────────────────────── */
.tone-row {{
    display: flex;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid {T["border2"]};
    font-size: 0.72rem;
    align-items: flex-start;
}}
.tone-row:last-child {{ border-bottom: none; }}
.tone-key {{
    width: 160px;
    flex-shrink: 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {T["text3"]};
    padding-top: 1px;
}}
.tone-val {{ flex: 1; color: {T["text2"]}; line-height: 1.5; }}

/* ── Steps progress ───────────────────────────────────────── */
.steps-wrap {{
    display: flex;
    gap: 0;
    margin-bottom: 10px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid {T["border"]};
}}
.step-item {{
    flex: 1;
    text-align: center;
    padding: 8px 4px;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: {T["surface2"]};
    color: {T["text3"]};
    border-right: 1px solid {T["border"]};
    transition: all .2s;
    font-family: 'Space Mono', monospace;
}}
.step-item:last-child {{ border-right: none; }}
.step-item.active {{
    background: {T["cyan_dim"]};
    color: {T["cyan"]};
}}
.step-item.done {{
    background: {T["green_dim"]};
    color: {T["green"]};
}}
.step-msg {{
    text-align: center;
    font-size: 0.72rem;
    color: {T["text2"]};
    margin-top: 8px;
    font-family: 'Space Mono', monospace;
}}

/* ── Divider ──────────────────────────────────────────────── */
.fc-divider {{
    height: 1px;
    background: {T["border2"]};
    margin: 1.5rem 0;
}}

/* ── Input overrides ──────────────────────────────────────── */
.stTextArea textarea {{
    background: {T["surface"]} !important;
    border: 1.5px solid {T["border"]} !important;
    border-radius: 12px !important;
    color: {T["text"]} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    line-height: 1.7 !important;
    caret-color: {T["cyan"]} !important;
    transition: border-color .2s !important;
    resize: none !important;
}}
.stTextArea textarea:focus {{
    border-color: {T["cyan"]} !important;
    box-shadow: 0 0 0 3px {T["cyan"]}18 !important;
    outline: none !important;
}}
.stTextArea textarea::placeholder {{
    color: {T["text3"]} !important;
    font-style: italic;
}}

.stTextInput input {{
    background: {T["surface"]} !important;
    border: 1.5px solid {T["border"]} !important;
    border-radius: 8px !important;
    color: {T["text"]} !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
}}
.stTextInput input:focus {{
    border-color: {T["cyan"]} !important;
    box-shadow: 0 0 0 3px {T["cyan"]}15 !important;
}}

/* ── Primary button ───────────────────────────────────────── */
.stButton > button {{
    background: {T["grad_accent"]} !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.6rem 1.5rem !important;
    width: 100% !important;
    transition: opacity .2s, transform .15s, box-shadow .2s !important;
    box-shadow: 0 2px 12px {T["cyan"]}33 !important;
}}
.stButton > button:hover {{
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px {T["cyan"]}44 !important;
}}
.stButton > button:active {{ transform: scale(0.98) !important; }}

.btn-ghost > button {{
    background: transparent !important;
    border: 1.5px solid {T["border"]} !important;
    color: {T["text2"]} !important;
    box-shadow: none !important;
}}
.btn-ghost > button:hover {{
    border-color: {T["red"]}55 !important;
    color: {T["red"]} !important;
    background: {T["red_dim"]} !important;
    box-shadow: none !important;
}}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background: {T["surface2"]} !important;
    border-radius: 10px !important;
    padding: 3px !important;
    gap: 2px !important;
    border: 1px solid {T["border"]} !important;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: {T["text3"]} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.73rem !important;
    font-weight: 500 !important;
    border-radius: 7px !important;
    padding: 7px 14px !important;
    transition: all .15s !important;
}}
.stTabs [aria-selected="true"] {{
    background: {T["surface"]} !important;
    color: {T["text"]} !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.08) !important;
}}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 1rem !important; }}

/* ── Progress ─────────────────────────────────────────────── */
.stProgress > div > div > div {{
    background: {T["grad_accent"]} !important;
    border-radius: 4px !important;
}}

/* ── Expander ─────────────────────────────────────────────── */
.streamlit-expanderHeader {{
    background: {T["surface2"]} !important;
    border: 1px solid {T["border"]} !important;
    border-radius: 10px !important;
    color: {T["text2"]} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
}}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: {T["surface"]} !important;
    border-right: 1px solid {T["border"]} !important;
}}

/* ── Sidebar buttons ──────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {{
    background: {T["surface2"]} !important;
    color: {T["text2"]} !important;
    border: 1px solid {T["border"]} !important;
    box-shadow: none !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    justify-content: flex-start !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: {T["cyan_dim"]} !important;
    border-color: {T["cyan"]}44 !important;
    color: {T["cyan"]} !important;
    transform: none !important;
    box-shadow: none !important;
}}

/* ── Sidebar status dot ───────────────────────────────────── */
.status-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: {T["surface2"]};
    border: 1px solid {T["border"]};
    border-radius: 10px;
    margin-bottom: 1rem;
}}
.status-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}}
.status-label {{ font-size: .72rem; font-weight: 600; }}
.status-sub {{
    font-size: .62rem;
    color: {T["text3"]};
    font-family: 'Space Mono', monospace;
}}

/* ── Sidebar section labels ───────────────────────────────── */
.sb-label {{
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T["text3"]};
    margin-bottom: 8px;
    margin-top: 1rem;
    display: block;
}}

/* ── How it works ─────────────────────────────────────────── */
.how-step {{
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
    align-items: flex-start;
}}
.how-num {{
    width: 20px; height: 20px;
    border-radius: 6px;
    background: {T["grad_accent"]};
    display: flex; align-items: center; justify-content: center;
    font-size: 0.6rem;
    font-weight: 700;
    color: #fff;
    flex-shrink: 0;
}}
.how-text {{ font-size: 0.7rem; color: {T["text2"]}; line-height: 1.5; }}

/* ── Word count hint ──────────────────────────────────────── */
.word-hint {{
    font-size: 0.63rem;
    font-family: 'Space Mono', monospace;
    color: {T["text3"]};
    margin-top: 5px;
}}

/* ── JSON block ───────────────────────────────────────────── */
.json-block {{
    background: {T["surface2"]};
    border: 1px solid {T["border"]};
    border-radius: 10px;
    padding: 1rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.63rem;
    color: {T["text2"]};
    white-space: pre-wrap;
    overflow-x: auto;
    max-height: 420px;
    overflow-y: auto;
    line-height: 1.6;
}}

/* ── Theme toggle button ──────────────────────────────────── */
.toggle-btn > button {{
    background: {T["surface2"]} !important;
    border: 1px solid {T["border"]} !important;
    color: {T["text2"]} !important;
    box-shadow: none !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    border-radius: 20px !important;
    width: auto !important;
}}
.toggle-btn > button:hover {{
    border-color: {T["cyan"]}55 !important;
    color: {T["cyan"]} !important;
    background: {T["cyan_dim"]} !important;
    transform: none !important;
    box-shadow: none !important;
}}

/* ── Responsive ───────────────────────────────────────────── */
@media (max-width: 768px) {{
    .block-container {{ padding: 1rem 0.75rem !important; }}
    .fc-header {{ padding: 1.25rem 1.25rem; flex-wrap: wrap; gap: 10px; }}
    .verdict-grid {{ grid-template-columns: 1fr; gap: 1rem; }}
    .fc-card {{ padding: 1.1rem 1.1rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"

SAMPLES = {
    "🌍 Climate Science":    "Scientists have confirmed that global temperatures have risen by approximately 1.1 degrees Celsius since the pre-industrial era, primarily due to greenhouse gas emissions from human activities. According to NASA and NOAA data, the last decade was the warmest on record. The IPCC report warns that without significant emissions reductions, temperatures could rise by 3 to 4 degrees by 2100, causing widespread flooding, droughts, and ecosystem collapse across multiple continents.",
    "📡 5G Conspiracy":      "SHOCKING: 5G towers are DESTROYING human DNA and causing cancer in millions! The government is HIDING this from you! My cousin who works at a hospital told me doctors are seeing massive increases in brain tumors near 5G towers. Wake up people! Share this before they delete it! Big Pharma doesn't want you to know the TRUTH about what they're putting in these towers! One weird trick doctors hate can protect you!",
    "💉 Health Claim":       "A new study published in the New England Journal of Medicine found that intermittent fasting reduces the risk of type 2 diabetes by 30 percent in adults with prediabetes. The randomized controlled trial followed 2,000 participants over 18 months and found that those who fasted 16 hours daily showed significantly improved insulin sensitivity and blood sugar control compared to control groups.",
    "🚀 Apollo Moon Landing":"The Apollo 11 mission successfully landed astronauts Neil Armstrong and Buzz Aldrin on the Moon on July 20, 1969. Armstrong became the first human to walk on the lunar surface. The mission was the culmination of the Space Race between the United States and the Soviet Union, and approximately 600 million people worldwide watched the event live on television.",
    "💊 Miracle Cure":       "DOCTORS HATE THIS! A simple kitchen spice cures cancer better than chemotherapy with zero side effects! Big Pharma has suppressed this information for decades because it would destroy their trillion-dollar industry. Thousands of people have already been cured using this one natural remedy. Share this before it gets censored! The establishment doesn't want you healthy!",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def score_color(s: float) -> str:
    s = int(s)
    if IS_DARK:
        if s >= 75: return "#34d399"
        if s >= 60: return "#6ee7b7"
        if s >= 45: return "#fbbf24"
        if s >= 30: return "#fb923c"
        return "#f87171"
    else:
        if s >= 75: return "#059669"
        if s >= 60: return "#10b981"
        if s >= 45: return "#d97706"
        if s >= 30: return "#ea580c"
        return "#dc2626"

def call_backend(text: str, custom_query: str = "") -> Optional[dict]:
    try:
        payload = {"text": text}
        if custom_query:
            payload["custom_query"] = custom_query
        r = requests.post(f"{BACKEND_URL}/analyze", json=payload, timeout=35)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        st.error(f"Backend error: {e}")
        return None

def local_analyze(text: str) -> dict:
    words = text.split()
    tl = text.lower()
    sents = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 25]
    HIGH_W = ['shocking','outrageous','hoax','conspiracy','cover-up','exposed','wake up','destroy','truth','liar','fake','rigged','criminal','evil','hidden','bombshell','unbelievable','insane']
    CRED_W = ['study','research','published','journal','according','data','evidence','peer','university','confirmed','trial','participants','scientists','researchers','statistics','findings']
    CLICK  = ["you won't believe","wake up people","share before","they don't want","one weird trick","mainstream media hiding","doctors hate","big pharma","suppressed","censored"]
    hw = [w for w in HIGH_W if w in tl]
    cw = [w for w in CRED_W if w in tl]
    cb = [p for p in CLICK if p in tl]
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 2 and w.isalpha()]
    exclaims = text.count('!')
    emo = min(10.0, ((len(hw)*3) / max(len(words), 1))*100)
    sev = "HIGH" if emo > 3.5 else "MEDIUM" if emo > 1.5 else "LOW"
    score = 50
    score += len(cw)*4 - len(hw)*6 - len(cb)*12 - len(caps_words)*3 - exclaims*3
    score = max(2, min(82, round(score)))
    verdict = ("VERIFIED" if score>=75 else "LIKELY TRUE" if score>=62 else "UNCERTAIN" if score>=45 else "MISLEADING" if score>=30 else "LIKELY FALSE" if score>=15 else "UNVERIFIABLE")
    summary = ". ".join(sents[:2]) + ("." if sents else "")
    keywords = list(dict.fromkeys(re.findall(r'\b[A-Z][a-z]{3,}\b', text)))[:6]
    SYNS = {"said":"stated","says":"reports","found":"discovered","show":"demonstrate","researchers":"scientists","experts":"analysts","study":"investigation","data":"evidence","confirmed":"verified","according":"based on","however":"nevertheless","also":"additionally","important":"significant"}
    para = summary
    for k, v in SYNS.items():
        para = re.sub(rf'\b{k}\b', lambda m, vv=v: vv[0].upper()+vv[1:] if m.group()[0].isupper() else vv, para)
    issues = []
    if cb:          issues.append({"type":"CLICKBAIT","severity":"HIGH","title":"Clickbait language detected","detail":f'Found: "{cb[0]}". Hallmark of misinformation content.'})
    if sev=="HIGH": issues.append({"type":"EMOTIONAL_LANGUAGE","severity":"HIGH","title":"Highly emotional language","detail":f"Trigger words detected: {', '.join(hw[:4])}. Credible sources use neutral language."})
    elif sev=="MEDIUM": issues.append({"type":"TONE_BIAS","severity":"MEDIUM","title":"Moderate emotional framing","detail":"Some persuasive language found. Verify claims independently."})
    if caps_words:  issues.append({"type":"CAPS_ABUSE","severity":"LOW","title":f"{len(caps_words)} ALL-CAPS word(s)","detail":"Excessive capitalization is a common sensationalism tactic."})
    if not cw:      issues.append({"type":"NO_CITATIONS","severity":"MEDIUM","title":"No citation indicators","detail":"No mentions of studies, journals, or named sources found."})
    issues.append({"type":"OFFLINE_MODE","severity":"LOW","title":"Backend offline — no live web research","detail":"Run: uvicorn main:app --reload --port 8000 for Wikipedia + news cross-referencing."})
    CTYPE = [(r'\b\d+\.?\d*\s*(%|percent)\b','statistical_claim'),(r'\b(never|always|all|none|every)\b','absolute_claim'),(r'\b(causes?|leads? to|linked to)\b','causal_claim'),(r'\b(scientists?|researchers?|experts?) (say|found|show)','expert_claim'),(r'\b(first|only|largest|highest|most)\b','superlative_claim')]
    claims = []
    for s in sents:
        for pat, ctype in CTYPE:
            if re.search(pat, s, re.I) and len(claims)<6:
                claims.append({"claim":s[:220],"type":ctype,"key_numbers":re.findall(r'\d+\.?\d*',s)[:3],"checkable":True}); break
    return {
        "truth_score": score, "verdict": verdict,
        "confidence_label": "Moderate" if score > 65 else "Low" if score > 40 else "Very low",
        "human_explanation": (f"⚡ Offline mode — no live research. {'Content shows hallmarks of misinformation: clickbait, emotional language, no citations.' if score<35 else 'Content uses evidence-based language with neutral tone.' if score>65 else 'Mixed signals detected. Some claims may be accurate but independent verification is recommended.'} Confidence: {score}/100."),
        "issues": issues,
        "score_breakdown": {"evidence_coverage":0,"source_credibility":0,"tone_penalty":emo,"research_depth_bonus":0},
        "input_analysis": {
            "word_count": len(words), "sentence_count": len(sents),
            "summary": summary, "simplified": ". ".join(sents[:3]),
            "paraphrased": para, "words_changed_pct": 9.2,
            "tone": {"emotional_score": round(emo,1),"severity":sev,"high_emotion_words":hw[:5],"neutral_indicators":cw[:4],"caps_words":caps_words[:5],"exclamation_count":exclaims,"clickbait_patterns":cb[:2],"tone_summary":"Clickbait content." if cb else "Emotional." if sev=="HIGH" else "Mostly neutral." if cw else "Mixed."}
        },
        "claims": claims,
        "research": {"query_used":" ".join(keywords[:4]),"keywords":keywords,"total_sources":0,"wikipedia_found":0,"news_found":0,"combined_summary":"","coverage":{"coverage_score":0,"matched_count":0}},
        "sources": [], "source_credibility": {"average_score":0}, "processing_time_ms": 280,
    }

# ── Render functions ───────────────────────────────────────────────────────────

def render_header():
    col_l, col_r = st.columns([4, 1])
    with col_l:
        st.markdown(f"""
        <div class="fc-header">
            <div class="fc-logo">
                <div class="fc-logo-icon">🔍</div>
                <div>
                    <div class="fc-title">Fact<span>Check</span> AI</div>
                    <div class="fc-sub">// Real-world misinformation detector</div>
                    <div class="fc-pills">
                        <span class="pill pill-cyan">No AI API</span>
                        <span class="pill pill-purple">Custom NLP</span>
                        <span class="pill pill-green">Web Research</span>
                        <span class="pill pill-amber">Claim Extractor</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_r:
        st.markdown("<div style='padding-top:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="toggle-btn">', unsafe_allow_html=True)
        if st.button(f"{T['theme_icon']} {T['theme_label']}", key="theme_btn"):
            st.session_state.theme = "light" if IS_DARK else "dark"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_verdict(data: dict):
    score = data["truth_score"]
    verdict = data["verdict"]
    vc = VERDICT_COLORS.get(verdict, VERDICT_COLORS["UNVERIFIABLE"])
    sc = vc["score"]
    conf = data.get("confidence_label", "—").upper()
    ms = data.get("processing_time_ms", "—")
    nsrc = data.get("research", {}).get("total_sources", 0)

    st.markdown(f"""
    <div class="verdict-wrap" style="background:{vc['bg']};border-color:{vc['border']}">
        <div class="verdict-grid">
            <div class="verdict-score-block">
                <div class="verdict-num" style="color:{sc}">{score}</div>
                <div class="verdict-label">Truth Score</div>
                <div class="verdict-badge" style="background:{vc['pill']};color:{vc['text']};border-color:{vc['border']}">{verdict}</div>
            </div>
            <div>
                <div class="verdict-conf">{conf} confidence &nbsp;·&nbsp; {ms}ms &nbsp;·&nbsp; {nsrc} sources</div>
                <div class="verdict-expl" style="border-left-color:{sc}">{data.get('human_explanation','')}</div>
                <div class="verdict-bar-track">
                    <div class="verdict-bar-fill" style="width:{score}%;background:{sc}"></div>
                </div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


def render_metrics(data: dict):
    ia = data.get("input_analysis", {})
    tone = ia.get("tone", {})
    cov = data.get("research", {}).get("coverage", {})
    cred = data.get("source_credibility", {})
    sev = tone.get("severity", "LOW")

    metrics = [
        ("📊", f"{int(cov.get('coverage_score', 0))}%", score_color(cov.get('coverage_score', 0)), "Evidence Coverage", f"{cov.get('matched_count', 0)} sentences matched"),
        ("🔗", f"{int(cred.get('average_score', 0))}", score_color(cred.get('average_score', 0)), "Source Credibility", f"{data['research'].get('total_sources', 0)} sources found"),
        ("🎭", f"{tone.get('emotional_score', 0):.1f}", T["red"] if sev=="HIGH" else T["amber"] if sev=="MEDIUM" else T["green"], "Emotional Score", sev + " severity"),
        ("📝", str(ia.get("word_count", 0)), T["blue"], "Word Count", f"{ia.get('sentence_count', 0)} sentences"),
    ]

    st.markdown('<div class="metrics-grid">', unsafe_allow_html=True)
    for icon, val, color, name, note in metrics:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-top">
                <div class="metric-icon">{icon}</div>
            </div>
            <div class="metric-val" style="color:{color}">{val}</div>
            <div class="metric-name">{name}</div>
            <div class="metric-note">{note}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_issues(issues: list):
    h = sum(1 for i in issues if i.get("severity") == "HIGH")
    m = sum(1 for i in issues if i.get("severity") == "MEDIUM")
    l = sum(1 for i in issues if i.get("severity") == "LOW")

    counts = f'<span style="color:{T["red"]}">{h}H</span> <span style="color:{T["text4"]}">·</span> <span style="color:{T["amber"]}">{m}M</span> <span style="color:{T["text4"]}">·</span> <span style="color:{T["blue"]}">{l}L</span>'
    st.markdown(f"""
    <div class="section-header">
        <div class="section-icon" style="background:{T["red_dim"]}">⚡</div>
        <div class="section-title">Issues Detected</div>
        <div class="section-count">{counts}</div>
    </div>""", unsafe_allow_html=True)

    if not issues:
        st.markdown(f'<div style="color:{T["green"]};font-size:.78rem;padding:8px 4px">✓ No issues detected.</div>', unsafe_allow_html=True)
        return

    for iss in issues:
        sc = SEV_COLORS.get(iss.get("severity", "LOW"), SEV_COLORS["LOW"])
        itype = iss.get("type", "").replace("_", " ")
        isev  = iss.get("severity", "")
        st.markdown(f"""
        <div class="issue-card" style="background:{sc['bg']};border-color:{sc['border']}">
            <div class="issue-stripe" style="background:{sc['bar']}"></div>
            <div>
                <div class="issue-title" style="color:{sc['text']}">{iss.get('title','')}</div>
                <div class="issue-detail">{iss.get('detail','')}</div>
                <div class="issue-foot">
                    <span class="issue-type" style="color:{sc['bar']};border-color:{sc['bar']}33">{itype}</span>
                    <span class="issue-type" style="color:{T['text3']};border-color:{T['border']}">{isev}</span>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_claims(claims: list):
    st.markdown(f"""
    <div class="section-header">
        <div class="section-icon" style="background:{T["purple_dim"]}">🔎</div>
        <div class="section-title">Extracted Claims</div>
        <div class="section-count">{len(claims)} found</div>
    </div>""", unsafe_allow_html=True)

    if not claims:
        st.markdown(f'<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-text">No verifiable claims detected.</div></div>', unsafe_allow_html=True)
        return

    for c in claims:
        ctype = c.get("type", "general")
        color = CLAIM_COLORS.get(ctype, T["blue"])
        nums = c.get("key_numbers", [])
        nums_html = f'<div class="claim-nums">Numbers: {", ".join(nums)}</div>' if nums else ""
        check_html = '<span class="checkable-badge">Checkable ✓</span>' if c.get("checkable") else ""
        st.markdown(f"""
        <div class="claim-card" style="border-left-color:{color}">
            <div class="claim-type" style="color:{color}">{ctype.replace("_"," ")}</div>
            <div class="claim-text">{c.get("claim","")[:220]}</div>
            {nums_html}{check_html}
        </div>""", unsafe_allow_html=True)


def render_text_analysis(data: dict):
    ia = data.get("input_analysis", {})
    tone = ia.get("tone", {})

    tab1, tab2, tab3, tab4 = st.tabs(["📄 Summary", "🔄 Paraphrase", "💬 Plain English", "🎭 Tone Analysis"])

    with tab1:
        st.markdown(f'<div class="text-panel"><span class="text-panel-label">→ Extractive Summary · TF-IDF Sentence Scoring</span>{ia.get("summary","No summary available.")}</div>', unsafe_allow_html=True)

    with tab2:
        pct = ia.get("words_changed_pct", 0)
        st.markdown(f'<div class="text-panel"><span class="text-panel-label">→ Paraphrased version · <span style="color:{T["green"]}">{pct}% words changed</span></span>{ia.get("paraphrased","No paraphrase available.")}</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown(f'<div class="text-panel"><span class="text-panel-label">→ Plain English Simplification</span>{ia.get("simplified","No simplified version.")}</div>', unsafe_allow_html=True)

    with tab4:
        sev = tone.get("severity", "LOW")
        sev_col = SEV_COLORS.get(sev, SEV_COLORS["LOW"])["text"]
        rows = [
            ("Tone severity",      f'<span style="color:{sev_col};font-weight:600">{sev}</span>'),
            ("Emotional score",    f'<span style="color:{sev_col}">{tone.get("emotional_score",0)}/10</span>'),
            ("Trigger words",      f'<span style="color:{T["red"]}">{", ".join(tone.get("high_emotion_words",[]) or ["None"])}</span>'),
            ("Clickbait patterns", f'<span style="color:{T["amber"]}">{", ".join(tone.get("clickbait_patterns",[]) or ["None found"])}</span>'),
            ("Neutral indicators", f'<span style="color:{T["green"]}">{", ".join(tone.get("neutral_indicators",[]) or ["None"])}</span>'),
            ("Exclamation marks",  f'<span style="color:{T["amber"]}">{tone.get("exclamation_count",0)}</span>'),
            ("Summary",            f'<span style="color:{T["text2"]}">{tone.get("tone_summary","—")}</span>'),
        ]
        rows_html = "".join(f'<div class="tone-row"><span class="tone-key">{k}</span><span class="tone-val">{v}</span></div>' for k, v in rows)
        st.markdown(f'<div class="text-panel">{rows_html}</div>', unsafe_allow_html=True)


def render_research(data: dict):
    r = data.get("research", {})
    cov = r.get("coverage", {})
    kws = r.get("keywords", [])

    st.markdown(f"""
    <div class="section-header">
        <div class="section-icon" style="background:{T["green_dim"]}">🌐</div>
        <div class="section-title">Web Research</div>
        <div class="section-count">{r.get("total_sources",0)} sources</div>
    </div>""", unsafe_allow_html=True)

    if kws:
        chips = "".join(f'<span class="kw-tag">{k}</span>' for k in kws)
        q = r.get("query_used","")
        if q:
            chips += f'<span class="kw-query">query: {q}</span>'
        st.markdown(f'<div class="kw-wrap">{chips}</div>', unsafe_allow_html=True)

    bars = [
        ("Evidence coverage",  cov.get("coverage_score", 0),   f'{int(cov.get("coverage_score", 0))}%'),
        ("Wikipedia articles", 100 if r.get("wikipedia_found",0)>0 else 0, "found" if r.get("wikipedia_found",0)>0 else "none"),
        ("News articles",      min(100, r.get("news_found",0)*20), f'{r.get("news_found",0)} articles'),
    ]
    for label, val, suffix in bars:
        color = score_color(val)
        st.markdown(f"""
        <div class="cov-item">
            <span class="cov-label">{label}</span>
            <div class="cov-track"><div class="cov-fill" style="width:{val}%;background:{color}"></div></div>
            <span class="cov-val">{suffix}</span>
        </div>""", unsafe_allow_html=True)

    if r.get("combined_summary"):
        st.markdown(f'<div style="margin-top:1rem"><div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{T["text3"]};margin-bottom:8px">What sources say</div><div class="text-panel">{r["combined_summary"]}</div></div>', unsafe_allow_html=True)


def render_score_breakdown(bd: dict):
    st.markdown(f"""
    <div class="section-header">
        <div class="section-icon" style="background:{T["amber_dim"]}">📈</div>
        <div class="section-title">Score Breakdown</div>
    </div>""", unsafe_allow_html=True)

    items = [
        ("Evidence Coverage",    bd.get("evidence_coverage", 0),       False),
        ("Source Credibility",   bd.get("source_credibility", 0),       False),
        ("Emotional Penalty",    bd.get("tone_penalty", 0)*10,          True),
        ("Research Depth Bonus", bd.get("research_depth_bonus", 0)*10,  False),
    ]
    for label, val, bad in items:
        val = min(100, max(0, float(val)))
        if bad:  color = T["red"] if val>50 else T["amber"] if val>25 else T["green"]
        else:    color = T["green"] if val>50 else T["amber"] if val>25 else T["red"]
        st.markdown(f"""
        <div class="cov-item">
            <span class="cov-label">{label}</span>
            <div class="cov-track"><div class="cov-fill" style="width:{val}%;background:{color}"></div></div>
            <span class="cov-val">{int(val)}</span>
        </div>""", unsafe_allow_html=True)


def render_sources(sources: list):
    st.markdown(f"""
    <div class="section-header">
        <div class="section-icon" style="background:{T["blue_dim"]}">🔗</div>
        <div class="section-title">Sources</div>
        <div class="section-count">{len(sources)} found</div>
    </div>""", unsafe_allow_html=True)

    if not sources:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-icon">⚡</div>
            <div class="empty-text">No sources loaded.</div>
            <div class="empty-hint">uvicorn main:app --reload --port 8000</div>
        </div>""", unsafe_allow_html=True)
        return

    for src in sources:
        level = src.get("cred_level","medium")
        cred_color = T["green"] if level=="high" else T["amber"] if level=="medium" else T["red"]
        url = src.get("url","")
        link = f'<a href="{url}" target="_blank" style="color:{T["cyan"]};text-decoration:none">↗ Open</a>' if url else ""
        st.markdown(f"""
        <div class="source-card">
            <div class="source-head">
                <div class="source-idx">{src.get("index","•")}</div>
                <div style="flex:1">
                    <div class="source-title">{src.get("title","Unknown")}</div>
                    <div class="source-meta">
                        <span>{src.get("domain","")}</span>
                        <span style="color:{T["border"]}">·</span>
                        <span>{src.get("type","")}</span>
                        {link}
                    </div>
                    <div class="source-snippet">{src.get("snippet","")[:280]}</div>
                    <span class="source-cred" style="color:{cred_color};border-color:{cred_color}44;background:{cred_color}0d">{src.get("credibility_note","")}</span>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown(f'<div style="padding:.75rem 0 .25rem"><span style="font-size:.65rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:{T["text3"]}">FactCheck AI</span></div>', unsafe_allow_html=True)

        # Backend status
        backend_ok = False
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=2)
            backend_ok = r.status_code == 200
        except Exception:
            pass

        dot_col = T["green"] if backend_ok else T["red"]
        status_label = "Backend online" if backend_ok else "Backend offline"
        status_sub   = "Live research active" if backend_ok else "Local mode only"
        st.markdown(f"""
        <div class="status-row">
            <div class="status-dot" style="background:{dot_col};box-shadow:0 0 6px {dot_col}88"></div>
            <div>
                <div class="status-label" style="color:{dot_col}">{status_label}</div>
                <div class="status-sub">{status_sub}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Samples
        st.markdown(f'<span class="sb-label">Sample Articles</span>', unsafe_allow_html=True)
        selected_sample = None
        for name in SAMPLES:
            if st.button(name, key=f"sample_{name}", use_container_width=True):
                selected_sample = name

        # Search override
        st.markdown(f'<span class="sb-label">Search Override</span>', unsafe_allow_html=True)
        custom_query = st.text_input("Custom query", placeholder="override auto-query...", label_visibility="collapsed")

        # How it works
        st.markdown(f'<span class="sb-label">How It Works</span>', unsafe_allow_html=True)
        steps = [("①","Extract keywords & claims"), ("②","Search Wikipedia API"), ("③","Fetch Google News RSS"), ("④","TF-IDF similarity check"), ("⑤","Score source credibility"), ("⑥","Generate human report")]
        steps_html = "".join(f'<div class="how-step"><div class="how-num">{n}</div><div class="how-text">{t}</div></div>' for n, t in steps)
        st.markdown(steps_html, unsafe_allow_html=True)

        # Start backend hint
        st.markdown(f"""
        <div style="margin-top:1.25rem;padding:10px 12px;background:{T["surface2"]};border:1px solid {T["border"]};border-radius:10px">
            <div style="font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{T["text3"]};margin-bottom:6px">Start Backend</div>
            <code style="color:{T["cyan"]};font-size:.6rem;display:block;margin-bottom:3px">pip install -r requirements.txt</code>
            <code style="color:{T["green"]};font-size:.6rem">uvicorn main:app --reload</code>
        </div>""", unsafe_allow_html=True)

        return selected_sample, custom_query


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    render_header()
    selected_sample, custom_query = render_sidebar()

    if "input_text" not in st.session_state: st.session_state.input_text = ""
    if "result"     not in st.session_state: st.session_state.result = None
    if selected_sample: st.session_state.input_text = SAMPLES[selected_sample]

    # ── Input area ─────────────────────────────────────────────────
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        input_text = st.text_area(
            "input",
            value=st.session_state.input_text,
            height=150,
            placeholder="Paste any article, news claim, or statement to fact-check...\n\nTip: Try sample articles in the sidebar →",
            label_visibility="collapsed",
            key="main_input",
        )
        words = len(input_text.split()) if input_text.strip() else 0
        st.markdown(f'<div class="word-hint">{words} words · {len(input_text)} characters</div>', unsafe_allow_html=True)

    with col_btn:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        analyze_clicked = st.button("🔍 Fact-Check", use_container_width=True, type="primary")
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        clear_clicked = st.button("✕ Clear", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if clear_clicked:
            st.session_state.input_text = ""
            st.session_state.result = None
            st.rerun()

    # ── Analysis ───────────────────────────────────────────────────
    if analyze_clicked and input_text and input_text.strip():
        if len(input_text.split()) < 5:
            st.warning("Please enter at least 5 words to fact-check.")
        else:
            st.session_state.input_text = input_text
            prog_placeholder = st.empty()
            steps   = ["Extract", "Research", "Summarize", "Analyze", "Report"]
            messages = [
                "🔬 Extracting keywords and claims...",
                "🌐 Searching Wikipedia and Google News...",
                "📝 Running summarizer & paraphraser...",
                "⚡ Running TF-IDF similarity analysis...",
                "✅ Generating fact-check report...",
            ]
            with prog_placeholder.container():
                prog_bar = st.progress(0)
                msg_box  = st.empty()
                for i, (step, msg) in enumerate(zip(steps, messages)):
                    step_html = "".join(
                        f'<div class="step-item {"active" if j==i else "done" if j<i else ""}">{steps[j]}</div>'
                        for j in range(len(steps))
                    )
                    msg_box.markdown(
                        f'<div class="steps-wrap">{step_html}</div><div class="step-msg">{msg}</div>',
                        unsafe_allow_html=True,
                    )
                    prog_bar.progress((i+1)*20)
                    time.sleep(0.4 if i < 2 else 0.2)
            prog_placeholder.empty()

            result = call_backend(input_text, custom_query)
            if result is None:
                result = local_analyze(input_text)
            st.session_state.result = result

    # ── Results ────────────────────────────────────────────────────
    if st.session_state.result:
        data = st.session_state.result
        st.markdown('<div class="fc-divider"></div>', unsafe_allow_html=True)

        render_verdict(data)
        render_metrics(data)

        st.markdown('<div class="fc-divider"></div>', unsafe_allow_html=True)

        # Issues + Claims
        col_l, col_r = st.columns(2, gap="medium")
        with col_l:
            st.markdown('<div class="fc-card">', unsafe_allow_html=True)
            render_issues(data.get("issues", []))
            st.markdown('</div>', unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="fc-card">', unsafe_allow_html=True)
            render_claims(data.get("claims", []))
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="fc-divider"></div>', unsafe_allow_html=True)

        # Text analysis
        st.markdown(f'<div style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{T["text3"]};margin-bottom:.75rem">📊 Text Analysis</div>', unsafe_allow_html=True)
        render_text_analysis(data)

        st.markdown('<div class="fc-divider"></div>', unsafe_allow_html=True)

        # Research + Breakdown
        col_r2, col_b = st.columns([3, 2], gap="medium")
        with col_r2:
            st.markdown('<div class="fc-card">', unsafe_allow_html=True)
            render_research(data)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="fc-card">', unsafe_allow_html=True)
            render_score_breakdown(data.get("score_breakdown", {}))
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="fc-divider"></div>', unsafe_allow_html=True)

        # Sources
        st.markdown('<div class="fc-card">', unsafe_allow_html=True)
        render_sources(data.get("sources", []))
        st.markdown('</div>', unsafe_allow_html=True)

        # Raw JSON
        with st.expander("🗂 Raw JSON Response"):
            st.markdown(
                f'<div class="json-block">{json.dumps(data, indent=2, default=str)[:8000]}</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()