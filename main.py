import argparse
import requests
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Constants
GITHUB_API_URL = "https://api.github.com"
EXCLUDED_BRANCHES = ["main", "master"]

# Retry constants
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Helper Functions
def make_request_with_retries(url, method, headers, json=None, retries=MAX_RETRIES):
    """Make a GitHub API request with retry logic."""
    for attempt in range(retries):
        if method == "GET":
            response = requests.get(url, headers=headers, json=json)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=json)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=json)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code == 403:  # Rate limit hit
            print("Rate limit reached. Waiting before retrying...")
            time.sleep(60)  # Wait for rate limit reset
            continue
        elif response.status_code in (200, 204):  # Success
            return response
        else:
            print(f"Attempt {attempt + 1}/{retries} failed: {response.text}")
            time.sleep(RETRY_DELAY)
    return response  # Return the final failed response

def calculate_cutoff_date(time_frame_gt):
    """Calculate the cutoff date for filtering releases."""
    now = datetime.utcnow()
    if time_frame_gt.endswith("m"):
        months = int(time_frame_gt[:-1])
        return now - relativedelta(months=months)
    elif time_frame_gt.endswith("d"):
        days = int(time_frame_gt[:-1])
        return now - timedelta(days=days)
    elif time_frame_gt.endswith("h"):
        hours = int(time_frame_gt[:-1])
        return now - timedelta(hours=hours)
    else:
        raise ValueError("Invalid time frame format. Use '1m', '30d', or '24h'.")

# Cleanup Functions
def delete_releases(org, repo, token, limit=None, time_frame_gt=None):
    """
    Delete releases in a GitHub repository older than a specified timeframe.
    """
    url = f"{GITHUB_API_URL}/repos/{org}/{repo}/releases"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"per_page": 50, "page": 1}
    deleted_count = 0
    cutoff_date = calculate_cutoff_date(time_frame_gt)

    print(f"[INFO] Deleting releases created before: {cutoff_date}")

    while True:
        print(f"[DEBUG] Fetching releases (Page {params['page']})...")
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch releases: {response.status_code} - {response.text}")
            break

        releases = response.json()
        if not releases:
            print("[INFO] No more releases found.")
            break

        for release in releases:
            release_date = datetime.strptime(release["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            release_name = release.get("name") or release.get("tag_name") or "Unnamed Release"

            # Delete releases older than the cutoff timeframe
            if release_date < cutoff_date:
                release_id = release["id"]
                delete_url = f"{url}/{release_id}"

                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 204:
                    print(f"[INFO] Deleted release: {release_name} (Created on: {release_date})")
                    deleted_count += 1
                    if limit and deleted_count >= limit:
                        print(f"[INFO] Reached limit of {limit} deletions.")
                        return
                else:
                    print(f"[ERROR] Failed to delete release: {release_name} (Status: {delete_response.status_code})")
            else:
                print(f"[DEBUG] Skipping release: {release_name} (Created: {release_date}, Cutoff: {cutoff_date})")

        # Check if there are more pages of releases
        if len(releases) < params["per_page"]:
            print("[INFO] No more pages of releases to process.")
            break

        # Increment the page number for the next API call
        params["page"] += 1

    print(f"[INFO] Total deleted releases: {deleted_count}")

def delete_tags(org, repo, token, limit=None):
    """Delete all tags in a repository with pagination, retries, and limit support."""
    url = f"{GITHUB_API_URL}/repos/{org}/{repo}/git/refs/tags"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"per_page": 50, "page": 1}
    deleted_count = 0

    while True:
        response = make_request_with_retries(url, "GET", headers=headers, json=params)
        if response.status_code != 200:
            print(f"Error fetching tags: {response.text}")
            return

        tags = response.json()
        if not tags:
            break

        for tag in tags:
            ref = tag["ref"]
            delete_url = f"{GITHUB_API_URL}/repos/{org}/{repo}/git/{ref}"
            delete_response = make_request_with_retries(delete_url, "DELETE", headers=headers)
            if delete_response.status_code == 204:
                print(f"Deleted tag: {ref}")
                deleted_count += 1
                if limit and deleted_count >= limit:
                    print(f"Reached specified limit of {limit} tags.")
                    return
            else:
                print(f"Failed to delete tag {ref}: {delete_response.text}")

        params["page"] += 1

    print(f"Finished deleting tags. Total deleted: {deleted_count}")

def delete_branches(org, repo, token, limit=None):
    """Delete all branches except main/master, with pagination support."""
    url = f"{GITHUB_API_URL}/repos/{org}/{repo}/branches"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"per_page": 50, "page": 1}
    deleted_count = 0

    while True:
        response = make_request_with_retries(url, "GET", headers=headers, json=params)
        if response.status_code != 200:
            print(f"Error fetching branches: {response.text}")
            return

        branches = response.json()
        if not branches:
            break

        for branch in branches:
            branch_name = branch["name"]
            if branch_name not in EXCLUDED_BRANCHES:
                delete_url = f"{GITHUB_API_URL}/repos/{org}/{repo}/git/refs/heads/{branch_name}"
                delete_response = make_request_with_retries(delete_url, "DELETE", headers=headers)
                if delete_response.status_code == 204:
                    print(f"Deleted branch: {branch_name}")
                    deleted_count += 1
                    if limit and deleted_count >= limit:
                        print(f"Reached specified limit of {limit} branches.")
                        return
                else:
                    print(f"Failed to delete branch {branch_name}: {delete_response.text}")

        params["page"] += 1

    print(f"Finished deleting branches. Total deleted: {deleted_count}")

def close_issues(org, repo, token, limit=None):
    """Close all issues in a repository with optional limit."""
    url = f"{GITHUB_API_URL}/repos/{org}/{repo}/issues"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"state": "open", "per_page": 50, "page": 1}
    closed_count = 0

    while True:
        response = make_request_with_retries(url, "GET", headers=headers)
        if response.status_code != 200:
            print(f"Error fetching issues: {response.text}")
            return

        issues = response.json()
        if not issues:
            break

        for issue in issues:
            issue_number = issue["number"]
            patch_url = f"{url}/{issue_number}"
            patch_response = make_request_with_retries(patch_url, "PATCH", headers=headers, json={"state": "closed"})
            if patch_response.status_code == 200:
                print(f"Closed issue: {issue['title']}")
                closed_count += 1
                if limit and closed_count >= limit:
                    print(f"Reached specified limit of {limit} issues.")
                    return
            else:
                print(f"Failed to close issue {issue['title']}: {patch_response.text}")

        params["page"] += 1

    print(f"Finished closing issues. Total closed: {closed_count}")

# Change Functions
def change_visibility_single(org, repo, visibility, token):
    """Change visibility for a single repository."""
    url = f"{GITHUB_API_URL}/repos/{org}/{repo}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"visibility": visibility}

    response = make_request_with_retries(url, "PATCH", headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Successfully changed visibility of {repo} to {visibility}.")
    else:
        print(f"Failed to change visibility of {repo}: {response.text}")

def change_visibility_all(org, visibility, token):
    """Change visibility for all repositories in an organization."""
    url = f"{GITHUB_API_URL}/orgs/{org}/repos"
    headers = {"Authorization": f"Bearer {token}"}

    response = make_request_with_retries(url, "GET", headers=headers)
    if response.status_code != 200:
        print(f"Error fetching repositories: {response.text}")
        return

    repos = response.json()
    for repo in repos:
        repo_name = repo["name"]
        print(f"Changing visibility for repository: {repo_name}")
        change_visibility_single(org, repo_name, visibility, token)

def change_repository_name(org, repo, new_name, token):
    """Change the name of a repository."""
    url = f"{GITHUB_API_URL}/repos/{org}/{repo}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"name": new_name}

    response = make_request_with_retries(url, "PATCH", headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Successfully changed repository name from {repo} to {new_name}.")
    else:
        print(f"Failed to change repository name: {response.text}")

# Main Function
def main():
    parser = argparse.ArgumentParser(description="GitHub Management Script")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Cleanup subcommand
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup GitHub repository")
    cleanup_parser.add_argument("--org", required=True, help="GitHub organization name")
    cleanup_parser.add_argument("--repo", required=True, help="GitHub repository name")
    cleanup_parser.add_argument("--type", choices=["releases", "tags", "branches", "issues"], help="Type of cleanup")
    cleanup_parser.add_argument("--time-frame-gt", help="Keep items created after this timeframe (e.g., '1m', '30d', '24h')")
    cleanup_parser.add_argument("--limit", type=int, help="Limit the number of items to clean up")
    cleanup_parser.add_argument("--token", required=True, help="GitHub personal access token")

    # Change subcommand
    change_parser = subparsers.add_parser("change", help="Modify GitHub repository settings")
    change_parser.add_argument("--org", required=True, help="GitHub organization name")
    change_parser.add_argument("--repo", help="GitHub repository name (target a single repository)")
    change_parser.add_argument("--all-repos", action="store_true", help="Change visibility for all repositories in the organization")
    change_parser.add_argument("--visibility", choices=["private", "public", "internal"], help="New visibility for the repository/repositories")
    change_parser.add_argument("--change-name", help="New name for the repository")
    change_parser.add_argument("--token", required=True, help="GitHub personal access token")

    args = parser.parse_args()

    if args.command == "cleanup":
        if args.type == "releases":
            delete_releases(args.org, args.repo, args.token, limit=args.limit, time_frame_gt=args.time_frame_gt)
        elif args.type == "tags":
            delete_tags(args.org, args.repo, args.token, limit=args.limit)
        elif args.type == "branches":
            delete_branches(args.org, args.repo, args.token, limit=args.limit)
        elif args.type == "issues":
            close_issues(args.org, args.repo, args.token, limit=args.limit)
        else:
            print("Please specify a valid --type")

    elif args.command == "change":
        if args.change_name:
            if not args.repo:
                print("Error: --repo must be specified when using --change-name.")
            else:
                change_repository_name(args.org, args.repo, args.change_name, args.token)
        elif args.all_repos:
            if args.visibility:
                change_visibility_all(args.org, args.visibility, args.token)
            else:
                print("Error: --visibility must be specified when using --all-repos.")
        elif args.repo:
            if args.visibility:
                change_visibility_single(args.org, args.repo, args.visibility, args.token)
            else:
                print("Error: You must specify either --visibility or --change-name for the change command.")
        else:
            print("Error: You must specify --repo, --all-repos, or --change-name for the change command.")

if __name__ == "__main__":
    main()
