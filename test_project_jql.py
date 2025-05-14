import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

url = f"{JIRA_DOMAIN}/rest/api/3/search"
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = { "Accept": "application/json" }

params = {
    "jql": f"project = {PROJECT_KEY}",
    "maxResults": 1,
    "fields": "key"
}

response = requests.get(url, headers=headers, auth=auth, params=params)

print("Status Code:", response.status_code)
print("Response:", response.text)
