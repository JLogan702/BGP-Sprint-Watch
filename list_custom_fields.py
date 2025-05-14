import os
import base64
import requests
from dotenv import load_dotenv

# === Load env vars ===
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")

# === Auth header ===
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Basic {base64.b64encode(f'{EMAIL}:{API_TOKEN}'.encode()).decode()}"
}

# === Fetch all fields ===
url = f"{JIRA_DOMAIN}/rest/api/3/field"
response = requests.get(url, headers=HEADERS)
fields = response.json()

# === Print matching field names
print("\n🔍 Searching for 'Epic Link' field ID...")
for field in fields:
    if "epic" in field["name"].lower():
        print(f"{field['name']} → {field['id']}")
