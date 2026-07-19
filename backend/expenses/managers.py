from django.db import models

class ActiveManager(models.Manager):
    """Default manager: automatically excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class AllObjectsManager(models.Manager):
    """Explicit manager for admin/audit contexts that need deleted records."""
    pass