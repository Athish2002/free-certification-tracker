import urllib.request
import json

def check_ci():
    url = "https://api.github.com/repos/Athish2002/free-certification-tracker/actions/runs?per_page=10"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            runs = data.get("workflow_runs", [])
            print(f"Total Workflow Runs Returned: {len(runs)}")
            for r in runs:
                print(f"ID: {r['id']} | Event: {r['event']} | Status: {r['status']} | Conclusion: {r['conclusion']} | SHA: {r['head_sha'][:7]} | Branch: {r['head_branch']} | Created: {r['created_at']}")
    except Exception as e:
        print("Error fetching GitHub Actions runs:", e)

if __name__ == "__main__":
    check_ci()
