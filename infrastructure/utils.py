import os
import shutil
import yaml
import pulumi


def get_esc_docker_hub_key():
    """
    Get the values.aws.secrets.dockerHub.fn::open::aws-secrets.get.secretId from
    infrastructure/esc-environment.yaml
    Returns:
        str: The Docker Hub credentials secret ID from Pulumi ESC environment
    Raises:
        FileNotFoundError: If the esc-environment.yaml file is not found
        Exception: If the file cannot be parsed or the secret ID is not found
    """
    # grab the file using file system
    esc_env_path = os.path.join(os.path.dirname(__file__), "esc-environment.yaml")
    try:
        with open(esc_env_path, "r") as f:
            esc_env_content = f.read()

        esc_env = yaml.safe_load(esc_env_content)

        secret_id = (
            esc_env.get("values", {})
            .get("aws", {})
            .get("secrets", {})
            .get("dockerHub", {})
            .get("fn::open::aws-secrets", {})
            .get("get", {})
            .get("secretId")
        )

        if not secret_id:
            raise ValueError("Docker Hub secret ID not found in esc-environment.yaml")

        return secret_id
    except FileNotFoundError:
        raise FileNotFoundError(f"ESC environment file not found at: {esc_env_path}")
    except Exception as e:
        raise Exception(f"Failed to load ESC environment: {e}")


# test
# print(get_esc_docker_hub_credentials())


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
