import os
import base64
import pandas as pd
import requests
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_PROJECT = "CLP"
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

# === Input Epic keys ===
epic_keys = ["CLP-75", "CLP-112", "CLP-840"]
slipped_csv_path = "/Users/jameslogan/Documents/clean_sprint_watchdog/sprint_watchdog_filtered_slips.csv"
output_csv = "slipped_stories_under_epics.csv"

# === Load slipped story keys ===
slipped_df = pd.read_csv(slipped_csv_path)
slipped_keys = set(slipped_df["key"].str.strip().str.upper())

# === Query Jira for stories under each epic ===
def get_stories_under_epic(epic_key):
    jql = (
        f'project = {JIRA_PROJECT} AND issuetype = Story AND "Epic Link" = {epic_key}'
    )
    url = f"{JIRA_DOMAIN}/rest/api/3/search?jql={requests.utils.quote(jql)}&maxResults=100"
    r = requests.get(url, headers=HEADERS)
    data = r.json()
    stories = data.get("issues", [])
    results = []

    for issue in stories:
        key = issue["key"]
        fields = issue["fields"]
        summary = fields["summary"]
        assignee = fields["assignee"]["displayName"] if fields.get("assignee") else "Unassigned"
        component_list = fields.get("components", [])
        components = ", ".join([c["name"] for c in component_list])
        results.append({
            "key": key,
            "summary": summary,
            "assignee": assignee,
            "component": components,
            "epic": epic_key
        })

    return results

# === Aggregate results for all epics ===
all_stories = []
for epic in epic_keys:
    all_stories.extend(get_stories_under_epic(epic))

story_df = pd.DataFrame(all_stories)

# === Filter stories that slipped ===
story_df["key_upper"] = story_df["key"].str.upper()
slipped_story_df = story_df[story_df["key_upper"].isin(slipped_keys)].drop(columns="key_upper")

# === Join with slippage info ===
merged_df = pd.merge(
    slipped_story_df,
    slipped_df,
    on="key",
    how="left",
    suffixes=('', '_slip')
)[["key", "summary", "assignee", "component", "epic", "times_moved", "last_moved"]]

# === Output CSV ===
merged_df.to_csv(output_csv, index=False)
print(f"✅ Report written to {output_csv}")
print(merged_df)
