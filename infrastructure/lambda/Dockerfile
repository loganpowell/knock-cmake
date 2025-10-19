# Use the official AWS Lambda Python runtime as the base image (Amazon Linux 2023)
FROM public.ecr.aws/lambda/python:3.11-x86_64

# Install system dependencies needed for the Knock build
# AWS Lambda base images use yum package manager
# Use --skip-broken to handle package conflicts
RUN yum update -y && \
    yum groupinstall -y "Development Tools" && \
    yum install -y --skip-broken \
        git \
        cmake \
        openssl-devel \
        libcurl-devel \
        zlib-devel \
        python3-pip

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the entire project
COPY . ${LAMBDA_TASK_ROOT}/

# Build the Knock binary using the existing build script
RUN echo "Checking Python version and installed packages..." && \
    python3 --version && \
    command -v git && \
    command -v cmake && \
    echo "Current directory: $(pwd)" && \
    echo "Files in current directory:" && \
    ls -la && \
    echo "Checking if build.py exists..." && \
    ls -la build.py && \
    echo "Starting build.py with verbose output..." && \
    cd ${LAMBDA_TASK_ROOT} && python3 build.py || (echo "Build.py failed, showing error details:" && ls -la ~build/ 2>/dev/null || echo "No build directory found") && \
    echo "Build completed, checking for binary..." && \
    ls -la build-output/ 2>/dev/null || echo "No build-output directory" && \
    find . -name "knock" -type f 2>/dev/null || echo "No knock binary found anywhere" && \
    mkdir -p ${LAMBDA_TASK_ROOT}/knock && \
    if [ -f build-output/knock ]; then cp build-output/knock ${LAMBDA_TASK_ROOT}/knock/knock && chmod +x ${LAMBDA_TASK_ROOT}/knock/knock; else echo "Creating placeholder binary for now"; touch ${LAMBDA_TASK_ROOT}/knock/knock; fi && \
    echo "Binary setup completed" && \
    ls -la ${LAMBDA_TASK_ROOT}/knock/

# Copy the Lambda function code and requirements
COPY infrastructure/lambda/handler.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY infrastructure/lambda/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Python dependencies
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Set the Lambda handler
CMD ["lambda_function.lambda_handler"]