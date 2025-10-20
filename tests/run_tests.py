#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "inquirer",
# ]
# ///
"""Interactive test runner for Knock Lambda tests.

Allows selection of:
- Test files to run
- Specific tests within files
- ACSM files to use
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional

import inquirer


def find_test_files(tests_dir: Path) -> List[Path]:
    """Find all pytest test files."""
    return sorted(tests_dir.glob("test_*.py"))


def extract_tests_from_file(file_path: Path) -> Dict[str, List[str]]:
    """Extract test classes and functions from a test file.
    
    Returns:
        Dict mapping class names to list of test methods.
        Top-level functions are under the key "standalone".
    """
    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=str(file_path))
    
    tests = {"standalone": []}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Found a test class
            class_tests = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                    class_tests.append(item.name)
            
            if class_tests:
                tests[node.name] = class_tests
        
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            # Top-level test function
            if node.col_offset == 0:  # Ensure it's not inside a class
                tests["standalone"].append(node.name)
    
    # Remove standalone key if empty
    if not tests["standalone"]:
        del tests["standalone"]
    
    return tests


def find_acsm_files(project_root: Path) -> List[Path]:
    """Find all ACSM files in assets directory."""
    assets_dir = project_root / "assets"
    if not assets_dir.exists():
        return []
    return sorted(assets_dir.glob("*.acsm"))


def select_test_files(test_files: List[Path]) -> List[Path]:
    """Prompt user to select a single test file or all files."""
    choices = ["All test files"] + [f.name for f in test_files]

    questions = [
        inquirer.List(
            'test_file',
            message="Select test file - arrows to move, ENTER to confirm",
            choices=choices,
            default="All test files",
        ),
    ]

    answers = inquirer.prompt(questions)
    if not answers or not answers['test_file']:
        print("❌ No test file selected")
        sys.exit(0)

    selection = answers['test_file']

    # If "All test files" is selected, return all
    if selection == "All test files":
        return test_files

    # Return the single selected file
    return [next(f for f in test_files if f.name == selection)]


def select_specific_tests(test_file: Path, tests: Dict[str, List[str]]) -> Optional[List[str]]:
    """Prompt user to select specific tests from a file.
    
    Returns:
        List of test specifiers (e.g., ["ClassName::test_name", ...])
        or None if all tests in the file should be run.
    """
    # Build choices
    choices = []
    choice_map = {}  # Display name -> test specifier
    
    for class_or_standalone, test_names in tests.items():
        if class_or_standalone == "standalone":
            for test_name in test_names:
                display = f"  {test_name}"
                choices.append(display)
                choice_map[display] = test_name
        else:
            # Add class header (visual separator)
            header = f"--- {class_or_standalone} ---"
            choices.append(header)
            for test_name in test_names:
                display = f"  {class_or_standalone}::{test_name}"
                choices.append(display)
                choice_map[display] = f"{class_or_standalone}::{test_name}"
    
    # Add "All tests" option at the top
    choices.insert(0, "All tests in this file")
    
    questions = [
        inquirer.Checkbox(
            'tests',
            message=f"Select tests from {test_file.name} - SPACE to toggle, ENTER to confirm",
            choices=choices,
            default=["All tests in this file"]
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not answers:
        return None
    
    selected = answers['tests']
    
    # If "All tests" is selected or nothing selected, return None (run all)
    if not selected or "All tests in this file" in selected:
        return None
    
    # Map display names back to test specifiers
    return [choice_map[choice] for choice in selected if choice in choice_map]


def select_acsm_file(acsm_files: List[Path]) -> Optional[Path]:
    """Prompt user to select an ACSM file (optional)."""
    if not acsm_files:
        print("ℹ️  No ACSM files found in assets/ directory")
        return None
    
    choices = [f.name for f in acsm_files] + ["No ACSM file (use defaults)"]
    
    questions = [
        inquirer.List(
            'acsm_file',
            message="Select ACSM file to use (optional)",
            choices=choices,
            default="No ACSM file (use defaults)"
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not answers or answers['acsm_file'] == "No ACSM file (use defaults)":
        return None
    
    selected_name = answers['acsm_file']
    return next(f for f in acsm_files if f.name == selected_name)


def select_test_markers() -> List[str]:
    """Prompt user to select marker options."""
    questions = [
        inquirer.Checkbox(
            'markers',
            message="Select options - SPACE to toggle, ENTER to confirm",
            choices=[
                ("Skip real ACSM tests (recommended)", "not real_acsm"),
                ("Verbose output (-v)", "verbose"),
                ("Show print statements (-s)", "show_prints"),
            ],
            default=["not real_acsm"]
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not answers:
        return ["not real_acsm"]  # Default
    
    return answers['markers']


def build_pytest_command(
    test_files: List[Path],
    specific_tests: Dict[Path, Optional[List[str]]],
    acsm_file: Optional[Path],
    marker_options: List[str]
) -> List[str]:
    """Build the pytest command."""
    cmd = ["pytest"]
    
    # Add test specifiers
    for test_file in test_files:
        tests = specific_tests.get(test_file)
        if tests is None:
            # Run all tests in file
            cmd.append(str(test_file))
        else:
            # Run specific tests
            for test_spec in tests:
                cmd.append(f"{test_file}::{test_spec}")
    
    # Add marker filters
    if "not real_acsm" in marker_options:
        cmd.extend(["-m", "not real_acsm"])
    
    # Add verbosity
    if "verbose" in marker_options:
        cmd.append("-v")
    
    # Show print statements
    if "show_prints" in marker_options:
        cmd.append("-s")
    
    # Add ACSM file option
    if acsm_file:
        cmd.append(f"--acsm-file={acsm_file.name}")
    
    return cmd


def main():
    """Main interactive test runner."""
    # Get project structure
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("🧪 Knock Lambda Interactive Test Runner\n")
    
    # Step 1: Find test files
    test_files = find_test_files(script_dir)
    if not test_files:
        print("❌ No test files found")
        sys.exit(1)
    
    print(f"📝 Found {len(test_files)} test file(s)\n")
    
    # Step 2: Select test files
    selected_files = select_test_files(test_files)
    print(f"\n✅ Selected {len(selected_files)} file(s)")
    
    # Step 3: Select specific tests (if single file selected)
    specific_tests = {}
    if len(selected_files) == 1:
        test_file = selected_files[0]
        tests = extract_tests_from_file(test_file)
        
        print(f"\n📋 Found {sum(len(v) for v in tests.values())} test(s) in {test_file.name}")
        
        selected = select_specific_tests(test_file, tests)
        specific_tests[test_file] = selected
        
        if selected:
            print(f"\n✅ Selected {len(selected)} specific test(s)")
        else:
            print(f"\n✅ Will run all tests in {test_file.name}")
    else:
        # Multiple files - run all tests in each
        for f in selected_files:
            specific_tests[f] = None
    
    # Step 4: Select ACSM file
    print()
    acsm_files = find_acsm_files(project_root)
    acsm_file = select_acsm_file(acsm_files)
    if acsm_file:
        print(f"\n✅ Using ACSM file: {acsm_file.name}")
    
    # Step 5: Select marker options
    print()
    marker_options = select_test_markers()
    
    # Build command
    cmd = build_pytest_command(selected_files, specific_tests, acsm_file, marker_options)
    
    # Display and confirm
    print("\n" + "="*70)
    print("🚀 Ready to run pytest with the following command:")
    print("="*70)
    print(f"\n  {' '.join(cmd)}\n")
    print("="*70)
    
    questions = [
        inquirer.Confirm(
            'confirm',
            message="Run tests now?",
            default=True
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not answers or not answers['confirm']:
        print("\n❌ Test run cancelled")
        sys.exit(0)
    
    # Run pytest
    print("\n" + "="*70)
    print("🧪 Running tests...")
    print("="*70 + "\n")
    
    try:
        result = subprocess.run(cmd, cwd=script_dir)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n❌ Test run interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
