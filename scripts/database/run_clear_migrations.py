#!/usr/bin/env python3
"""
DEPRECATED — the remote /api/migrations/ endpoint was removed for security
(it allowed running migrations and destructive commands remotely). Run the
command inside the container instead.
"""
import sys

MESSAGE = """\
This script is disabled. The /api/migrations/ HTTP endpoint was removed in the
security hardening pass because it allowed unauthenticated, remote execution of
migrations and destructive database commands.

Run clear_migrations inside the running container (Portainer console or a shell
on the host):

    docker compose exec web python manage.py clear_migrations --force
"""

if __name__ == "__main__":
    print(MESSAGE)
    sys.exit(1)
