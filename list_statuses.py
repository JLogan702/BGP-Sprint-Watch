import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load env variables
load_dotenv()

EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

url = f"{JIRA_DOMAIN}/rest/api/3/project/{PROJECT_KEY}/statuses"
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

response = requests.get(url, headers=headers, auth=auth)

print(f"Status Code: {response.status_code}")
print("Raw Response Text:")
print(response.text)

try:
    workflows = response.json()
    for workflow in workflows:
        issue_type = workflow['issueType']
        print(f"\n🔧 Issue Type: {issue_type}")
        for status in workflow['statuses']:
            print(f"   - {status['name']} ({status['statusCategory']['name']})")
except Exception as e:
    print(f"❌ Failed to parse response: {e}")
