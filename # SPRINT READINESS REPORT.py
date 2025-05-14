# SPRINT READINESS REPORT v2
# Compares To Do + Ready tickets against average velocity per board

import os
import base64
import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from collections import defaultdict

# === Load Environment ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")
STORY_POINTS_FIELD = os.getenv("STORY_POINTS_FIELD")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

# === Board Map ===
boards = {
    "Data Science": 251,
    "Design": 250,
    "Engineering - AI Ops": 448,
    "Engineering - Platform": 252,
    "Engineering - Product": 514
}

READY_STATUSES = ["To Do", "Ready for Development"]
CSV_PATH = "sprint_readiness_report.csv"
BAR_CHART = "sprint_readiness_chart.png"
PIE_CHART = "sprint_ticket_distribution.png"

# === Slack Posting ===
def post_to_slack(message):
    client = WebClient(token=SLACK_BOT_TOKEN)
    client.chat_postMessage(channel=SLACK_CHANNEL, text=message)

def upload_chart_to_slack(file_path, title, explanation):
    client = WebClient(token=SLACK_BOT_TOKEN)
    with open(file_path, "rb") as file_content:
        client.files_upload_v2(
            channel=SLACK_CHANNEL,
            file=file_content,
            filename=os.path.basename(file_path),
            title=title,
            initial_comment=f"📊 *{title}*\n{explanation}"
        )

# === Velocity Calculation ===
def get_average_velocity(board_id):
    url = f"{JIRA_DOMAIN}/rest/agile/1.0/board/{board_id}/sprint?state=closed"
    r = requests.get(url, headers=HEADERS)
    sprints = r.json().get("values", [])[-2:]  # last 2
    velocities = []
    for sprint in sprints:
        sprint_id = sprint["id"]
        issues_url = f"{JIRA_DOMAIN}/rest/agile/1.0/sprint/{sprint_id}/issue?maxResults=100"
        resp = requests.get(issues_url, headers=HEADERS)
        completed_points = 0
        for issue in resp.json().get("issues", []):
            fields = issue.get("fields", {})
            status = fields.get("status", {}).get("statusCategory", {}).get("key", "")
            points = fields.get(STORY_POINTS_FIELD)
            if status == "done" and points:
                completed_points += points
        velocities.append(completed_points)
    return round(sum(velocities)/len(velocities), 1) if velocities else 0

# === Readiness Calculation ===
def get_ready_tickets(board_id):
    url = f"{JIRA_DOMAIN}/rest/agile/1.0/board/{board_id}/sprint?state=active"
    resp = requests.get(url, headers=HEADERS)
    sprints = resp.json().get("values", [])
    if not sprints:
        return 0
    sprint_id = sprints[0]["id"]
    issues_url = f"{JIRA_DOMAIN}/rest/agile/1.0/sprint/{sprint_id}/issue?maxResults=100"
    resp = requests.get(issues_url, headers=HEADERS)
    count = 0
    for issue in resp.json().get("issues", []):
        status = issue["fields"].get("status", {}).get("name", "")
        if status in READY_STATUSES:
            count += 1
    return count

# === Report ===
def build_report():
    rows = []
    for team, board_id in boards.items():
        velocity = get_average_velocity(board_id)
        ready = get_ready_tickets(board_id)
        percent = round((ready / velocity) * 100) if velocity else 0
        rows.append({
            "Team": team,
            "Tickets_Ready": ready,
            "Avg_Velocity": velocity,
            "Readiness_%": percent
        })

    df = pd.DataFrame(rows)

    # Explanation for the CSV
    explanation_text = (
        "\n\n---\nExplanation:\n"
        "This report compares the number of tickets in `To Do` and `Ready for Development` "
        "statuses from the current open sprint against the average team velocity from the last two closed sprints.\n"
        "The readiness percentage = (Ready tickets / Avg Velocity) * 100.\n"
        "Helps identify if teams have enough refined work queued for the next sprint cycle."
    )

    df.to_csv(CSV_PATH, index=False)
    with open(CSV_PATH, "a") as f:
        f.write(explanation_text)

    # Bar Chart
    plt.figure(figsize=(10, 6))
    df.sort_values("Readiness_%", ascending=False).plot(
        kind="bar", x="Team", y="Readiness_%", legend=False
    )
    plt.title("Sprint Readiness by Team (% of Avg Velocity)")
    plt.ylabel("Readiness %")
    plt.tight_layout()
    plt.savefig(BAR_CHART)
    plt.close()

    # Pie Chart
    plt.figure(figsize=(6, 6))
    df.set_index("Team")["Tickets_Ready"].plot.pie(autopct="%1.1f%%")
    plt.ylabel("")
    plt.title("Ready Ticket Distribution by Team")
    plt.tight_layout()
    plt.savefig(PIE_CHART)
    plt.close()

    # Slack Summary
    summary = (
        "*📦 Sprint Readiness Report*\n"
        "```\n"
        + df.to_string(index=False) + "\n"
        "```\n"
        "This report shows how many stories are ready (`To Do`, `Ready for Development`) "
        "compared to average team velocity across the last 2 sprints."
    )

    post_to_slack(summary)

    upload_chart_to_slack(
        BAR_CHART,
        "Sprint Readiness by Team (% of Avg Velocity)",
        "This bar chart shows how many tickets are ready (To Do + Ready for Development) per team compared to average sprint velocity over the past 2 sprints. A higher % means the team has a refined backlog ready to tackle."
    )

    upload_chart_to_slack(
        PIE_CHART,
        "Ready Ticket Distribution by Team",
        "This pie chart shows how the total number of ready tickets is distributed across teams. Helps identify which teams may be underprepared or overcommitted."
    )

# === Entry Point ===
if __name__ == "__main__":
    build_report()