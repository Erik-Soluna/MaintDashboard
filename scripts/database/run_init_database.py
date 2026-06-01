#!/usr/bin/env python3
"""
DEPRECATED — the remote /api/migrations/ endpoint was removed for security.
Run init_database inside the container instead.
"""
import sys

MESSAGE = """\
This script is disabled. The /api/migrations/ HTTP endpoint was removed in the
security hardening pass.

Run init_database inside the running container (Portainer console or a shell on
the host):

    docker compose exec web python manage.py init_database --force
"""

if __name__ == "__main__":
    print(MESSAGE)
    sys.exit(1)
