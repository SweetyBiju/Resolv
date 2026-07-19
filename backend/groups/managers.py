from django.db import models


class ActiveGroupManager(models.Manager):
    """
    Default manager for Group. Excludes soft-deleted (is_active=False) rows.
    Group.objects.all() → active groups only.
    Group.all_objects.all() → includes deleted, for admin/audit.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
