#!/usr/bin/env python3

"""
Simplified build script for Lambda container builds.
Uses local source dependencies from deps/ directory - no network required.
"""

import os
import shutil
import subprocess
from subprocess import run, CalledProcessError
from pathlib import Path
import sys

# Build configuration
SOURCE_DIR = Path(__file__).resolve().parent
BUILD_DIR = Path(f"{SOURCE_DIR}/~build")
INSTALL_DIR = Path(f"{SOURCE_DIR}/build-output")
libgourou_DIR = Path(f"{SOURCE_DIR}/deps/libgourou")
updfparser_DIR = Path(f"{SOURCE_DIR}/deps/uPDFParser")
knock_DIR = Path(f"{SOURCE_DIR}/knock")


def run_cmd(cmd, cwd=None, check=True):
    """Run a command with proper error handling"""
    print(f"Running: {' '.join(str(c) for c in cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")

    try:
        result = run(cmd, cwd=cwd, check=check, capture_output=False, text=True)
        return result
    except CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}")
        print(f"Command: {' '.join(str(c) for c in cmd)}")
        sys.exit(1)


def check_binary_dependency(name: str, critical=True) -> bool:
    """Check if a binary is available in PATH"""
    try:
        proc = run([name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        if not critical:
            return False
        raise RuntimeError(f"This script needs `{name}`, but `{name}` is not found.")
    return True


def rmdir_if_exist(path):
    """Remove directory if it exists"""
    if Path(path).exists():
        shutil.rmtree(path)


def clean():
    """Clean build artifacts"""
    rmdir_if_exist(BUILD_DIR)
    rmdir_if_exist(INSTALL_DIR)


def verify_sources():
    """Verify all required source directories exist"""
    print("Verifying source directories...")
    
    required_dirs = {
        "libgourou": libgourou_DIR,
        "uPDFParser": updfparser_DIR,
        "knock": knock_DIR,
    }
    
    for name, path in required_dirs.items():
        if not path.exists():
            print(f"ERROR: {name} source directory not found at {path}")
            print(f"\nIf deps/ directory is empty, extract sources with:")
            print(f"  mkdir -p deps")
            print(f"  tar -xzf assets/sources/libgourou.tar.gz -C deps/")
            print(f"  tar -xzf assets/sources/uPDFParser.tar.gz -C deps/")
            sys.exit(1)
        
        # Check for CMakeLists.txt
        cmake_file = path / "CMakeLists.txt"
        if not cmake_file.exists():
            print(f"ERROR: CMakeLists.txt not found in {path}")
            print(f"\nCopy build configuration with:")
            print(f"  cp config/{name}/CMakeLists.txt {path}/")
            sys.exit(1)
    
    print("✓ All source directories verified")


def main():
    print("=" * 60)
    print("Knock Container Build - Using Local Sources")
    print("=" * 60)

    # Verify cmake version
    cmake_version = run(["cmake", "--version"], capture_output=True, text=True)
    print(f"\nCMake version: {cmake_version.stdout.splitlines()[0]}")

    # Verify build tools
    print("\nChecking build dependencies...")
    check_binary_dependency("cmake")
    print("✓ cmake found")

    # Verify source directories exist
    verify_sources()

    # Clean old build artifacts
    print("\nCleaning old build artifacts...")
    clean()
    print("✓ Clean completed")

    # Build configuration
    build_type = os.environ.get('CMAKE_BUILD_TYPE', 'Release')
    print(f"\nBuild type: {build_type}")
    
    cxx_flags = "-g -fno-omit-frame-pointer"
    if build_type == "Debug":
        cxx_flags += " -O0 -DDEBUG"
        print("🔍 Debug mode enabled")
    else:
        cxx_flags += " -O2"

    # CMake configure
    print("\n" + "=" * 60)
    print("CONFIGURING BUILD")
    print("=" * 60)
    
    cmake_cmd = [
        "cmake",
        "-S", ".",
        "-B", str(BUILD_DIR),
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DCMAKE_CXX_FLAGS={cxx_flags}",
        f"-DCMAKE_C_FLAGS={cxx_flags}",
        "-DBUILD_STATIC=OFF",  # Use dynamic linking for Lambda container
        "-DBUILD_SHARED=ON",
    ]
    
    run_cmd(cmake_cmd, cwd=SOURCE_DIR)
    print("✓ CMake configure completed")

    # CMake build
    print("\n" + "=" * 60)
    print("BUILDING")
    print("=" * 60)
    
    build_cmd = [
        "cmake",
        "--build", str(BUILD_DIR),
        "--config", "Release",
        "--verbose"
    ]

    # Add parallel jobs if cmake version supports it (3.12+)
    cmake_version_output = run(["cmake", "--version"], capture_output=True, text=True)
    if "cmake version 3." in cmake_version_output.stdout:
        version_line = cmake_version_output.stdout.splitlines()[0]
        version_str = version_line.split("cmake version ")[1].split()[0]
        major, minor = version_str.split(".")[:2]
        if int(major) >= 3 and int(minor) >= 12:
            cpu_count = os.cpu_count() or 1
            build_cmd.extend(["-j", str(cpu_count)])
            print(f"Using {cpu_count} parallel jobs")

    run_cmd(build_cmd, cwd=SOURCE_DIR)
    print("✓ Build completed")

    # CMake install
    print("\n" + "=" * 60)
    print(f"INSTALLING TO: {INSTALL_DIR}")
    print("=" * 60)
    
    run_cmd(["cmake", "--install", str(BUILD_DIR), "--verbose"], cwd=SOURCE_DIR)
    print("✓ Install completed")

    # Verify binary
    binary_path = INSTALL_DIR / "knock"
    print(f"\nVerifying binary at: {binary_path}")
    
    if not binary_path.exists():
        print("\n" + "=" * 60)
        print(f"ERROR: Binary not found at {binary_path}")
        print("=" * 60)
        
        if INSTALL_DIR.exists():
            print(f"\nContents of {INSTALL_DIR}:")
            for item in INSTALL_DIR.iterdir():
                print(f"  {item}")
        
        sys.exit(1)

    # Check binary properties
    print("\nBinary information:")
    run(["ls", "-lh", str(binary_path)])
    run(["file", str(binary_path)])
    
    print("\n" + "=" * 60)
    print("✅ BUILD SUCCESSFUL")
    print("=" * 60)
    print(f"\nKnock binary: {binary_path}")
    
    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBuild failed with error: {e}")
        sys.exit(1)
