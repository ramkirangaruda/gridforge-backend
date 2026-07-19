#!/bin/sh
# Runs once as root (the image's default user, on purpose - see below)
# purely to grant appuser access to the mounted Docker socket, then execs
# the real process as appuser. The worker's own Python code never runs
# as root.
#
# Why this can't just be a fixed USER in the Dockerfile like
# backend/Dockerfile: /var/run/docker.sock is owned by root:<docker
# group>, but that group's GID is whatever the Docker installation on
# the HOST assigned it - it varies machine to machine and isn't knowable
# at image-build time. Matching group membership has to happen at
# container start, against whatever socket is actually mounted in.
#
# Read this alongside its limit, not instead of it: granting access to
# the Docker socket is root-equivalent on the HOST regardless of which
# UID inside this container holds it - anything with socket access can
# launch a privileged container that mounts the host's / and do whatever
# it wants from there. This script narrows the blast radius for risks
# UNRELATED to the socket itself (a bug in the worker's own Python code
# can't casually write to arbitrary host files or modify system binaries
# inside this container's own filesystem), it does not eliminate the
# fundamental exposure that comes with mounting the socket at all. See
# docker-compose.yml's comment on the worker service for the actual
# hardening option if that residual risk matters for a given deployment
# (routing through docker-socket-proxy instead of mounting the raw
# socket, so the worker never holds a credential broader than the
# handful of Docker API calls docker_runner.py actually makes).
set -e

DOCKER_SOCK=/var/run/docker.sock
if [ -S "$DOCKER_SOCK" ]; then
    SOCK_GID=$(stat -c '%g' "$DOCKER_SOCK")
    if ! getent group "$SOCK_GID" >/dev/null 2>&1; then
        groupadd -g "$SOCK_GID" dockerhost
    fi
    usermod -aG "$SOCK_GID" appuser
fi

exec gosu appuser "$@"
