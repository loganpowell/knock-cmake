The goal of this project is to provide a serverless function that can process Knock files using C++ code packaged in a Lambda container image. The infrastructure is defined using Pulumi and deployed to AWS.

This is a container lambda that takes an .acsm file, which is an Adobe Content Server Message file, which contains a reference to an eBook or PDF protected by Adobe DRM, and processes it to produce a DRM-free PDF.

The function is built using a multi-stage Dockerfile that compiles C++ code with CMake and packages it into a Lambda-compatible container image. The build process is automated using AWS CodeBuild, which pulls the source code from an S3 bucket, builds the Docker image, and pushes it to an ECR repository.

Issues:

- We need to build the image in CodeBuild because we can't count on the user having Docker installed locally.
- The C++ code has dependencies that need to be checked out from GitHub, so the build process includes steps to clone those repositories and configure the build with CMake.
- The Lambda function is invoked via an HTTP endpoint, which accepts POST requests with the ACSM file content in base64 format and returns the processed EPUB or PDF file.
- We need to temporarily store the EPUB/PDF file so that the user can download it, which is done using a pre-signed URL from S3.
  - the files will be stored in S3 with a short expiration time for security (24 hours).
  - a link will be returned in the response for the user to download the file.

## Architecture

The architecture consists of the following components:

- **AWS Container Lambda**: The serverless function that processes the ACSM files.
- **AWS CodeBuild**: The service that builds the Docker image containing the C++ code and its dependencies.
- **AWS ECR**: The container registry that stores the built Docker images.
- **AWS S3**: The storage service used to hold
  - the source code for building
  - the processed files temporarily.
- **AWS IAM**: The identity and access management service that defines roles and policies for
  - the Lambda function
  - CodeBuild project.
- **AWS CloudWatch Logs**: The logging service that captures logs from the Lambda function for monitoring and debugging.

## User Workflow

1. The user sends a POST request to the Lambda function URL with the ACSM file content encoded in base64.
2. The Lambda function decodes the ACSM file and processes it using the Knock C++container.
3. The processed EPUB or PDF file is uploaded to S3 with a pre-signed URL.
4. The Lambda function returns the pre-signed URL to the user for downloading the file.
