import os
import base64
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from slack_sdk import WebClient

# === Load environment ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

# === Inputs ===
epic_keys = ["CLP-75", "CLP-112", "CLP-840"]
JIRA_PROJECT = "CLP"
slipped_csv_path = "/Users/jameslogan/Documents/clean_sprint_watchdog/sprint_watchdog_filtered_slips.csv"
output_csv = "slipped_stories_under_epics.csv"
output_chart = "slipped_stories_chart.png"

# === Load slipped keys ===
slipped_df = pd.read_csv(slipped_csv_path)
slipped_keys = set(slipped_df["key"].str.strip().str.upper())

# === Get stories per epic ===
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

# === Aggregate and filter ===
all_stories = []
for epic in epic_keys:
    all_stories.extend(get_stories_under_epic(epic))

story_df = pd.DataFrame(all_stories)
story_df["key_upper"] = story_df["key"].str.upper()
slipped_story_df = story_df[story_df["key_upper"].isin(slipped_keys)].drop(columns="key_upper")

merged_df = pd.merge(
    slipped_story_df,
    slipped_df,
    on="key",
    how="left",
    suffixes=('', '_slip')
)[["key", "summary", "assignee", "component", "epic", "times_moved", "last_moved"]]

merged_df.to_csv(output_csv, index=False)

# === Chart ===
plt.figure(figsize=(8, 5))
sns.set_theme(style="whitegrid")
chart_data = merged_df["epic"].value_counts().reset_index()
chart_data.columns = ["Epic", "Slipped Stories"]

bar = sns.barplot(data=chart_data, x="Epic", y="Slipped Stories", palette="pastel")

for i, row in chart_data.iterrows():
    bar.text(i, row["Slipped Stories"] + 0.1, int(row["Slipped Stories"]), ha='center', fontweight='bold')

plt.title("Slipped Stories by Epic")
plt.ylabel("Count")
plt.xlabel("Epic")
plt.ylim(0, chart_data["Slipped Stories"].max() + 1)
plt.figtext(0.5, -0.1, "Includes stories under CLP-75, CLP-112, CLP-840 that were moved between sprints", 
            wrap=True, horizontalalignment='center', fontsize=9, color="gray")
plt.tight_layout()
plt.savefig(output_chart)
plt.close()

# === Slack ===
def post_to_slack():
    client = WebClient(token=SLACK_BOT_TOKEN)
    
    summary = "*📦 Slipped Stories by Epic*\n"
    summary += "The following stories under Epics `CLP-75`, `CLP-112`, `CLP-840` were moved between sprints:\n"
    summary += f"```\n{merged_df[['key', 'epic', 'assignee']].to_string(index=False)}\n```\n"
    summary += "_This chart shows the number of slipped stories per Epic._"

    client.chat_postMessage(channel=SLACK_CHANNEL, text=summary)

    with open(output_chart, "rb") as f:
        client.files_upload_v2(
            channel=SLACK_CHANNEL,
            file=f,
            filename=output_chart,
            title="Slipped Stories Chart",
            initial_comment="📊 Slipped stories per Epic"
        )

post_to_slack()
print(f"✅ Report written to {output_csv} and chart sent to Slack.")
