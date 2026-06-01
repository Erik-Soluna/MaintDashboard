#!/usr/bin/env python3
"""
DEPRECATED — the remote /api/create-admin/ endpoint was removed for security
(it allowed unauthenticated superuser creation). Manage admin users with the
in-container management command instead.
"""
import sys

MESSAGE = """\
This script is disabled. The /api/create-admin/ HTTP endpoint was removed in the
security hardening pass because it allowed anyone to create a superuser remotely.

Create or reset an admin user by running the management command inside the
running container (Portainer console or a shell on the host):

    docker compose exec web python manage.py create_admin_user --username admin --force
    # omit --password to auto-generate a strong one (printed once),
    # or pass --password '<value>' / set ADMIN_PASSWORD in the environment.
"""

if __name__ == "__main__":
    print(MESSAGE)
    sys.exit(1)
