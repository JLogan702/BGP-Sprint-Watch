import os
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# === ENV & CONFIG ===
load_dotenv()
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = "CLP"

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")

client = WebClient(token=SLACK_BOT_TOKEN)
AUTH = (EMAIL, API_TOKEN)
HEADERS = {"Accept": "application/json"}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "slipping_stories_report.csv")
CHART_PATH = os.path.join(SCRIPT_DIR, "slipping_stories_chart.png")

# === COMPONENT MAPPING ===
COMPONENTS = [
    "Data Science", "Design", "Engineering - AI Ops", "Engineering - Platform", "Engineering - Product"
]

# === FUNCTIONS ===

def get_issues():
    jql = f'project = {PROJECT_KEY} AND issuetype = Story AND statusCategory != Done ORDER BY created DESC'
    all_issues = []
    start_at = 0
    while True:
        resp = requests.get(
            f"{JIRA_DOMAIN}/rest/api/3/search",
            headers=HEADERS,
            auth=AUTH,
            params={
                "jql": jql,
                "startAt": start_at,
                "maxResults": 100,
                "fields": "key,summary,components,customfield_10020,status",
                "expand": "changelog"
            }
        )
        data = resp.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)
        if len(issues) < 100:
            break
        start_at += 100
    return all_issues

def detect_slips(issues):
    data = []
    for issue in issues:
        key = issue["key"]
        comps = issue["fields"].get("components", [])
        component_name = comps[0]["name"] if comps else "Unassigned"
        sprints = issue["fields"].get("customfield_10020", [])
        if isinstance(sprints, list) and len(sprints) > 1:
            data.append(component_name)
    return data

def build_dataframe(component_slips):
    df = pd.DataFrame(component_slips, columns=["Component"])
    df = df[df["Component"].isin(COMPONENTS)]
    summary = df.value_counts().reset_index(name="Slipped Stories")
    summary["Total Stories"] = summary["Component"].map(df["Component"].value_counts())
    summary["Percent Slipped"] = round(summary["Slipped Stories"] / summary["Total Stories"] * 100, 1)
    return summary

def generate_chart(df):
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    chart = sns.barplot(x="Component", y="Percent Slipped", data=df, palette="coolwarm")
    for bar in chart.patches:
        height = bar.get_height()
        chart.text(bar.get_x() + bar.get_width()/2., height + 1, f'{height:.1f}%', ha='center')
    chart.set_title("Slipped Stories by Component (Sprint 4–Present)", fontsize=14)
    chart.set_ylabel("Percent of Stories Slipped (%)")
    chart.set_xlabel("Team Component")
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(CHART_PATH)
    plt.close()

def post_to_slack(df):
    explanation = (
        "*Slipping Stories Report (Sprint 4–Present)*\n"
        "This chart shows what % of user stories were originally planned in a sprint but later moved to a new one.\n\n"
        "*How this was calculated:*\n"
        "- All `Story` issues from project CLP were pulled from Jira\n"
        "- The script looked at sprint history in the `customfield_10020` field\n"
        "- If a story appeared in more than one sprint, it's counted as 'slipped'\n\n"
        "*Why this matters:*\n"
        "Frequent slipping = delivery risk, poor estimation, or cross-team blockers.\n"
    )
    try:
        client.files_upload_v2(
            channel=SLACK_CHANNEL,
            file=CHART_PATH,
            filename="slipping_stories_chart.png",
            title="Slipping Stories Chart",
            initial_comment=explanation
        )
    except SlackApiError as e:
        print("❌ Slack chart upload failed:", e.response['error'])

# === MAIN EXECUTION ===

def main():
    issues = get_issues()
    slips = detect_slips(issues)
    df = build_dataframe(slips)
    df.to_csv(CSV_PATH, index=False)
    generate_chart(df)
    post_to_slack(df)

if __name__ == "__main__":
    main()
