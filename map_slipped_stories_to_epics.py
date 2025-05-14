import os
import base64
import pandas as pd
import requests
from dotenv import load_dotenv

# === Load credentials ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

# === Load slipped stories ===
slipped_path = "/Users/jameslogan/Documents/clean_sprint_watchdog/sprint_watchdog_filtered_slips.csv"
slipped_df = pd.read_csv(slipped_path)
slipped_keys = slipped_df["key"].dropna().tolist()

# === Function to get Epic Link for a given issue key ===
def get_epic_link(issue_key):
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}?fields=summary,customfield_10005"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        return data["fields"].get("customfield_10005")  # Epic Link
    return None

# === Map epic links ===
epic_map = {}
for key in slipped_keys:
    epic_key = get_epic_link(key)
    epic_map[key] = epic_key if epic_key else "None"

# === Add Epic column to slipped_df ===
slipped_df["epic"] = slipped_df["key"].map(epic_map)

# === Output for use in gauge charts and visuals ===
output_path = "slipped_stories_with_epics.csv"
slipped_df.to_csv(output_path, index=False)
print(f"✅ Epic mapping complete. Output saved to {output_path}")
