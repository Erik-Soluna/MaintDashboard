"""Dynamic ModelSerializer factory — built per model from the safe field set."""

from functools import lru_cache

from rest_framework import serializers

from .registry import safe_field_names


@lru_cache(maxsize=None)
def build_serializer(model):
    """Return (and cache) a read serializer exposing the model's safe fields,
    plus a human-readable `display` (the model's __str__)."""
    field_names = list(safe_field_names(model)) + ['display']
    meta = type('Meta', (), {'model': model, 'fields': field_names})
    return type(
        f'{model.__name__}DynamicSerializer',
        (serializers.ModelSerializer,),
        {
            'Meta': meta,
            'display': serializers.SerializerMethodField(),
            'get_display': lambda self, obj: str(obj),
        },
    )
