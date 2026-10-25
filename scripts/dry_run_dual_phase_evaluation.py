"""
Dry-Run Evaluation Script: Dual-Phase Adaptive Verification Engine (DPAVE)
Benchmarks all 39 offers across 22 platforms without mutating any production code.
"""

import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, List

def classify_cluster(platform: str, domain: str, path: str) -> Dict[str, str]:
    """Classifies an offer into one of the 4 platform gatekeeper clusters."""
    domain_lower = domain.lower()
    path_lower = path.lower()
    
    # Cluster B: Scholarships & Annual Application Windows
    if any(k in path_lower for k in ["scholarship", "pack", "1mcc", "lift"]) or "cncf.io" in domain_lower:
        return {
            "cluster": "Cluster B: Time-Bounded Scholarship",
            "code": "SCHOLARSHIP",
            "primary_gatekeeper": "Cohort / Capacity Closure Wall",
            "assertion_focus": "Scan for 'capacity reached', 'cohort full', or application date windows"
        }
    
    # Cluster C: Continuous Education / Recertification Communities
    if any(k in path_lower for k in ["rev-up", "recert", "community"]) or "learningnetwork.cisco.com" in domain_lower:
        return {
            "cluster": "Cluster C: CE Recertification Community",
            "code": "RECERT_COMMUNITY",
            "primary_gatekeeper": "Community Forum Thread Expiration",
            "assertion_focus": "Scan for active 30-day challenge thread & CE credit eligibility"
        }
    
    # Cluster D: Event-Tied Fast Challenges (Historical Archive)
    if any(k in domain_lower for k in ["githubuniverse", "conf", "summit"]) or any(k in path_lower for k in ["challenges", "summit"]):
        return {
            "cluster": "Cluster D: Event-Tied Fast Wave",
            "code": "EVENT_WAVE",
            "primary_gatekeeper": "Promotional Expiration 302 Silent Bounce",
            "assertion_focus": "Audit redirect chain against root conference hub downgrade"
        }
    
    # Cluster A: Enterprise LMS Portals (Default)
    return {
        "cluster": "Cluster A: Enterprise LMS Portal",
        "code": "ENTERPRISE_LMS",
        "primary_gatekeeper": "SPA Hydration Lag + OneTrust / TrustArc Cookie Shield",
        "assertion_focus": "Inject storage preset, await semantic route hydration, check $0.00 waiver"
    }

def calculate_simulated_pqs(offer: Dict[str, Any], cluster_info: Dict[str, str], is_divergent: bool) -> Dict[str, Any]:
    """Computes the simulated Proof Quality Score (PQS 0-100) and risk assessment."""
    url = offer.get("url", "")
    parsed = urlparse(url)
    path_depth = len([p for p in parsed.path.split("/") if p])
    
    # 1. URL Integrity (30 pts)
    # Deep path preserved gets higher points
    if path_depth >= 3:
        s_url = 100
    elif path_depth >= 1:
        s_url = 80
    else:
        s_url = 40
        
    # 2. DOM & Pricing Invariant (30 pts)
    cost = offer.get("cost", "")
    voucher = offer.get("voucher_code", "")
    if "$0.00" in cost or "Free" in cost or "WAIVER" in voucher:
        s_dom = 100
    elif "75%" in cost or "Partial" in cost:
        s_dom = 70
    else:
        s_dom = 50
        
    # 3. Visual Element Proof (20 pts)
    has_screenshot = bool(offer.get("screenshot_path"))
    s_visual = 100 if has_screenshot else 50
    
    # 4. Dual-Source Corroboration (20 pts)
    has_truth_source = bool(offer.get("truth_oracle", {}).get("truth_source_url"))
    s_corroboration = 100 if has_truth_source else 30
    
    # Weighted PQS formula
    pqs = (0.30 * s_url) + (0.30 * s_dom) + (0.20 * s_visual) + (0.20 * s_corroboration)
    
    if pqs >= 85:
        tier = "HIGH_CONFIDENCE_VERIFIED"
    elif pqs >= 65:
        tier = "MODERATE_CONFIDENCE_SSO_GATE"
    else:
        tier = "LOW_CONFIDENCE_REVIEW_NEEDED"
        
    return {
        "pqs_score": round(pqs, 1),
        "tier": tier,
        "s_url": s_url,
        "s_dom": s_dom,
        "s_visual": s_visual,
        "s_corroboration": s_corroboration,
        "path_depth": path_depth,
        "landing_page_risk": "HIGH" if is_divergent else "LOW"
    }

def main():
    offers_path = Path("data/offers.json")
    if not offers_path.exists():
        print("[ERROR] data/offers.json not found!")
        return

    with open(offers_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = data.get("offers", [])
    results = []
    cluster_counts = {}
    divergence_count = 0

    for offer in offers:
        offer_id = offer.get("id", "")
        platform = offer.get("platform", "")
        deep_url = offer.get("url", "")
        direct_url = offer.get("direct_verified_url", "")
        vendor_url = offer.get("verified_vendor_url", "")
        
        parsed_deep = urlparse(deep_url)
        cluster = classify_cluster(platform, parsed_deep.netloc, parsed_deep.path)
        cluster_counts[cluster["code"]] = cluster_counts.get(cluster["code"], 0) + 1
        
        # Determine old vs new navigation targets
        old_nav_target = direct_url or vendor_url or deep_url
        is_divergent = bool(direct_url and direct_url != deep_url)
        if is_divergent:
            divergence_count += 1
            
        dual_phase_plan = {
            "phase_1_authority_gate": vendor_url or direct_url or f"https://{parsed_deep.netloc}",
            "phase_2_deep_claim_proof": deep_url,
            "old_code_nav_target": old_nav_target,
            "landing_page_trap_detected": is_divergent
        }
        
        pqs_eval = calculate_simulated_pqs(offer, cluster, is_divergent)
        
        results.append({
            "id": offer_id,
            "platform": platform,
            "title": offer.get("title", ""),
            "cluster": cluster,
            "dual_phase_plan": dual_phase_plan,
            "pqs_eval": pqs_eval
        })

    # Output Summary
    print(f"=== DPAVE DRY-RUN EVALUATION COMPLETE ===")
    print(f"Total Offers Evaluated: {len(results)}")
    print(f"Landing Page Divergences Caught & Resolved: {divergence_count}")
    print("\nCluster Breakdown:")
    for c_code, count in sorted(cluster_counts.items(), key=lambda x: -x[1]):
        print(f"  • {c_code}: {count} offers")
        
    avg_pqs = sum(r["pqs_eval"]["pqs_score"] for r in results) / len(results)
    print(f"\nAverage Proof Quality Score (PQS): {avg_pqs:.1f} / 100")
    
    # Write full JSON report to brain directory
    out_json = Path("C:/Users/Athish/.gemini/antigravity/brain/2752b532-7acc-4cf6-aa66-69f850b0b12e/dry_run_dpave_results.json")
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[OK] Saved full dry-run results to: {out_json.name}")

if __name__ == "__main__":
    main()
