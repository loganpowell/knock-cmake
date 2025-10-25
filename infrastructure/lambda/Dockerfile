# Optimized Dockerfile for AWS Lambda Container Cold Start Performance
# 
# Key optimizations based on Lambda's convergent encryption and chunk caching:
# 1. Use private ECR cached Debian base for fastest, most reliable builds
# 2. Layer dependencies separately from application code
# 3. Minimize unique bytes in each layer
# 4. Clean package caches to reduce layer size
# 
# Lambda shares 512kb chunks across all users via convergent encryption.
# Using private ECR eliminates Docker Hub rate limits and external dependencies.

# Stage 1: Build knock binary using cached Debian base
# Using libgourou v0.8.7 which requires OpenSSL 3.x support
# Pull from private ECR cache (cached during CodeBuild pre-build phase)
ARG ECR_REGISTRY_URL
FROM ${ECR_REGISTRY_URL}/knock-base:debian-bookworm-slim AS builder

# Install build dependencies including static libraries
# Combine into single RUN to reduce layers and leverage Lambda's chunk caching
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    libcurl4-openssl-dev \
    libkrb5-dev \
    zlib1g-dev \
    pkg-config \
    python3 \
    wget \
    ca-certificates \
    file \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory for build
WORKDIR /build

# Copy project files - include deps/ directory with local sources
COPY deps/ /build/deps/
COPY knock/ /build/knock/
COPY CMakeLists.txt /build/
COPY build_container.py /build/

# Build the Knock binary using simplified build script
SHELL ["/bin/bash", "-c"]
RUN set -o pipefail && \
    echo "=== KNOCK CONTAINER BUILD - LOCAL SOURCES ===" && \
    echo "Build environment:" && \
    cmake --version && \
    python3 --version && \
    openssl version && \
    echo "" && \
    echo "=== VERIFYING SOURCE DIRECTORIES ===" && \
    ls -la deps/ && \
    ls -la knock/ && \
    echo "" && \
    echo "=== RUNNING SIMPLIFIED BUILD SCRIPT ===" && \
    export CMAKE_BUILD_TYPE=Release && \
    python3 -u build_container.py 2>&1 | tee /tmp/build.log; \
    BUILD_EXIT_CODE=$?; \
    echo "" && \
    if [ $BUILD_EXIT_CODE -ne 0 ]; then \
        echo "=== BUILD FAILED ===" && \
        echo "Last 100 lines of build log:" && \
        tail -100 /tmp/build.log && \
        exit 1; \
    fi && \
    echo "=== VERIFYING BUILD OUTPUT ===" && \
    ls -lh build-output/knock && \
    file build-output/knock && \
    echo "" && \
    echo "=== CHECKING DYNAMIC DEPENDENCIES ===" && \
    ldd build-output/knock && \
    echo "" && \
    echo "=== BUILD SUCCESSFUL ===" && \
    ./build-output/knock 2>&1 | head -5 || true

# Stage 2: Create Lambda runtime image using same cached Debian base
# Using private ECR cached Debian to ensure binary compatibility with build stage
# GLIBC compatibility is critical for the compiled knock and adept_activate binaries
# Same base image as build stage for consistency and maximum caching efficiency
ARG ECR_REGISTRY_URL
FROM ${ECR_REGISTRY_URL}/knock-base:debian-bookworm-slim

# Install Python and essential runtime dependencies in single layer
# Minimize unique bytes while maintaining binary compatibility
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    libcurl4 \
    libssl3 \
    zlib1g \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set up Lambda directories
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the built binary and shared libraries
RUN mkdir -p ${LAMBDA_TASK_ROOT}/knock ${LAMBDA_TASK_ROOT}/lib
COPY --from=builder /build/build-output/knock ${LAMBDA_TASK_ROOT}/knock/knock
COPY --from=builder /build/build-output/adept_activate ${LAMBDA_TASK_ROOT}/knock/adept_activate
COPY --from=builder /build/~build/libgourou/*.so* ${LAMBDA_TASK_ROOT}/lib/
COPY --from=builder /build/~build/uPDFParser/*.so* ${LAMBDA_TASK_ROOT}/lib/
RUN chmod +x ${LAMBDA_TASK_ROOT}/knock/knock ${LAMBDA_TASK_ROOT}/knock/adept_activate

# Set LD_LIBRARY_PATH so knock can find the shared libraries
ENV LD_LIBRARY_PATH="${LAMBDA_TASK_ROOT}/lib:${LD_LIBRARY_PATH}"

# Verify the binary works in the Lambda environment
RUN echo "=== VERIFYING BINARY IN LAMBDA ENVIRONMENT ===" && \
    ls -la ${LAMBDA_TASK_ROOT}/knock/ && \
    ls -la ${LAMBDA_TASK_ROOT}/lib/ && \
    file ${LAMBDA_TASK_ROOT}/knock/knock && \
    file ${LAMBDA_TASK_ROOT}/knock/adept_activate && \
    echo "Checking shared library dependencies for knock:" && \
    ldd ${LAMBDA_TASK_ROOT}/knock/knock && \
    echo "Checking shared library dependencies for adept_activate:" && \
    ldd ${LAMBDA_TASK_ROOT}/knock/adept_activate && \
    echo "Testing knock binary:" && \
    ${LAMBDA_TASK_ROOT}/knock/knock 2>&1 | head -5 || echo "Knock test complete (exit code: $?)" && \
    echo "Testing adept_activate binary:" && \
    ${LAMBDA_TASK_ROOT}/knock/adept_activate --version 2>&1 || echo "adept_activate test complete (exit code: $?)"

# Install Python dependencies in a separate layer for better caching
# This layer will likely be shared across many Lambda functions
COPY infrastructure/lambda/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages \
    -r ${LAMBDA_TASK_ROOT}/requirements.txt \
    awslambdaric

# Copy application-specific files in final layer
# Keep unique application code in the smallest possible layer
COPY infrastructure/lambda/handler.py ${LAMBDA_TASK_ROOT}/lambda_function.py

# Set the entrypoint to use the Lambda Runtime Interface Client
ENTRYPOINT ["/usr/bin/python3", "-m", "awslambdaric"]
CMD ["lambda_function.lambda_handler"]
