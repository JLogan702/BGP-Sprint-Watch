import requests
from requests.auth import HTTPBasicAuth

# CONFIG
EMAIL = "loganj@evolve24.com"
API_TOKEN = "ATATT3xFfGF0O2TH5kuupbzPkUQ_6PaYZNqe36Avq_ETjs-QC9EraS3NfyhOGLahLh-M9zfuzVIkjmNnCy_4p2kahaIkvBL6iVHycS-mGq9tnfVQcv2qZmcMXPWeamYQ8KoLz8Yz1aF1R0DuiGdleOePW9lZ3JW3Fe3MCevJpMUH2Dm6RtVMXA4=954DC039"
JIRA_DOMAIN = "https://evolve24.atlassian.net"

url = f"{JIRA_DOMAIN}/rest/api/3/status"
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

response = requests.get(url, headers=headers, auth=auth)

# Print debug output
print(f"Status Code: {response.status_code}")
print("Raw Response Text:")
print(response.text)

try:
    statuses = response.json()
    print(f"\n✅ Retrieved {len(statuses)} statuses.")
    for status in statuses:
        print(f"{status['id']}: {status['name']} ({status['statusCategory']['name']})")
except Exception as e:
    print(f"❌ Failed to parse response: {e}")
