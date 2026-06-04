"""API access permission — read-only diagnostics access for the AI agent /
staff. Writes are not enabled by this API."""

from rest_framework.permissions import BasePermission


class HasApiReadAccess(BasePermission):
    message = 'You need diagnostics/administration read access to use the API.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.is_staff:
            return True
        try:
            profile = user.userprofile
            return (profile.has_permission('diagnostics.read')
                    or profile.has_permission('administration.read'))
        except Exception:
            return False


class HasApiDeployAccess(BasePermission):
    """Privileged action permission — triggering a stack redeploy. Stricter than
    read access: requires diagnostics.deploy / administration.write / staff."""
    message = 'You need diagnostics.deploy or administration write access to redeploy.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.is_staff:
            return True
        try:
            profile = user.userprofile
            return (profile.has_permission('diagnostics.deploy')
                    or profile.has_permission('administration.write'))
        except Exception:
            return False
