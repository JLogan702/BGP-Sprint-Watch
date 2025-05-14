# BACKLOG HEALTH REPORT v2
# Tracks tickets in New or Grooming state, grouped by component and status

import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import base64

# === Load Configuration ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}
CSV_PATH = "backlog_health_report.csv"
CHART_PATH = "backlog_health_by_component.png"

STATUS_FILTER = ["New", "Grooming"]

# === Jira Data Fetch ===
def get_issues():
    jql = f'project = {PROJECT_KEY} AND status in ({", ".join([f"\"{s}\"" for s in STATUS_FILTER])})'
    start_at = 0
    all_issues = []
    while True:
        resp = requests.get(
            f"{JIRA_DOMAIN}/rest/api/3/search",
            headers=HEADERS,
            params={
                "jql": jql,
                "startAt": start_at,
                "maxResults": 100,
                "fields": "key,summary,status,assignee,components"
            }
        )
        if resp.status_code != 200:
            print("Jira error:", resp.status_code, resp.text)
            resp.raise_for_status()
        data = resp.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)
        if len(issues) < 100:
            break
        start_at += 100
    return all_issues

# === Slack Posting ===
def post_to_slack(message):
    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        client.chat_postMessage(channel=SLACK_CHANNEL, text="Backlog Health Report", blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": message}}
        ])
    except SlackApiError as e:
        print("Slack error:", e.response['error'])

# === Chart Upload ===
def upload_chart_to_slack(file_path, title="Backlog Health Chart"):
    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        with open(file_path, "rb") as file_content:
            response = client.files_upload_v2(
                channel=SLACK_CHANNEL,
                file=file_content,
                filename=os.path.basename(file_path),
                title=title,
                initial_comment="📊 Here's the chart visual from the backlog health report:"
            )
        print("✅ Chart uploaded to Slack.")
    except SlackApiError as e:
        print("❌ Slack upload failed:", e.response['error'])


# === Generate Visuals ===
def generate_chart(df):
    pivot = df.pivot_table(index="Component", columns="Status", values="Key", aggfunc="count", fill_value=0)
    pivot.plot(kind="bar", stacked=True, figsize=(12, 6))
    plt.title("Backlog Health by Component")
    plt.ylabel("Number of Issues")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(CHART_PATH)
    plt.close()
    return CHART_PATH

# === Report ===
def build_report():
    issues = get_issues()
    records = []
    for issue in issues:
        fields = issue["fields"]
        records.append({
            "Key": issue["key"],
            "Summary": fields.get("summary", ""),
            "Status": fields.get("status", {}).get("name", ""),
            "Component": ", ".join([c["name"] for c in fields.get("components", [])]) or "None",
            "Assignee": fields["assignee"]["displayName"] if fields.get("assignee") else "Unassigned"
        })

    df = pd.DataFrame(records)
    df.to_csv(CSV_PATH, index=False)
    chart = generate_chart(df)

    summary = (
        f"*🧹 Backlog Health Report: `{PROJECT_KEY}`*\n"
        f"```\n"
        f"Total issues: {len(df)}\n"
        f"Statuses included: {', '.join(STATUS_FILTER)}\n"
        f"CSV: {CSV_PATH}\n"
        f"Chart: {CHART_PATH}\n"
        f"```\n"
        "👉 This report shows all tickets in *New* or *Grooming* status, grouped by Component. "
        "Use it to identify unrefined or unassigned work early in the pipeline."
    )

    post_to_slack(summary)
    upload_chart_to_slack(CHART_PATH)

# === Entry Point ===
if __name__ == "__main__":
    build_report()