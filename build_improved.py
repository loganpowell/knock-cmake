#!/usr/bin/env python3

"""
Improved build.py with proper error handling for Lambda container builds
"""

import os
import shutil
import subprocess
from subprocess import run, CalledProcessError
from pathlib import Path
from typing import Optional
import sys

# default build config directories
SOURCE_DIR = Path(__file__).resolve().parent
BUILD_DIR = Path(f"{SOURCE_DIR}/~build")
CHECKOUT_DIR = Path(f"{SOURCE_DIR}/~checkout")
INSTALL_DIR = Path(f"{SOURCE_DIR}/build-output")
libgourou_DIR = Path(f"{CHECKOUT_DIR}/libgourou")
updfparser_DIR = Path(f"{CHECKOUT_DIR}/uPDFParser")
knock_DIR = Path(f"{SOURCE_DIR}/knock")


def run_cmd(cmd, cwd=None, check=True):
    """Run a command with proper error handling"""
    print(f"Running: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")

    try:
        result = run(cmd, cwd=cwd, check=check, capture_output=False, text=True)
        return result
    except CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}")
        print(f"Command: {' '.join(cmd)}")
        sys.exit(1)


def check_binary_dependency(name: str, critical=True) -> bool:
    try:
        proc = run(name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        if not critical:
            return False
        raise RuntimeError(f"This script needs `{name}`, but `{name}` is not found.")
    return True


def extract_source_archive(archive_name: str, outputDir: Path) -> bool:
    """Extract source code from a tar.gz archive instead of git cloning"""
    outputDir = Path(outputDir)
    
    # Check if directory already exists and has content
    if outputDir.exists() and any(outputDir.iterdir()):
        print(f"Directory {outputDir} already exists with content, skipping extraction")
        if (outputDir / "CMakeLists.txt").exists():
            print(f"✓ Found CMakeLists.txt in {outputDir}, source appears valid")
            return True
        else:
            print(f"⚠️ Directory exists but CMakeLists.txt not found, proceeding with extraction")
    
    # Path to the source archive
    source_archive = SOURCE_DIR / "assets" / "sources" / f"{archive_name}.tar.gz"
    
    if not source_archive.exists():
        print(f"ERROR: Source archive not found: {source_archive}")
        return False
    
    # Create parent directory if it doesn't exist
    outputDir.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting {archive_name} from archive: {source_archive}")
    print(f"Target directory: {outputDir}")
    
    # Extract the archive
    cmd = ["tar", "-xzf", str(source_archive), "-C", str(outputDir.parent)]
    run_cmd(cmd)
    
    # Verify extraction worked
    if not outputDir.exists() or not any(outputDir.iterdir()):
        print(f"ERROR: Extraction failed - {outputDir} is empty or doesn't exist")
        return False
    
    if not (outputDir / "CMakeLists.txt").exists():
        print(f"ERROR: CMakeLists.txt not found after extraction in {outputDir}")
        return False
    
    print(f"✓ Successfully extracted {archive_name}")
    return True


def get_git_repo(
    repoPath: str,
    outputDir: Path,
    tag: Optional[str] = None,
    commitHash: Optional[str] = None,
) -> bool:
    """Legacy function - now uses source archives instead of git"""
    outputDir = Path(outputDir)
    
    # Determine which archive to use based on the repo path
    if "libgourou" in repoPath:
        return extract_source_archive("libgourou", outputDir)
    elif "uPDFParser" in repoPath:
        return extract_source_archive("uPDFParser", outputDir)
    else:
        print(f"ERROR: Unknown repository: {repoPath}")
        return False


def cp(sourcePath: Path, targetPath: Path, copyContents: bool = False):
    sourcePath = Path(sourcePath).resolve()
    targetPath = Path(targetPath).absolute()
    if sourcePath.is_file():
        shutil.copyfile(sourcePath, targetPath)
    elif sourcePath.is_dir() and copyContents:
        shutil.copytree(sourcePath, targetPath, dirs_exist_ok=True)
    elif sourcePath.is_dir() and not copyContents:
        newTarget = Path(f"{targetPath}/{sourcePath.name}")
        if not newTarget.exists():
            os.mkdir(newTarget)
        shutil.copytree(sourcePath, newTarget, dirs_exist_ok=True)


def rmdir_if_exist(path):
    if Path(path).exists():
        shutil.rmtree(path)


def clean():
    rmdir_if_exist(CHECKOUT_DIR)
    rmdir_if_exist(BUILD_DIR)
    rmdir_if_exist(INSTALL_DIR)


def main():
    print("Starting build process...")

    # Verify cmake version
    cmake_version = run(["cmake", "--version"], capture_output=True, text=True)
    print(f"CMake version: {cmake_version.stdout.splitlines()[0]}")

    # clean repo of old build artifacts
    print("Cleaning old build artifacts...")
    clean()
    print("✓ Clean completed")

    print("Checking binary dependencies...")

    print("Checking for git...")
    check_binary_dependency("git")
    print("✓ git found")

    print("Checking for cmake...")
    check_binary_dependency("cmake")
    print("✓ cmake found")

    print("Cloning libgourou repository...")
    get_git_repo(
        "https://forge.soutade.fr/soutade/libgourou",
        libgourou_DIR,
        "master",
        None,  # Use latest master instead of specific commit
    )
    print("✓ libgourou cloned")

    print("Cloning uPDFParser repository...")
    get_git_repo(
        "https://forge.soutade.fr/soutade/uPDFParser",
        updfparser_DIR,
        "master",
        None,  # Use latest master instead of specific commit
    )
    print("✓ uPDFParser cloned")

    # copy the needed build configuration files
    print("Copying configuration files...")
    cp(Path(f"{SOURCE_DIR}/config/libgourou/"), libgourou_DIR, True)
    cp(Path(f"{SOURCE_DIR}/config/uPDFParser"), updfparser_DIR, True)
    print("✓ Configuration files copied")

    # run cmake configure and build commands with proper error handling
    print("Running cmake configure...")
    cmake_cmd = [
        "cmake",
        "-S",
        ".",
        "-B",
        str(BUILD_DIR),
        "-DOPENSSL_ROOT_DIR=/usr",
        "-DOPENSSL_LIBRARIES=/usr/lib64/libssl.so;/usr/lib64/libcrypto.so",
        "-DOPENSSL_INCLUDE_DIR=/usr/include",
        "-DOPENSSL_SSL_LIBRARY=/usr/lib64/libssl.so",
        "-DOPENSSL_CRYPTO_LIBRARY=/usr/lib64/libcrypto.so",
    ]
    run_cmd(cmake_cmd, cwd=SOURCE_DIR)
    print("✓ cmake configure completed")

    print("Running cmake build...")
    # Check cmake version to determine if -j is supported
    cmake_version_output = run(["cmake", "--version"], capture_output=True, text=True)
    cmake_version_line = cmake_version_output.stdout.splitlines()[0]
    print(f"Using cmake: {cmake_version_line}")

    # Use older cmake syntax if needed
    build_cmd = ["cmake", "--build", str(BUILD_DIR), "--config", "Release"]

    # Only add -j flag if cmake version supports it (3.12+)
    if "cmake version 3." in cmake_version_line:
        version_str = cmake_version_line.split("cmake version ")[1].split()[0]
        major, minor = version_str.split(".")[:2]
        if int(major) >= 3 and int(minor) >= 12:
            build_cmd.extend(["-j", str(os.cpu_count())])

    run_cmd(build_cmd, cwd=SOURCE_DIR)
    print("✓ cmake build completed")

    print("Running cmake install...")
    run_cmd(["cmake", "--install", str(BUILD_DIR)], cwd=SOURCE_DIR)
    print("✓ cmake install completed")

    # Verify the binary was created
    binary_path = INSTALL_DIR / "knock"
    if not binary_path.exists():
        print(f"ERROR: Binary not found at {binary_path}")
        print(f"Contents of {INSTALL_DIR}:")
        if INSTALL_DIR.exists():
            for item in INSTALL_DIR.iterdir():
                print(f"  {item}")
        else:
            print(f"  Directory {INSTALL_DIR} does not exist")
        sys.exit(1)

    print(
        f"✓ Build finished successfully, knock binary located at: {INSTALL_DIR}/knock"
    )
    return True


if __name__ == "__main__":
    main()
