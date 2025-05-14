import os
import base64
import requests
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from slack_sdk import WebClient

# === Load Config ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

CSV_PATH = "dependency_status_report.csv"
CHART_PATH = "dependency_graph.png"

# === Slack ===
def post_to_slack(message):
    client = WebClient(token=SLACK_BOT_TOKEN)
    client.chat_postMessage(channel=SLACK_CHANNEL, text=message)

def upload_chart_to_slack(file_path, title, explanation):
    client = WebClient(token=SLACK_BOT_TOKEN)
    with open(file_path, "rb") as f:
        client.files_upload_v2(
            channel=SLACK_CHANNEL,
            file=f,
            filename=os.path.basename(file_path),
            title=title,
            initial_comment=explanation
        )

# === Get All Issues in CLP Project ===
def get_all_issues():
    start = 0
    max_results = 100
    all_issues = []

    while True:
        jql = f'project = {PROJECT_KEY} AND statusCategory != Done'
        url = f"{JIRA_DOMAIN}/rest/api/3/search?jql={jql}&fields=key,status,issuelinks,components&startAt={start}&maxResults={max_results}"
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)
        if len(issues) < max_results:
            break
        start += max_results

    return all_issues

# === Build the Report ===
def build_report():
    all_issues = get_all_issues()
    rows = []
    graph = nx.DiGraph()

    for issue in all_issues:
        key = issue["key"]
        status = issue["fields"]["status"]["name"]
        components = issue["fields"].get("components", [])
        component = components[0]["name"] if components else "None"
        links = issue["fields"].get("issuelinks", [])

        for link in links:
            direction = None
            linked = None
            if "inwardIssue" in link:
                direction = "depends on"
                linked = link["inwardIssue"]
            elif "outwardIssue" in link:
                direction = "blocks"
                linked = link["outwardIssue"]
            if linked:
                dep_key = linked["key"]
                dep_status = linked["fields"]["status"]["name"]
                dep_components = linked["fields"].get("components", [])
                dep_component = dep_components[0]["name"] if dep_components else "None"
                rows.append({
                    "Issue": key,
                    "Status": status,
                    "Component": component,
                    "Depends On": dep_key,
                    "Dependency Status": dep_status,
                    "Dependency Component": dep_component
                })
                graph.add_edge(key, dep_key)

    # === Save CSV with explanation
    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False)
    with open(CSV_PATH, "a") as f:
        f.write("\n---\n")
        f.write("Explanation: This report maps issue-to-issue dependencies across the CLP project.\n")
        f.write("Only non-Done issues are included. Dependencies include 'blocks' and 'is blocked by' links.\n")
        f.write("Used to identify chain-of-blockage and cross-team blockers.\n")

    # === Draw Graph
    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(graph, k=0.4)
    nx.draw(graph, pos, with_labels=True, arrows=True, node_size=500, node_color="lightblue", font_size=8)
    plt.title("CLP Dependency Graph")
    plt.tight_layout()
    plt.savefig(CHART_PATH)
    plt.close()

    # === Post to Slack
    post_to_slack("*🔗 CLP Dependency Status Report*\nSee which issues are currently blocked by others.")
    upload_chart_to_slack(
        CHART_PATH,
        "CLP Issue Dependency Graph",
        "This network graph shows issue-to-issue dependencies (directional). Only active dependencies are shown."
    )

# === Run
if __name__ == "__main__":
    build_report()
