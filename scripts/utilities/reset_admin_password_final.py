#!/usr/bin/env python3
"""
DEPRECATED — the remote /api/reset-admin-password/ endpoint was removed for
security. Reset an admin password with the in-container management command.
"""
import sys

MESSAGE = """\
This script is disabled. The /api/reset-admin-password/ HTTP endpoint was removed
in the security hardening pass.

Reset an admin password by running the management command inside the running
container (Portainer console or a shell on the host):

    docker compose exec web python manage.py create_admin_user --username admin --force
    # omit --password to auto-generate a strong one (printed once),
    # or pass --password '<value>' / set ADMIN_PASSWORD in the environment.
"""

if __name__ == "__main__":
    print(MESSAGE)
    sys.exit(1)
