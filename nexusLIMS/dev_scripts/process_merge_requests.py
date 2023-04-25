# ruff: noqa
"""
Print minimal details about issues and merge requests in a Gitlab project using the API.

This script was originally used to get a CSV list of issues and merge requests in the
order they were closed or merged, to be used in retroactively generating a changelog
for the NexusLIMS project.

Requires three environment variables: gitlab_project_id (the numeric id of the project
on a Gitlab server), gitlab_api_url (e.g. https://my.gitlab.com/api/v4 or sometimes
https://my.gitlab.com/gitlab/api/v4), and gitlab_api_token (a project or personal
access token with permissions to read the project in question).
"""

import os

import dotenv
import requests

dotenv.load_dotenv()

project_id = os.environ.get("gitlab_project_id")
api_url = os.environ.get("gitlab_api_url")
api_token = os.environ.get("gitlab_api_token")

mr_url = f"{api_url}/projects/{project_id}/merge_requests"
issue_url = f"{api_url}/projects/{project_id}/issues"
headers = {"PRIVATE-TOKEN": api_token}

payload = ""

merge_requests, issues = [], []

x_next_page = 1

while x_next_page:
    querystring = {"page": str(x_next_page)}

    response = requests.request(
        "GET",
        issue_url,
        data=payload,
        headers=headers,
        params=querystring,
    )
    x_next_page = response.headers["x-next-page"]
    issues += response.json()


issues = sorted([m for m in issues if m["closed_at"]], key=lambda x: x["closed_at"])


for m in issues:
    print(f"\"{m['iid']}\", \"{m['title']}\", \"{m['closed_at']}\"")

x_next_page = 1

while x_next_page:
    querystring = {"page": str(x_next_page)}

    response = requests.request(
        "GET",
        mr_url,
        data=payload,
        headers=headers,
        params=querystring,
    )
    x_next_page = response.headers["x-next-page"]
    merge_requests += response.json()

merge_requests = sorted(
    [m for m in merge_requests if m["merged_at"]], key=lambda x: x["merged_at"]
)

for m in merge_requests:
    print(f"\"{m['iid']}\", \"{m['title']}\", \"{m['merged_at']}\"")
