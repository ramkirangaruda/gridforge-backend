# Base image with a non-root user
FROM python:3.10-slim

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -s /sbin/nologin -c "Application User" appuser

# Create a workspace directory owned by the new user
WORKDIR /workspace
RUN chown appuser:appuser /workspace

# Switch to the non-root user
USER appuser

# The entrypoint will be provided by the docker_runner
# CMD ["python", "main.py"]
