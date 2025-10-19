# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

knock-cmake is a CMake-based build system for the Knock ACSM-to-PDF/EPUB converter. It enables cross-platform compilation of Knock on Linux (and Windows WSL) across various processor architectures, replacing the original Nix-based build system.

## Architecture

This is a multi-component C++ project with a complex dependency chain:

- **knock**: Main application (C++) that converts ACSM files
- **libgourou**: Core DRM processing library 
- **uPDFParser**: PDF parsing library (dependency of libgourou)

The build system uses a hierarchical CMake structure where the top-level CMakeLists.txt orchestrates building all components in dependency order.

## Build System Commands

### Primary Build Command
```bash
python3 build.py
```
- Handles complete build process including dependency management
- Requires root privileges on apt-based systems for automatic dependency installation
- Generates binary at `./knock/knock`

### Manual Build Process (if Python unavailable)
```bash
# Install dependencies (Ubuntu/Debian)
sudo apt install build-essential git cmake libssl-dev libcurl4-openssl-dev zlib1g-dev -y

# Create checkout directory and clone dependencies
mkdir ~checkout
cd ~checkout
git clone https://forge.soutade.fr/soutade/libgourou.git -b master
git clone https://forge.soutade.fr/soutade/uPDFParser -b master  
git clone https://github.com/Alvin-He/knock-cmake -b knock-base-release-79

# Reset to specific commits (as defined in build.py)
cd libgourou && git reset --hard 81faf1f9bef4d27d8659f2f16b9c65df227ee3d7
cd ../uPDFParser && git reset --hard 6060d123441a06df699eb275ae5ffdd50409b8f3
cd ../knock-cmake && git reset --hard 0aa4005fd4f2ee1b41c20643017c8f0a2bdf6262

# Copy configuration files
cp -r config/libgourou/* ~checkout/libgourou/
cp -r config/uPDFParser/* ~checkout/uPDFParser/
cp -r config/knock/* ~checkout/knock-cmake/

# Build with CMake
cmake -S . -B ~build
cmake --build ~build --config Release -j$(nproc)
cmake --install ~build
```

### Clean Build
```bash
# The build.py script automatically cleans before building
# Manual cleanup:
rm -rf ~build ~checkout knock
```

## Key Build Configuration

- **Static linking**: Builds static binaries by default for portability
- **Version tracking**: Currently tracks Knock version 79 (3.0.79)
- **Install location**: `./knock/knock` (relative to project root)
- **Upstream fork**: Uses Alvin-He's fork since original BentonEdmondson repo is offline

## Dependencies

### Build-time Dependencies
- build-essential (gcc, g++, make)
- git, cmake
- libssl-dev, libcurl4-openssl-dev, zlib1g-dev

### Runtime Dependencies (for binaries built by this system)
- libcurl, libopenssl, zlib
- Note: Official upstream binaries don't require these runtime dependencies

## Project Structure

```
config/
├── knock/CMakeLists.txt          # Knock application build config
├── libgourou/CMakeLists.txt      # DRM library build config  
└── uPDFParser/CMakeLists.txt     # PDF parser build config
build.py                          # Main build orchestration script
CMakeLists.txt                    # Top-level CMake configuration
```

## Development Notes

- CMake configurations in `/config` are designed to be standalone and reusable
- Git repositories are pinned to specific commits for reproducibility
- Build artifacts are isolated in `~build` and `~checkout` directories (ignored by git)
- The build system handles cross-compilation through standard CMake mechanisms

## Common Issues

- Python 3 required for build script; fallback shell commands available at end of build.py
- Root privileges needed on apt-based systems for automatic dependency installation
- Original Knock repository is offline; project uses maintained fork