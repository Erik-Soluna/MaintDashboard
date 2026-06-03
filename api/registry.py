"""
Dynamic model registry for the API. Reflects the live models in the project's
own apps so the API/Explorer never goes stale as the schema evolves.
"""

from django.apps import apps as django_apps

# Only expose our own domain apps (never auth/sessions/admin/authtoken/etc.).
EXPOSED_APPS = {'core', 'equipment', 'maintenance', 'events'}

# Models that hold secrets/credentials or are pure plumbing — never exposed.
DENY_MODELS = {'portainerconfig'}

# Field names containing any of these are stripped from output (defence in depth).
SENSITIVE_FIELD_HINTS = ('password', 'secret', 'token', 'api_key', 'apikey',
                         'signing', 'private_key', 'webhook_secret')


def exposed_models():
    """All non-sensitive models in our domain apps."""
    out = []
    for model in django_apps.get_models():
        if model._meta.app_label not in EXPOSED_APPS:
            continue
        if model._meta.model_name in DENY_MODELS:
            continue
        out.append(model)
    return sorted(out, key=model_key)


def model_key(model):
    return f"{model._meta.app_label}/{model._meta.model_name}"


def get_model(app_label, model_name):
    """Resolve a model by app_label + model_name, restricted to exposed models."""
    app_label = (app_label or '').lower()
    model_name = (model_name or '').lower()
    for m in exposed_models():
        if m._meta.app_label == app_label and m._meta.model_name == model_name:
            return m
    return None


def safe_field_names(model):
    """Concrete field names, minus anything that looks sensitive."""
    names = []
    for f in model._meta.concrete_fields:
        if any(h in f.name.lower() for h in SENSITIVE_FIELD_HINTS):
            continue
        names.append(f.name)
    return names


def field_metadata(model):
    """Lightweight field descriptors for the registry / Explorer."""
    meta = []
    safe = set(safe_field_names(model))
    for f in model._meta.concrete_fields:
        if f.name not in safe:
            continue
        meta.append({
            'name': f.name,
            'type': f.get_internal_type(),
            'relation': f.related_model._meta.label_lower if f.is_relation and f.related_model else None,
        })
    return meta
