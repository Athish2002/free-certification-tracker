import json
from pathlib import Path

def audit_offers():
    offers_path = Path("data/offers.json")
    with open(offers_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    offers = data.get("offers", [])
    print(f"Total Tracked Offers: {len(offers)}")
    
    active = [o for o in offers if o.get("status") == "Active"]
    review = [o for o in offers if o.get("status") == "Review Needed"]
    closed = [o for o in offers if o.get("status") in ("Registrations Closed", "Concluded", "Expired")]
    
    print(f"\n--- ACTIVE OFFERS ({len(active)}) ---")
    for o in active:
        tier = o.get("credential_tier", "unknown")
        val = o.get("value_usd", 0)
        auth = o.get("authenticity_score", 0)
        tv = o.get("truth_verification", {})
        policy = tv.get("policy_type", "none")
        print(f"• [{o['platform']}] {o['title']}")
        print(f"  ID: {o['id']} | Tier: {tier} | Value: ${val} | Auth Score: {auth}%")
        print(f"  Policy: {policy} | URL: {o.get('url')}")
        
    print(f"\n--- REVIEW NEEDED ({len(review)}) ---")
    for o in review:
        print(f"• [{o['platform']}] {o['title']} ({o['id']}) -> {o.get('notes')}")

    print(f"\n--- CLOSED / TRIAGE ({len(closed)}) ---")
    for o in closed:
        print(f"• [{o['platform']}] {o['title']} ({o['id']}) -> Status: {o.get('status')}")

if __name__ == "__main__":
    audit_offers()
