#!/usr/bin/env python3
"""
RetentionAI — Main Orchestrator Agent
Azercell Customer Retention & Product Evolution System

Run:
    python src/agent.py
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# ── ensure src/ is importable regardless of CWD ──
sys.path.insert(0, str(Path(__file__).parent))

from analyzer import analyze_feedback
from offer_generator import generate_special_offer

# ─────────────────────────────────────────────────────
# Terminal Color & Style Helpers
# ─────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

BLACK  = "\033[30m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"

BG_DARK  = "\033[48;5;235m"
BG_BLUE  = "\033[48;5;17m"


def c(text, *styles):
    return "".join(styles) + str(text) + RESET


def banner():
    width = 70
    print()
    print(c("═" * width, CYAN, BOLD))
    print(c("  ██████╗ ███████╗████████╗███████╗███╗   ██╗████████╗██╗ ██████╗ ███╗   ██╗", CYAN))
    print(c("  ██╔══██╗██╔════╝╚══██╔══╝██╔════╝████╗  ██║╚══██╔══╝██║██╔═══██╗████╗  ██║", CYAN))
    print(c("  ██████╔╝█████╗     ██║   █████╗  ██╔██╗ ██║   ██║   ██║██║   ██║██╔██╗ ██║", CYAN))
    print(c("  ██╔══██╗██╔══╝     ██║   ██╔══╝  ██║╚██╗██║   ██║   ██║██║   ██║██║╚██╗██║", CYAN))
    print(c("  ██║  ██║███████╗   ██║   ███████╗██║ ╚████║   ██║   ██║╚██████╔╝██║ ╚████║", CYAN))
    print(c("  ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝", CYAN))
    print()
    print(c("  Dual-Pathway Customer Retention & Product Evolution Agent", WHITE, BOLD))
    print(c("  Powered by Azercell × StarNest × OMNI AI Summit", DIM))
    print(c("═" * width, CYAN, BOLD))
    print()


def section_header(title: str, icon: str = "▶"):
    print()
    print(c(f"  {icon}  {title}", YELLOW, BOLD))
    print(c("  " + "─" * 60, DIM))


def priority_color(priority: str) -> str:
    return {
        "CRITICAL": c(f"● {priority}", RED, BOLD),
        "HIGH":     c(f"● {priority}", YELLOW, BOLD),
        "MEDIUM":   c(f"● {priority}", CYAN),
        "LOW":      c(f"● {priority}", GREEN),
    }.get(priority, priority)


def tier_badge(tier: str) -> str:
    return {
        "VIP":      c(" ★ VIP CONCIERGE ", BG_BLUE, WHITE, BOLD),
        "Premium":  c(" ◆ PREMIUM ", MAGENTA, BOLD),
        "Standard": c(" ○ STANDARD ", DIM),
    }.get(tier, tier)


def print_customer_card(customer: dict):
    print()
    print(c(f"  ┌─── CUSTOMER PROFILE {'─'*40}", BLUE))
    print(c(f"  │  ID      : {customer['customer_id']}", BLUE) + c(f"  {tier_badge(customer['tier'])}", ""))
    print(c(f"  │  Name    : {customer['name']}", BLUE))
    print(c(f"  │  Product : {customer['product']}", BLUE))
    print(c(f"  │  LTV     : ", BLUE) + c(f"${customer['lifetime_value_usd']:,}", GREEN, BOLD) +
          c(f"   Margin Cap: ", BLUE) + c(f"{customer['margin_limit_percentage']}%", YELLOW, BOLD))
    print(c(f"  └{'─'*55}", BLUE))
    print()
    print(c("  📨 Feedback:", DIM))
    print(c(f"  \"{customer['feedback']}\"", WHITE, DIM))


def print_pathway_a(analysis: dict):
    section_header("PATHWAY A — Product Intelligence (Dev/Product Team)", "🔧")
    print(c(f"    Sentiment       : ", DIM) + c(analysis.get('sentiment', 'N/A'), YELLOW, BOLD))
    print(c(f"    Affected Feature: ", DIM) + c(analysis.get('affected_feature', 'N/A'), CYAN))
    print(c(f"    Core Issue      : ", DIM) + c(analysis.get('core_issue', 'N/A'), WHITE))
    print(c(f"    Priority        : ", DIM) + priority_color(analysis.get('priority', 'N/A')))
    print()
    print(c("    📋 Product Insight for Dev Team:", GREEN, BOLD))
    print(c(f"    → {analysis.get('product_insight', 'N/A')}", GREEN))


def print_pathway_b(result: dict, customer_name: str):
    params = result["offer_params"]
    section_header("PATHWAY B — Luma Customer Success Agent", "💬")
    print(c(f"    Customer Tier   : {tier_badge(params['tier_label'])}", ""))
    print(c(f"    Offer Type      : ", DIM) + c(params['offer_type'], MAGENTA))
    print(c(f"    LTV             : ", DIM) + c(f"${params['ltv_usd']:,}", GREEN, BOLD))
    print(c(f"    Max Discount    : ", DIM) + c(f"{params['max_discount']}%", YELLOW, BOLD) +
          c("  ← Margin-Protected Ceiling", DIM))
    print()
    print(c("    ✉️  Message from Luma:", CYAN, BOLD))
    print()
    # Word-wrap the message for clean terminal display
    message_lines = result["message"].split("\n")
    for line in message_lines:
        print(c(f"    {line}", WHITE))


def print_summary(processed: int, total_ltv: float, start_time: float):
    elapsed = time.time() - start_time
    print()
    print(c("═" * 70, GREEN, BOLD))
    print(c("  ✅  RETENTION PIPELINE COMPLETE", GREEN, BOLD))
    print(c(f"  Customers Processed : {processed}", WHITE))
    print(c(f"  Total Portfolio LTV : ${total_ltv:,.0f}", GREEN, BOLD))
    print(c(f"  Elapsed Time        : {elapsed:.2f}s", DIM))
    print(c(f"  Timestamp           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", DIM))
    print(c("═" * 70, GREEN, BOLD))
    print()


def run_agent():
    banner()

    # ── Load customer data ──
    data_path = Path(__file__).parent.parent / "data" / "customers.json"
    if not data_path.exists():
        print(c(f"  ERROR: customers.json not found at {data_path}", RED, BOLD))
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        customers = json.load(f)

    print(c(f"  Loaded {len(customers)} customer records from {data_path.name}", DIM))
    start_time = time.time()
    total_ltv = sum(c["lifetime_value_usd"] for c in customers)

    # ── Process each customer ──
    for i, customer in enumerate(customers, 1):
        separator = c("━" * 70, DIM)
        print(f"\n{separator}")
        print(c(f"  PROCESSING CUSTOMER {i}/{len(customers)}", BOLD, WHITE))

        print_customer_card(customer)

        # ─ Pathway A: Analyze ─
        print()
        print(c("  ⏳ Running Pathway A: Analyzing feedback...", DIM))
        try:
            analysis = analyze_feedback(customer["feedback"])
        except Exception as e:
            print(c(f"  ✖ Analyzer failed: {e}", RED))
            continue

        print_pathway_a(analysis)

        # ─ Pathway B: Generate Offer ─
        print()
        print(c("  ⏳ Running Pathway B: Generating Luma retention offer...", DIM))
        try:
            offer_result = generate_special_offer(
                text=customer["feedback"],
                analysis=analysis,
                customer_data=customer,
            )
        except Exception as e:
            print(c(f"  ✖ Offer generator failed: {e}", RED))
            continue

        print_pathway_b(offer_result, customer["name"])
        print()

    # ── Final Summary ──
    print_summary(len(customers), total_ltv, start_time)


if __name__ == "__main__":
    run_agent()
