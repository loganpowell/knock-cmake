import os
import shutil
import yaml
import pulumi
import subprocess
from typing import Tuple


def get_github_repository() -> Tuple[str, str, str]:
    """
    Get GitHub repository information dynamically.

    Tries multiple sources in this order:
    1. GITHUB_REPOSITORY environment variable (set by GitHub Actions)
    2. Git remote URL (when running locally)
    3. Fallback to loganpowell/knock-lambda

    Returns:
        Tuple[str, str, str]: (GITHUB_REPOSITORY, GITHUB_ORG, GITHUB_REPO)
        Example: ("loganpowell/knock-lambda", "loganpowell", "knock-lambda")
    """
    # Try environment variable first (GitHub Actions sets this)
    github_repository = os.environ.get("GITHUB_REPOSITORY")

    if not github_repository:
        # Try to get from git remote when running locally
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True,
            )
            git_url = result.stdout.strip()

            # Extract org/repo from GitHub URL (supports both HTTPS and SSH)
            if "github.com" in git_url:
                if git_url.startswith("git@"):
                    # SSH: git@github.com:loganpowell/knock-lambda.git
                    repo_part = git_url.split(":")[-1].replace(".git", "")
                else:
                    # HTTPS: https://github.com/loganpowell/knock-lambda.git
                    repo_part = git_url.split("github.com/")[-1].replace(".git", "")
                github_repository = repo_part
        except Exception:
            # Fallback - will need to be set manually
            github_repository = "loganpowell/knock-lambda"
            pulumi.log.warn(
                f"Could not determine GitHub repository, using fallback: {github_repository}"
            )

    # Parse organization and repository name
    if github_repository and "/" in github_repository:
        github_org, github_repo = github_repository.split("/", 1)
    else:
        github_org, github_repo = "loganpowell", "knock-lambda"
        github_repository = f"{github_org}/{github_repo}"
        pulumi.log.warn(
            f"Could not parse GitHub repository, using fallback: {github_repository}"
        )

    return github_repository, github_org, github_repo


def get_shell_command():
    """
    Detect the appropriate shell for executing scripts in a cross-platform way.

    Returns:
        str: The shell command to use ('bash', 'sh', or 'C:\\Program Files\\Git\\bin\\bash.exe')

    Priority:
    1. bash (most common on Unix/Linux/macOS and Git Bash on Windows)
    2. sh (POSIX shell, widely available)
    3. Git Bash on Windows (C:\\Program Files\\Git\\bin\\bash.exe)

    Raises:
        RuntimeError: If no compatible shell is found
    """
    # Try to find bash first (preferred)
    bash_path = shutil.which("bash")
    if bash_path:
        return bash_path

    # Fall back to sh (POSIX shell)
    sh_path = shutil.which("sh")
    if sh_path:
        return sh_path

    # On Windows, try common Git Bash locations
    if os.name == "nt":
        git_bash_paths = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Git\bin\bash.exe"),
        ]
        for path in git_bash_paths:
            if os.path.exists(path):
                return f'"{path}"'  # Quote path for spaces

    raise RuntimeError(
        "No compatible shell found. Please install bash, sh, or Git for Windows."
    )


# YAML validation function
def validate_buildspec_yaml(buildspec_content):
    """Validate buildspec YAML before using it"""
    try:
        # Try to parse as YAML

        parsed = yaml.safe_load(buildspec_content)

        # Basic structure validation
        if not isinstance(parsed, dict):
            raise ValueError("Buildspec must be a dictionary")

        if "version" not in parsed:
            raise ValueError("Buildspec must have 'version' field")

        if "phases" not in parsed:
            raise ValueError("Buildspec must have 'phases' field")

        # Validate phases structure
        phases = parsed["phases"]
        if not isinstance(phases, dict):
            raise ValueError("'phases' must be a dictionary")

        for phase_name, phase_content in phases.items():
            if not isinstance(phase_content, dict):
                raise ValueError(f"Phase '{phase_name}' must be a dictionary")

            if "commands" in phase_content:
                commands = phase_content["commands"]
                if not isinstance(commands, list):
                    raise ValueError(f"Commands in phase '{phase_name}' must be a list")

                for i, cmd in enumerate(commands):
                    if not isinstance(cmd, str):
                        raise ValueError(
                            f"Command {i} in phase '{phase_name}' must be a string, got {type(cmd)}: {cmd}"
                        )

        print("✅ Buildspec YAML validation passed")
        return True

    except ImportError:
        print("⚠️ PyYAML not available, skipping validation")
        return True
    except Exception as e:
        pulumi.log.error(f"❌ Buildspec YAML validation failed: {e}")
        raise e


def get_validated_buildspec():
    """Load and validate the buildspec YAML from file"""

    # Path to the buildspec file
    buildspec_path = os.path.join(os.path.dirname(__file__), "buildspec.yml")

    try:
        with open(buildspec_path, "r") as f:
            buildspec_content = f.read()

        # Validate the buildspec
        validate_buildspec_yaml(buildspec_content)
        return buildspec_content

    except FileNotFoundError:
        raise FileNotFoundError(f"Buildspec file not found at: {buildspec_path}")
    except Exception as e:
        raise Exception(f"Failed to load buildspec: {e}")
