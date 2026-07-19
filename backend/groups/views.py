"""
groups/views.py
───────────────
HTTP mechanics only. No business logic. No balance guards. No inline ORM mutations.
All domain logic lives in groups/services.py.

ViewSets:
  GroupViewSet — full CRUD + membership actions + invite management
"""
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.throttling import ScopedRateThrottle
from .models import Group, GroupMembership
from .serializers import GroupSerializer, GroupAdminSerializer
from .permissions import IsGroupAdmin, IsMemberOfGroup
from . import services

logger = logging.getLogger('resolv.groups')


class JoinRateThrottle(ScopedRateThrottle):
    scope = 'join'


class GroupViewSet(viewsets.ModelViewSet):
    """
    Full group lifecycle.
    list/retrieve: any member. create/update/destroy: admin only.
    get_serializer_class() returns GroupAdminSerializer when requester is admin
    (adds invite_code to response).
    """
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get_serializer_class(self):
        """
        Admin sees invite_code; members do not.
        Single EXISTS query — no instance caching, no stale data.
        """
        pk = self.kwargs.get('pk')
        if pk and Group.objects.filter(pk=pk, admin=self.request.user).exists():
            return GroupAdminSerializer
        return GroupSerializer

    def get_queryset(self):
        """Own groups only, with admin eager-loaded."""
        return (
            Group.objects
            .filter(members=self.request.user)
            .select_related('admin')
            .prefetch_related('groupmembership_set__user')
        )

    def perform_create(self, serializer):
        """Delegates to service — creates group + admin membership atomically."""
        group = services.create_group(
            name       = serializer.validated_data['name'],
            admin_user = self.request.user,
            **{k: v for k, v in serializer.validated_data.items() if k != 'name'},
        )
        # Replace serializer instance so the response reflects the created group
        serializer.instance = group

    def destroy(self, request, *args, **kwargs):
        """Soft-delete with full balance guard. Raises 400 if unsettled."""
        group = self.get_object()
        try:
            services.delete_group(group=group, deleted_by=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Membership actions ─────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='add-member',
            permission_classes=[IsAuthenticated, IsGroupAdmin])
    def add_member(self, request, pk=None):
        """Admin-only: add a user by username, email, or database ID."""
        group      = self.get_object()
        identifier = request.data.get('identifier') or request.data.get('user_id')
        if not identifier:
            return Response({'detail': 'User identifier (username, email, or ID) is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.db.models import Q
        from users.models import User
        
        lookup_filter = Q(username__iexact=str(identifier).strip()) | Q(email__iexact=str(identifier).strip())
        if str(identifier).strip().isdigit():
            lookup_filter |= Q(pk=int(identifier))

        try:
            user = User.objects.filter(lookup_filter).first()
            if not user:
                raise User.DoesNotExist
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            services.add_member(group=group, user_to_add=user, added_by=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Member added.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-member',
            permission_classes=[IsAuthenticated, IsGroupAdmin])
    def remove_member(self, request, pk=None):
        """Admin-only: remove a member if their balance is settled."""
        group   = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from users.models import User
        try:
            user = User.all_objects.get(pk=int(user_id))
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            services.remove_member(group=group, user_to_remove=user, removed_by=request.user)
        except (ValueError, PermissionError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Member removed.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='transfer-admin',
            permission_classes=[IsAuthenticated, IsGroupAdmin])
    def transfer_admin(self, request, pk=None):
        """Admin-only: transfer admin rights to another group member."""
        group   = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from users.models import User
        try:
            new_admin = User.objects.get(pk=int(user_id))
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            services.transfer_admin(group=group, new_admin=new_admin, requested_by=request.user)
        except (ValueError, PermissionError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Admin rights transferred successfully.'}, status=status.HTTP_200_OK)


    # ── Invite actions ─────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='join',
            throttle_classes=[JoinRateThrottle])
    def join_group(self, request):
        """
        Join a group via invite code. Custom throttle: 10/hr (anti brute-force).
        Idempotent — returns the group if already a member.
        """
        invite_code = request.data.get('invite_code', '')
        if not invite_code:
            return Response({'detail': 'invite_code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = services.join_via_invite(invite_code=invite_code, user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(group)
        return Response({'detail': 'Joined successfully.', 'group': serializer.data},
                        status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='invite-code',
            permission_classes=[IsAuthenticated, IsGroupAdmin])
    def get_invite_code(self, request, pk=None):
        """Admin-only: retrieve the current invite code."""
        group = self.get_object()
        if group.admin_id != request.user.pk:
            return Response(
                {'detail': 'Only the group admin can view the invite code.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({'invite_code': group.invite_code})

    @action(detail=True, methods=['post'], url_path='regenerate-invite',
            permission_classes=[IsAuthenticated, IsGroupAdmin])
    def regenerate_invite(self, request, pk=None):
        """Admin-only: rotate the invite code, invalidating the old one."""
        group = self.get_object()
        try:
            new_code = services.regenerate_invite_code(group=group, requested_by=request.user)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response({'invite_code': new_code}, status=status.HTTP_200_OK)

