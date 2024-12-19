# GitHub Management Script

This Python script provides functionality to manage GitHub repositories, including cleaning up releases, tags, branches, and issues, as well as modifying repository settings like visibility and name.

## Features

### Cleanup Functionality
- **Delete Releases:** Remove old releases based on a specified timeframe.
- **Delete Tags:** Delete all tags in a repository.
- **Delete Branches:** Delete all branches except the default branches (`main` and `master`).
- **Close Issues:** Close all open issues in a repository.

### Change Functionality
- **Change Repository Visibility:** Modify the visibility of a repository or all repositories in an organization (e.g., private, public, internal).
- **Rename Repository:** Change the name of a single repository.

## Requirements
- Python 3.6+
- `requests` library

Install the `requests` library if not already installed:
```bash
pip install requests
```

## Usage

Run the script with the desired command and arguments. Use `--help` to see the available options for each command.

### Commands

#### Cleanup
Perform cleanup operations on a GitHub repository.

```bash
python3 main.py cleanup --org <organization> --repo <repository> --type <type> --time-frame-gt <timeframe> --limit <number> --token <token>
```

**Arguments:**
- `--org`: GitHub organization name (required).
- `--repo`: GitHub repository name (required).
- `--type`: The type of cleanup to perform (`releases`, `tags`, `branches`, `issues`).
- `--time-frame-gt`: Specify a timeframe (e.g., `1m`, `30d`, `24h`) to keep items created after this period. Applicable for releases.
- `--limit`: Maximum number of items to clean up.
- `--token`: GitHub personal access token (required).

**Examples:**
- Delete releases older than 30 days:
  ```bash
  python3 main.py cleanup --org my-org --repo my-repo --type releases --time-frame-gt 30d --token my-token
  ```
- Delete all tags:
  ```bash
  python3 main.py cleanup --org my-org --repo my-repo --type tags --token my-token
  ```
- Close open issues with a limit of 50:
  ```bash
  python3 main.py cleanup --org my-org --repo my-repo --type issues --limit 50 --token my-token
  ```

#### Change
Modify repository settings like visibility and name.

```bash
python3 main.py change --org <organization> [--repo <repository>] [--all-repos] [--visibility <visibility>] [--change-name <new_name>] --token <token>
```

**Arguments:**
- `--org`: GitHub organization name (required).
- `--repo`: GitHub repository name. Required when renaming a repository.
- `--all-repos`: Apply the change to all repositories in the organization.
- `--visibility`: Change the visibility of the repository/repositories (`private`, `public`, `internal`).
- `--change-name`: New name for the repository.
- `--token`: GitHub personal access token (required).

**Examples:**
- Change visibility of a repository to private:
  ```bash
  python3 main.py change --org my-org --repo my-repo --visibility private --token my-token
  ```
- Rename a repository:
  ```bash
  python3 main.py change --org my-org --repo old-repo-name --change-name new-repo-name --token my-token
  ```
- Change visibility of all repositories in an organization to public:
  ```bash
  python3 main.py change --org my-org --all-repos --visibility public --token my-token
  ```

## Notes
- **Authentication:** Use a GitHub personal access token with the appropriate permissions for the operations you intend to perform.
- **Rate Limiting:** If the script encounters rate limits, it will wait and retry automatically.

## License
This script is open source and available under the MIT License.

