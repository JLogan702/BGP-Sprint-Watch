import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")

token = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
headers = {
    "Authorization": f"Basic {token}",
    "Accept": "application/json"
}

response = requests.get(f"{JIRA_DOMAIN}/rest/api/3/myself", headers=headers)
print("Status Code:", response.status_code)
print("Response:", response.json())
