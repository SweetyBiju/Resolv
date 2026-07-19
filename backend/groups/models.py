"""
groups/models.py
────────────────
Two models:
  Group           — a shared expense pool with invite-code membership
  GroupMembership — through model capturing role and join date

Design rules:
  - Group.admin uses SET_NULL (not PROTECT) so the group survives admin deletion.
  - GroupMembership is hard-deleted (it is not financial data).
  - Budget lives in analytics/, not here.
"""
import uuid
from django.db import models
from django.conf import settings
from .managers import ActiveGroupManager


class GroupMembership(models.Model):
    """
    Through model for the Group ↔ User many-to-many.
    Captures role (ADMIN / MEMBER) and the exact join timestamp.
    Always create via GroupMembership.objects.create() — never use members.add()
    directly, as that bypasses the role default.
    """
    ROLE_CHOICES = [
        ('ADMIN',  'Admin'),
        ('MEMBER', 'Member'),
    ]
    group     = models.ForeignKey('Group', on_delete=models.CASCADE)
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role      = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('group', 'user')]

    def __str__(self):
        return f"{self.user} in {self.group} ({self.role})"


class Group(models.Model):
    """
    A shared expense pool. Members are linked via the GroupMembership through model.

    admin → SET_NULL: if the admin user is deleted, the group survives and
    another member can be promoted. PROTECT would block any admin deletion forever.

    invite_code: auto-generated UUID hex[:8] on first save. DB unique constraint
    handles the rare collision — no retry loop (which would itself be a race condition).
    """
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Optional UI display fields
    emoji       = models.CharField(max_length=4, blank=True)
    currency    = models.CharField(max_length=3, default='INR')
    invite_code = models.CharField(max_length=10, unique=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    is_active   = models.BooleanField(default=True, db_index=True)

    # SET_NULL so the group survives admin deletion. Never PROTECT — see docstring.
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_groups',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='GroupMembership',
        related_name='joined_groups',
        blank=True,
    )

    objects     = ActiveGroupManager()   # default: active groups only
    all_objects = models.Manager()       # admin/audit: includes soft-deleted

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Soft delete — financial records referencing this group are preserved."""
        self.is_active = False
        self.save(update_fields=['is_active'])

    class Meta:
        indexes = [models.Index(fields=['invite_code'])]

    def __str__(self):
        return self.name


