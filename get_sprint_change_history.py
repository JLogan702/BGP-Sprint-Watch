import os
import base64
import requests
import pandas as pd
from dotenv import load_dotenv

# === Load Jira credentials ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic " + base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
}

# === Load slipped stories ===
slipped_csv_path = "/Users/jameslogan/Documents/BGP_Sprint_Watch/slipped_stories_with_epics.csv"
df = pd.read_csv(slipped_csv_path)
issue_keys = df["key"].dropna().unique().tolist()

# === Function to get sprint history from changelog ===
def get_sprint_transitions(issue_key):
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}?expand=changelog"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return None, None

    data = r.json()
    from_sprint, to_sprint = None, None

    for history in data.get("changelog", {}).get("histories", []):
        for item in history.get("items", []):
            if item.get("field") == "Sprint":
                from_sprint = item.get("fromString")
                to_sprint = item.get("toString")

    return from_sprint, to_sprint

# === Loop and collect sprint transitions ===
results = []
for key in issue_keys:
    from_sprint, to_sprint = get_sprint_transitions(key)
    results.append({
        "key": key,
        "from_sprint": from_sprint,
        "to_sprint": to_sprint
    })

# === Merge into original data and export ===
history_df = pd.DataFrame(results)
merged = df.merge(history_df, on="key", how="left")
merged.to_csv("slipped_stories_with_sprint_changes.csv", index=False)
print("✅ Sprint transitions exported to slipped_stories_with_sprint_changes.csv")
