# SPRINT COMPLETION REPORT — NOW SLIP-SMART™

import os
import base64
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from slack_sdk import WebClient

# === Load .env ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")

# === Jira auth headers ===
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

# === Team boards ===
boards = {
    "Data Science": 251,
    "Design": 250,
    "Engineering": 252
}

# === File paths ===
CSV_PATH = "sprint_completion_report.csv"
CHART_PATH = "sprint_completion_chart.png"
SLIPPED_ISSUES_PATH = "/Users/jameslogan/Documents/clean_sprint_watchdog/sprint_watchdog_filtered_slips.csv"

# === Slack functions ===
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

# === Load slipped issue keys ===
def load_slipped_issues():
    try:
        df = pd.read_csv(SLIPPED_ISSUES_PATH)
        return set(df['key'].dropna().tolist())
    except Exception as e:
        print("⚠️ Error loading slipped stories:", e)
        return set()

# === Sprint report API logic ===
def get_sprint_report_data(board_id, slipped_keys):
    url = f"{JIRA_DOMAIN}/rest/agile/1.0/board/{board_id}/sprint?state=closed"
    r = requests.get(url, headers=HEADERS)
    all_sprints = r.json().get("values", [])
    sprints = all_sprints[-4:-1] if len(all_sprints) >= 4 else all_sprints[-3:]

    results = []

    for sprint in sprints:
        sprint_id = sprint["id"]
        report_url = f"{JIRA_DOMAIN}/rest/greenhopper/1.0/rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}"
        r = requests.get(report_url, headers=HEADERS)
        data = r.json()

        completed = data.get("contents", {}).get("completedIssues", [])
        not_done = data.get("contents", {}).get("issuesNotCompletedInCurrentSprint", [])

        def get_key(issue):
            return issue.get("key", "").strip().upper()

        planned_issues = [i for i in completed + not_done if get_key(i) not in slipped_keys]
        completed_issues = [i for i in completed if get_key(i) not in slipped_keys]
        all_issues = completed + not_done  # before filtering

        results.append((planned_issues, completed_issues, all_issues))

    return results


# === Report Builder ===
def build_report():
    slipped_keys = load_slipped_issues()
    # Normalize slipped keys just in case
    slipped_keys = set(k.strip().upper() for k in slipped_keys)

    rows = []

    for team, board_id in boards.items():
        print(f"\n🔍 Checking team: {team}")
        sprint_data = get_sprint_report_data(board_id, slipped_keys)

        total_planned = 0
        total_completed = 0
        excluded_keys = []

        for sprint_id, (planned_issues, completed_issues, all_issues) in enumerate(sprint_data):
            planned_ids = [i.get("key", "") for i in planned_issues]
            completed_ids = [i.get("key", "") for i in completed_issues]
            all_ids = [i.get("key", "") for i in all_issues]
            filtered_out = [k for k in all_ids if k.upper() in slipped_keys]
            excluded_keys.extend(filtered_out)

            total_planned += sum(i.get("estimateStatistic", {}).get("statFieldValue", {}).get("value", 0) for i in planned_issues)
            total_completed += sum(i.get("estimateStatistic", {}).get("statFieldValue", {}).get("value", 0) for i in completed_issues)

        percent = round((total_completed / total_planned) * 100, 1) if total_planned else 0

        print(f"🧮 {team} - Planned Points: {total_planned}, Completed Points: {total_completed}, Completion %: {percent}")
        print(f"🚫 Excluded Issues (Slipped): {excluded_keys[:10]}{' ...' if len(excluded_keys) > 10 else ''}")

        rows.append({
            "Team": team,
            "Planned Points": total_planned,
            "Completed Points": total_completed,
            "Completion %": percent
        })

    df = pd.DataFrame(rows)

    # Save CSV with explanation
    explanation = (
        "\n\n---\nExplanation:\n"
        "Only includes stories committed at sprint start and not removed or slipped to future sprints.\n"
        "• Slipped stories were excluded using `sprint_watchdog_filtered_slips.csv`\n"
        "• Completion % = (Completed Story Points / Planned) * 100\n"
        "• This version prints debug info to help validate filtering logic."
    )
    df.to_csv(CSV_PATH, index=False)
    with open(CSV_PATH, "a") as f:
        f.write(explanation)


    # Chart
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    bar = sns.barplot(data=df, x="Team", y="Completion %", hue="Team", palette="Set2", legend=False)

    for i, row in df.iterrows():
        bar.text(i, row["Completion %"] + 2, f'{row["Completion %"]}%', ha='center', fontweight='bold')

    plt.title("Sprint Completion by Team (Slipped Stories Excluded)", fontsize=14, fontweight='bold')
    plt.ylabel("Completion %")
    plt.ylim(0, 120)
    plt.xticks(fontsize=11)
    plt.figtext(0.5, -0.1,
        "Only includes stories that remained in the sprint and were not moved to a future sprint.",
        wrap=True, horizontalalignment='center', fontsize=9, color="gray")
    plt.tight_layout()
    plt.savefig(CHART_PATH, bbox_inches='tight')
    plt.close()

    # Post to Slack
    slack_summary = (
        "*🎯 Sprint Completion Report (Slip-Smart™)*\n"
        "```\n" + df.to_string(index=False) + "\n```\n"
        "_Stories that were moved to future sprints were excluded to ensure accuracy._"
    )

    post_to_slack(slack_summary)
    upload_chart_to_slack(
        CHART_PATH,
        "Sprint Completion by Team (No Slips)",
        "This chart reflects true sprint execution by removing all stories that were moved to later sprints."
    )

# === Run the report ===
if __name__ == "__main__":
    build_report()
