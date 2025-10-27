#!/usr/bin/env python3
"""
Comprehensive setup script for knock-lambda development environment.

This script sets up Pulumi ESC (Environment, Secrets, and Configuration) as the primary
source of truth for:
1. Pulumi ESC environment for centralized configuration
2. Local development environment variables
3. Git hooks for development workflow
4. Optional GitHub secrets for CI/CD (if needed)

Security Model:
- Pulumi ESC is the source of truth for environment configuration
- Local development uses ESC environment
- GitHub Actions can use ESC or GitHub secrets (configurable)
- No local .env files with secrets (security risk)

Usage:
    uv run setup
"""

import json
import os
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple
import shutil


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


def print_step(step: str, text: str) -> None:
    """Print a formatted step."""
    print(f"{Colors.BLUE}{Colors.BOLD}{step} {text}{Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def run_command(
    cmd: list, check: bool = True, capture: bool = False
) -> Tuple[int, str]:
    """Run a shell command and return exit code and output."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.returncode, result.stdout.strip()
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, ""
    except subprocess.CalledProcessError as e:
        return e.returncode, str(e)
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


def get_shell_command() -> str:
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


def source_platform_compat() -> None:
    """Source the platform compatibility script to set up cross-platform environment."""
    repo_root = Path(__file__).parent.parent
    platform_script = repo_root / "scripts" / "platform-compat.sh"

    if platform_script.exists():
        # Source the platform compatibility script
        # This sets up PLATFORM, PATH_SEP, and other cross-platform variables
        try:
            # Use cross-platform shell detection
            shell_cmd = get_shell_command()
            result = subprocess.run(
                [shell_cmd, "-c", f"source '{platform_script}' && env"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse environment variables from the sourced script
            for line in result.stdout.split("\n"):
                if "=" in line and not line.startswith("_"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value

            print_success("Platform compatibility environment loaded")
        except subprocess.CalledProcessError as e:
            print_warning(f"Could not source platform-compat.sh: {e}")
        except RuntimeError as e:
            print_warning(f"Shell detection failed: {e}")
            print_warning("Skipping platform compatibility setup")
    else:
        print_warning("platform-compat.sh not found - using default environment")


class PulumiESCManager:
    """Manage Pulumi ESC environment as the primary configuration source."""

    def __init__(
        self, 
        organization: str = "default", 
        environment_name: str = "knock-lambda-esc"
    ):
        self.organization = organization
        self.environment_name = environment_name
        self.full_env_name = f"{organization}/{environment_name}"
        self.secrets = {}

    def check_esc_cli(self) -> bool:
        """Check if ESC CLI is installed and user is authenticated with Pulumi."""
        # Check for ESC CLI
        if not check_command_exists("esc"):
            print_error("Pulumi ESC CLI is required for this setup")
            print("Install from: https://www.pulumi.com/docs/esc/cli/download-install/")
            print("Or run: curl -fsSL https://get.pulumi.com/esc/install.sh | sh")
            return False

        # Check for Pulumi CLI
        if not check_command_exists("pulumi"):
            print_error("Pulumi CLI is required for this setup")
            print("Install from: https://www.pulumi.com/docs/install/")
            return False

        # Check authentication
        code, _ = run_command(["pulumi", "whoami"], check=False)
        if code != 0:
            print_error("Not authenticated with Pulumi Cloud")
            print("Run: pulumi login")
            return False

        return True

    def check_existing_environment(self) -> bool:
        """Check if the ESC environment already exists."""
        code, _ = run_command(
            ["esc", "env", "get", self.full_env_name], check=False, capture=True
        )
        return code == 0

    def create_environment(self) -> bool:
        """Create a new ESC environment."""
        code, _ = run_command(["esc", "env", "init", self.full_env_name], check=False)
        if code == 0:
            print_success(f"Created ESC environment: {self.full_env_name}")
            return True
        else:
            print_error(f"Failed to create ESC environment: {self.full_env_name}")
            return False

    def get_current_values(self) -> Dict[str, str]:
        """Get current values from ESC environment."""
        if not self.check_existing_environment():
            return {}

        code, output = run_command(
            ["esc", "env", "open", self.full_env_name], check=False, capture=True
        )
        if code == 0:
            try:
                env_data = json.loads(output)
                env_vars = env_data.get("environmentVariables", {})
                return env_vars
            except json.JSONDecodeError:
                print_warning("Could not parse ESC environment output")
                return {}
        else:
            print_warning("Could not retrieve current ESC environment values")
            return {}

    def prompt_for_configuration(self) -> Dict[str, str]:
        """Check existing configuration and prompt for any missing values."""
        required_config = {
            "AWS_REGION": {
                "description": "AWS region for deployment (single region)",
                "default": "us-east-2",
                "instructions": [
                    "1. Choose a single AWS region for deployment",
                    "2. Common regions: us-east-1, us-east-2, us-west-1, us-west-2, eu-west-1, etc.",
                    "3. Recommend: us-east-2 (good balance of services and cost)",
                ],
            },
            "DOCKER_HUB_USERNAME": {
                "description": "Docker Hub username for ECR pull-through cache",
                "default": "your-username-here",
                "instructions": [
                    "1. Go to https://hub.docker.com/",
                    "2. Sign in or create account",
                    "3. Your username is shown in the top-right corner",
                    "4. You can use placeholder 'your-username-here' and update later",
                ],
            },
            "DOCKER_HUB_TOKEN": {
                "description": "Docker Hub access token for ECR pull-through cache",
                "default": "your-token-here",
                "instructions": [
                    "1. Go to https://hub.docker.com/settings/security",
                    "2. Click 'New Access Token'",
                    "3. Enter description: 'knock-lambda ECR cache'",
                    "4. Select permissions: 'Public Repo Read'",
                    "5. Copy the generated token (starts with 'dckr_pat_')",
                    "6. You can use placeholder 'your-token-here' and update later",
                ],
            },
        }

        print_step("1️⃣", "Pulumi ESC Environment Configuration")

        # Check if environment exists
        if not self.check_existing_environment():
            print(
                f"\n📋 ESC environment '{self.full_env_name}' does not exist. Creating..."
            )
            if not self.create_environment():
                return {}
        else:
            print(f"\n📋 ESC environment '{self.full_env_name}' found.")

        # Load current values
        current_values = self.get_current_values()

        if current_values:
            print("\n✅ Current environment variables:")
            for key, value in current_values.items():
                # Mask sensitive values
                if "TOKEN" in key or "SECRET" in key or "KEY" in key:
                    display_value = (
                        "***" if value and value != "your-token-here" else value
                    )
                else:
                    display_value = value
                print(f"  ✓ {key}: {display_value}")
        else:
            print("\n📝 No current environment variables found.")

        # Check for missing or placeholder values
        missing_config = []
        for config_name, config_info in required_config.items():
            current_value = current_values.get(config_name, "")
            default_value = config_info["default"]

            # Consider it missing if not set or still using placeholder
            if not current_value or current_value == default_value:
                missing_config.append(config_name)

        if not missing_config:
            print_success("All required configuration is set up!")
        else:
            print(
                f"\n📝 Required configuration to update ({len(missing_config)} items):"
            )
            for config in missing_config:
                current_val = current_values.get(config, "not set")
                print(f"  ❌ {config}: {current_val}")

        # Return early if nothing to configure
        if not missing_config:
            return {}

        # Prompt for missing configuration
        config_to_set = {}

        if missing_config:
            print(f"\n🔧 Please provide required configuration values:")
            print("(You can leave values as placeholders and update them later)")

            for config_name in missing_config:
                config_info = required_config[config_name]
                description = config_info["description"]
                default_value = config_info["default"]
                instructions = config_info["instructions"]

                print(f"\n{'='*60}")
                print(f"🔧 {config_name}")
                print(f"📝 {description}")
                print("\n📋 Setup instructions:")
                for i, instruction in enumerate(instructions, 1):
                    print(f"   {instruction}")
                print("=" * 60)

                current_value = current_values.get(config_name, "")
                if current_value:
                    prompt = f"\nCurrent value: {current_value}\nEnter new {config_name} (press Enter to keep current): "
                else:
                    prompt = (
                        f'\nEnter {config_name} (press Enter for "{default_value}"): '
                    )

                value = input(prompt).strip()

                if not value:
                    if current_value:
                        # Keep current value
                        continue
                    else:
                        # Use default
                        value = default_value

                config_to_set[config_name] = value

        return config_to_set
    def set_configuration(self, config_values: Dict[str, str]) -> bool:
        """Set configuration values in the ESC environment."""
        if not config_values:
            print_warning("No configuration to set")
            return True

        print_step("2️⃣", "Updating ESC Environment")

        # Create basic environment configuration YAML
        env_config = {"values": {"environmentVariables": config_values}}

        # Write to temporary file
        import tempfile
        import yaml

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(env_config, f, default_flow_style=False)
                temp_file = f.name

            # Apply configuration to ESC environment
            code, output = run_command(
                ["esc", "env", "edit", self.full_env_name, "-f", temp_file], check=False
            )

            # Clean up temp file
            os.unlink(temp_file)

            if code == 0:
                print_success(f"Updated ESC environment: {self.full_env_name}")

                # Verify the update
                updated_values = self.get_current_values()
                print("\n✅ Updated environment variables:")
                for key, value in updated_values.items():
                    # Mask sensitive values
                    if "TOKEN" in key or "SECRET" in key or "KEY" in key:
                        display_value = (
                            "***" if value and value != "your-token-here" else value
                        )
                    else:
                        display_value = value
                    print(f"  ✓ {key}: {display_value}")

                return True
            else:
                print_error(f"Failed to update ESC environment: {output}")
                return False

        except Exception as e:
            print_error(f"Error updating ESC environment: {e}")
            return False

    def setup_pulumi_integration(self) -> bool:
        """Set up Pulumi to use ESC environment."""
        print_step("3️⃣", "Pulumi ESC Integration")

        # Check Pulumi stack configuration
        # Note: Base stack doesn't use ESC (needs credentials to create OIDC providers first)
        stack_configs = [
            "infrastructure/Pulumi.base.yaml",
            "infrastructure/Pulumi.dev.yaml",
            "infrastructure/Pulumi.main.yaml",
        ]

        for config_file in stack_configs:
            config_path = Path(config_file)
            stack_name = config_file.split(".")[-2]  # Extract stack name (base, dev, main)
            
            if config_path.exists():
                try:
                    import yaml

                    with open(config_path, "r") as f:
                        config_data = yaml.safe_load(f) or {}

                    # Base stack doesn't use ESC (chicken-and-egg problem)
                    if stack_name == "base":
                        print_warning(f"{config_file} - Base stack doesn't use ESC")
                        print("  • Base stack creates the OIDC providers needed for ESC")
                        print("  • Deploy base stack first using local AWS credentials")
                        continue

                    # Check if ESC environment is configured
                    environment = config_data.get("environment", [])
                    if self.full_env_name in environment:
                        print_success(f"{config_file} already configured for ESC")
                    else:
                        print_warning(
                            f"{config_file} not configured for ESC environment"
                        )
                        print(
                            f"  Expected: environment contains '{self.full_env_name}'"
                        )
                        print(f"  Current: {environment}")

                except Exception as e:
                    print_warning(f"Could not read {config_file}: {e}")
            else:
                print_warning(f"{config_file} not found")

        print("\n🔧 ESC Integration Status:")
        print(f"  • ESC Environment: {self.full_env_name}")
        print("  • Stack Architecture:")
        print("    - base:  Shared resources (OIDC, secrets, ECR cache)")
        print("    - dev:   Development environment")
        print("    - main:  Production environment")
        print()
        print("🎯 Stack Creation & Deployment:")
        print()
        print("  # First, create all three stacks (one-time setup):")
        print("  ```")
        print("  pulumi stack init base")
        print("  pulumi stack init dev")
        print("  pulumi stack init main")
        print("  ```")
        print()
        print("  # Then deploy in order:")
        print("  # 1. Deploy base stack FIRST (uses local AWS credentials)")
        print("  ```")
        print("  pulumi stack select base")
        print(f"  esc run {self.full_env_name} -- pulumi up")
        print("  ```")
        print()
        print(f"  # 2. Deploy environment stacks (esc inferred from Pulumi.<stack>.yaml 'environment')")
        print("  ```")
        print("  pulumi stack select dev")
        print(f"  pulumi up")
        print("  ```")
        print()
        print("  ```")
        print("  pulumi stack select main")
        print(f"  pulumi up")
        print("  ```")
        print()
        print("💡 Note: Base stack must be deployed before dev/main stacks")
        print()

        return True


class GitHooksSetup:
    """Handle Git hooks setup."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.hooks_source = repo_root / "scripts" / "git-hooks"
        self.hooks_target = repo_root / ".git" / "hooks"

    def setup_hooks(self) -> None:
        """Set up Git hooks."""
        print_step("4️⃣", "Git Hooks Setup")

        if not self.hooks_source.exists():
            print_warning("Git hooks source directory not found")
            return

        # Install post-checkout hook
        post_checkout_source = self.hooks_source / "post-checkout"
        post_checkout_target = self.hooks_target / "post-checkout"

        if post_checkout_source.exists():
            try:
                shutil.copy2(post_checkout_source, post_checkout_target)
                os.chmod(post_checkout_target, 0o755)
                print_success(
                    "Installed post-checkout hook (auto-switches Pulumi stack on branch change)"
                )
                print("  📋 Hook behavior:")
                print("    • git checkout dev  → pulumi stack select dev")
                print("    • git checkout main → pulumi stack select main")
                print("  💡 Base stack: manually select with 'pulumi stack select base'")
            except Exception as e:
                print_error(f"Failed to install post-checkout hook: {e}")
        else:
            print_warning("post-checkout hook template not found")


def main():
    """Main setup function."""
    repo_root = Path(__file__).parent.parent

    # Set up cross-platform environment
    source_platform_compat()

    print_header("🚀 Knock Lambda Development Environment Setup")

    print("This script will:")
    print("  1️⃣  Set up Pulumi ESC environment for configuration")
    print("  2️⃣  Configure environment variables in ESC")
    print("  3️⃣  Set up Pulumi integration with ESC")
    print("  4️⃣  Install Git hooks for development workflow")
    print()
    print("🔒 Security Model:")
    print("  • Pulumi ESC is the authoritative configuration source")
    print("  • Environment variables managed centrally in ESC")
    print("  • No local .env files with secrets")
    print("  • Access controlled through Pulumi Cloud permissions")
    print("  • Infrastructure automatically loads config from ESC")
    print()

    # Initialize ESC manager
    esc_manager = PulumiESCManager()

    if not esc_manager.check_esc_cli():
        print_error("Required CLIs not available")
        sys.exit(1)

    # Step 1 & 2: Check existing configuration and prompt for missing values
    config_to_set = esc_manager.prompt_for_configuration()

    # Set any missing configuration in ESC
    if config_to_set:
        if not esc_manager.set_configuration(config_to_set):
            print_error("Failed to set ESC configuration")
            sys.exit(1)
    else:
        print_step("2️⃣", "All Configuration Already Set")
        print("✅ No missing configuration found - proceeding with existing setup")

    # Step 3: Pulumi integration
    esc_manager.setup_pulumi_integration()

    # Step 4: Git hooks
    git_hooks = GitHooksSetup(repo_root)
    git_hooks.setup_hooks()

    print_header("🎉 Setup Complete!")

    print("Summary of what was configured:")
    print("  ✅ Pulumi ESC environment set up")
    print("  ✅ Environment variables configured in ESC")
    print("  ✅ Pulumi integration with ESC verified")
    print("  ✅ Git hooks for development workflow")
    print()

    print("🔒 Security Benefits:")
    print("  • All configuration centralized in Pulumi ESC")
    print("  • No local credential files")
    print("  • Access controlled through Pulumi Cloud")
    print("  • Infrastructure automatically loads config from ESC")
    print("  • Easy to share configuration with team members")
    print()

    print("�️  Multi-Stack Architecture:")
    print("  • base:  Shared resources (OIDC providers, secrets, ECR cache)")
    print("  • dev:   Development environment (references base stack)")
    print("  • main:  Production environment (references base stack)")
    print()

    print("🚀 Next steps:")
    print()
    print("  🏗️  First-time setup: Create the three stacks")
    print("    ```")
    print("    pulumi stack init base")
    print("    pulumi stack init dev")
    print("    pulumi stack init main")
    print("    ```")
    print()
    print("  📦 Step 1: Deploy base stack (shared infrastructure)")
    print("    ```")
    print("    pulumi stack select base")
    print(f"    esc run {esc_manager.full_env_name} -- pulumi up --yes")
    print("    ```")
    print()
    print("  🌍 Step 2: Deploy dev stack")
    print("    ```")
    print("    pulumi stack select dev")
    print(f"    pulumi up")
    print("    ```")
    print()
    print("  🌐 Step 3: Deploy main stack")
    print("    ```")
    print("    pulumi stack select main")
    print(f"    pulumi up")
    print("    ```")
    print("💡 Pro Tips:")
    print("  • Base stack must be deployed FIRST (creates shared OIDC providers)")
    print("  • Dev/main stacks reference base stack outputs via StackReference")
    print("  • Update shared resources by updating base stack only")
    print("  • ESC environment is forker-friendly - no GitHub secrets needed!")
    print("  • Update configuration anytime with: esc env edit")
    print("  • Share configuration with team via Pulumi Cloud permissions")
    print()


if __name__ == "__main__":
    main()
