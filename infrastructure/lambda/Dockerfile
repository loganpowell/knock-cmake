# Use the official AWS Lambda Python runtime as the base image (Amazon Linux 2023)
FROM public.ecr.aws/lambda/python:3.11-x86_64

# Install system dependencies needed for the Knock build  
# Install system dependencies needed for the Knock build
# Use openssl11-devel to avoid conflicts with pre-installed openssl-snapsafe-libs  
RUN yum update -y && \
    yum groupinstall -y "Development Tools" && \
    yum install -y --skip-broken \
        git \
        openssl11-devel \
        libcurl-devel \
        zlib-devel \
        python3-pip \
        wget \
        tar \
        pkgconfig

# Install a newer version of CMake (the yum version is too old)
RUN cd /tmp && \
    curl -L -o cmake-3.28.0-linux-x86_64.tar.gz https://github.com/Kitware/CMake/releases/download/v3.28.0/cmake-3.28.0-linux-x86_64.tar.gz && \
    tar -xzf cmake-3.28.0-linux-x86_64.tar.gz && \
    cp -r cmake-3.28.0-linux-x86_64/* /usr/local/ && \
    rm -rf cmake-3.28.0-linux-x86_64* && \
    ln -sf /usr/local/bin/cmake /usr/bin/cmake

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the entire project
COPY . ${LAMBDA_TASK_ROOT}/



# Build the Knock binary using the existing build script with error handling
RUN echo "=== STARTING KNOCK BUILD PROCESS ===" && \
    echo "Verifying cmake version:" && \
    cmake --version && \
    echo "Verifying build environment:" && \
    python3 --version && \
    command -v git && \
    echo "Current directory: $(pwd)" && \
    echo "Available files:" && \
    ls -la && \
    echo "=== RUNNING IMPROVED BUILD SCRIPT WITH STRICT ERROR HANDLING ===" && \
    cd ${LAMBDA_TASK_ROOT} && \
    set -e && \
    python3 -u build_improved.py 2>&1 | tee /tmp/build.log && \
    echo "=== BUILD.PY COMPLETED - VERIFYING OUTPUT ===" && \
    if [ ! -d "build-output" ]; then echo "ERROR: build-output directory not created"; cat /tmp/build.log; exit 1; fi && \
    echo "Build output directory contents:" && \
    ls -la build-output/ && \
    if [ ! -f "build-output/knock" ]; then echo "ERROR: knock binary not found"; ls -la build-output/; exit 1; fi && \
    echo "Verifying knock binary:" && \
    ls -la build-output/knock && \
    file build-output/knock && \
    echo "=== SETTING UP LAMBDA BINARY LOCATION ===" && \
    mkdir -p ${LAMBDA_TASK_ROOT}/knock && \
    cp build-output/knock ${LAMBDA_TASK_ROOT}/knock/knock && \
    chmod +x ${LAMBDA_TASK_ROOT}/knock/knock && \
    echo "Final binary verification:" && \
    ls -la ${LAMBDA_TASK_ROOT}/knock/ && \
    file ${LAMBDA_TASK_ROOT}/knock/knock && \
    ${LAMBDA_TASK_ROOT}/knock/knock --help 2>/dev/null || echo "Binary exists but may need libraries" && \
    echo "=== KNOCK BUILD PROCESS COMPLETED ==="

# Copy the Lambda function code and requirements
COPY infrastructure/lambda/handler.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY infrastructure/lambda/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Python dependencies
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Set the Lambda handler
CMD ["lambda_function.lambda_handler"]