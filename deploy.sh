#!/usr/bin/env bash
# Rebuilds and restarts the production stack using whatever code is
# currently checked out on this VM. Run manually over SSH, or let
# .github/workflows/deploy.yml invoke it automatically after every push
# to main that passes CI.
#
# Deliberately does NOT do the `git fetch`/`git reset` step itself - that
# lives in the GitHub Actions workflow instead, so a fresh copy of this
# very script is on disk before it starts running. A deploy script that
# rewrites itself via git mid-execution is a real footgun: bash doesn't
# guarantee it keeps reading the OLD file contents once they've been
# overwritten out from under it. Calling this after the pull, as a fresh
# process, sidesteps that entirely.
#
# Does NOT touch the frontend service - see the deployment writeup for
# why (Vercel is the recommended home for it, not this VM). If you're
# running frontend here instead, add it to the service list below.
set -euo pipefail
cd "$(dirname "$0")"

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build \
  redis gridforge-exec-image backend worker caddy

# Old image layers from the rebuild pile up on disk over many deploys
# otherwise - this VM doesn't have room to spare for that.
docker image prune -f
