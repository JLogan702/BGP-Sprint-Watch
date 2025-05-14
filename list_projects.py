import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load .env
load_dotenv()

EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")

url = f"{JIRA_DOMAIN}/rest/api/3/project"
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

response = requests.get(url, headers=headers, auth=auth)

print(f"Status Code: {response.status_code}")
if response.ok:
    projects = response.json()
    print("\n📋 Available Projects:")
    for proj in projects:
        print(f"- {proj['key']}: {proj['name']}")
else:
    print(f"❌ Error: {response.text}")
