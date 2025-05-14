import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")  # ✅ Make sure this matches .env

url = f"{JIRA_DOMAIN}/rest/api/3/project/{PROJECT_KEY}"
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

response = requests.get(url, headers=headers, auth=auth)

print(f"Status Code: {response.status_code}")
print("Response Body:")
print(response.text)
