# Simplified Build System for Knock Lambda

## Overview

This document describes the simplified build system that eliminates external dependencies and makes the Lambda container build more reliable and transparent.

## What Changed

### 1. **Local Source Dependencies** (`deps/` directory)

**Before:** Dependencies (`libgourou` and `uPDFParser`) were cloned from external git repositories during build time.

**After:** Dependencies are extracted from tarballs in `assets/sources/` into the `deps/` directory and committed to the repo.

```
deps/
├── libgourou/       # DRM processing library (extracted from tarball)
│   ├── include/
│   ├── src/
│   ├── utils/
│   └── CMakeLists.txt (copied from config/)
└── uPDFParser/      # PDF parsing library (extracted from tarball)
    ├── include/
    ├── src/
    └── CMakeLists.txt (copied from config/)
```

**Benefits:**
- ✅ No network dependency during build
- ✅ Full source visibility and control
- ✅ Git-trackable changes
- ✅ Reproducible builds
- ✅ Faster builds (no git cloning)

### 2. **Simplified Build Script** (`build_container.py`)

**Before:** `build_improved.py` handled git cloning and extraction

**After:** `build_container.py` uses only local sources with better validation

**Key Features:**
- Verifies all source directories exist before building
- Clear error messages with helpful suggestions
- No git operations (network-free)
- Better progress reporting
- Same static linking for portability

### 3. **Updated CMakeLists.txt**

**Before:**
```cmake
set(updfparser_DIR "${CMAKE_SOURCE_DIR}/~checkout/uPDFParser" ...)
set(libgourou_DIR "${CMAKE_SOURCE_DIR}/~checkout/libgourou" ...)
```

**After:**
```cmake
set(updfparser_DIR "${CMAKE_SOURCE_DIR}/deps/uPDFParser" ...)
set(libgourou_DIR "${CMAKE_SOURCE_DIR}/deps/libgourou" ...)
```

### 4. **Optimized Dockerfile**

**Before:** Copied entire project and ran `build_improved.py` with network access

**After:** Selectively copies only needed directories and uses `build_container.py`

```dockerfile
# Copies only what's needed
COPY deps/ /build/deps/
COPY knock/ /build/knock/
COPY config/ /build/config/
COPY CMakeLists.txt /build/
COPY build_container.py /build/
```

**Benefits:**
- Better Docker layer caching
- Faster builds on source changes
- No network required during build
- Clearer build logs

## Directory Structure

```
knock-lambda/
├── deps/                      # ✨ NEW: Local dependency sources
│   ├── libgourou/
│   │   ├── CMakeLists.txt    # Build configuration
│   │   ├── include/          # Library headers
│   │   ├── src/              # Library implementation
│   │   └── utils/            # DRM processor client
│   └── uPDFParser/
│       ├── CMakeLists.txt
│       ├── include/
│       └── src/
├── knock/                     # Main Knock application
│   ├── src/
│   │   └── knock.cpp         # Main C++ entry point
│   └── CMakeLists.txt
├── config/                    # Legacy config directory (can be removed)
├── assets/                    # Source tarballs (backup)
│   └── sources/
│       ├── libgourou.tar.gz
│       └── uPDFParser.tar.gz
├── infrastructure/            # AWS Lambda deployment
│   └── lambda/
│       ├── Dockerfile        # ✨ UPDATED: Uses deps/ and build_container.py
│       └── handler.py
├── CMakeLists.txt            # ✨ UPDATED: References deps/ instead of ~checkout/
├── build_container.py        # ✨ NEW: Simplified build script
├── build.py                  # Legacy build script (for reference)
└── build_improved.py         # Previous improved version (for reference)
```

## How to Use

### Local Development Build

```bash
# Using new simplified script
python3 build_container.py

# Or traditional script (still works with local sources)
python3 build.py
```

### Docker Container Build

```bash
# Build Lambda container locally
docker build -f infrastructure/lambda/Dockerfile -t knock-lambda .

# Test the container locally
docker run --rm knock-lambda
```

### Deploy to AWS

```bash
cd infrastructure
pulumi up
```

## Migration Notes

### For New Clones

The `deps/` directory is now tracked in git, so no additional setup is needed. Just:

```bash
git clone <repo>
cd knock-lambda
python3 build_container.py
```

### For Existing Repositories

If you have an existing clone without `deps/`, extract the sources:

```bash
mkdir -p deps
cd deps
tar -xzf ../assets/sources/libgourou.tar.gz
tar -xzf ../assets/sources/uPDFParser.tar.gz
cd ..

# Copy build configurations
cp config/libgourou/CMakeLists.txt deps/libgourou/
cp config/uPDFParser/CMakeLists.txt deps/uPDFParser/
```

## Troubleshooting

### "Source directory not found"

**Error:** `ERROR: libgourou source directory not found at /path/to/deps/libgourou`

**Solution:** Extract source tarballs:
```bash
mkdir -p deps
tar -xzf assets/sources/libgourou.tar.gz -C deps/
tar -xzf assets/sources/uPDFParser.tar.gz -C deps/
```

### "CMakeLists.txt not found"

**Error:** `ERROR: CMakeLists.txt not found in /path/to/deps/libgourou`

**Solution:** Copy build configuration:
```bash
cp -r config/libgourou/* deps/libgourou/
cp -r config/uPDFParser/* deps/uPDFParser/
```

### Docker Build Fails

If Docker build fails with "deps/ not found":
1. Verify `deps/` directory exists locally
2. Check `.dockerignore` doesn't exclude `deps/`
3. Ensure dependencies are extracted correctly

## Technical Details

### Static Linking

The build system uses static linking to create a portable binary that works across:
- Debian Bookworm (build environment)
- Amazon Linux 2023 (Lambda runtime)

This is configured in `CMakeLists.txt`:
```cmake
set(BUILD_STATIC ON)
set(BUILD_SHARED OFF)
```

### OpenSSL Compatibility

- **Build:** Debian Bookworm with OpenSSL 3.x
- **Runtime:** Amazon Linux 2023 with OpenSSL 3.x
- **Status:** ✅ Compatible (both use OpenSSL 3.x)

### Dependencies Included

The knock binary statically links:
- libgourou (v0.8.7+)
- uPDFParser
- OpenSSL (Crypto & SSL)
- libcurl
- zlib
- pugixml (XML parser)
- libzip (ZIP handling)
- Kerberos libraries (for curl)

## Next Steps

1. **Test the build locally:**
   ```bash
   python3 build_container.py
   ./build-output/knock --version
   ```

2. **Test Docker build:**
   ```bash
   docker build -f infrastructure/lambda/Dockerfile -t knock-lambda-test .
   ```

3. **Deploy to AWS:**
   ```bash
   cd infrastructure
   pulumi up
   ```

## Legacy Scripts

The following scripts are kept for reference but are no longer primary:
- `build.py` - Original build script (clones from git)
- `build_improved.py` - Improved version with better error handling

**Use `build_container.py` for all container builds.**

## Questions?

- Check the build logs for detailed output
- Verify `deps/` directory structure matches documentation
- Ensure CMakeLists.txt files are in place
- Review `WARP.md` for project-specific guidance
