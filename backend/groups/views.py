from django.shortcuts import render

# Create your views here.
# backend/groups/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db.models import Sum 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Group
from .serializers import GroupSerializer 

class GroupViewSet(viewsets.ModelViewSet):
   
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return groups the user belongs to that have not been soft-deleted
        return Group.objects.filter(is_active=True, members=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the creator as the Admin
        group = serializer.save(admin=self.request.user)
        # Add the admin as the first member automatically
        group.members.add(self.request.user)


    def destroy(self, request, *args, **kwargs):
        # Secure the delete operation
        group = self.get_object()
        if group.admin != request.user:
            return Response(
                {'error': 'Only the group admin can delete the group.'},
                status=status.HTTP_403_FORBIDDEN
            )
        group.delete() # Triggers the soft delete defined in models.py
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """
        API to add a member to a group.
        Expects: {"user_id": <id>}
        """
        group = self.get_object()
        if group.admin != request.user:
            return Response(
                {'error': 'Only the group admin can add members.'},
                status=status.HTTP_403_FORBIDDEN
            )
        user_id = request.data.get('user_id')
        if user_id:
            group.members.add(user_id)
            return Response({'status': 'member added'}, status=status.HTTP_200_OK)
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='remove-member')
    def remove_member(self, request, pk=None):
        """
        API to remove a member from a group.
        Expects: {"user_id": <id>}
        """
       
        
        group = self.get_object()
        
        if group.admin != request.user:
            return Response(
                {'error': 'Only the group admin can remove members.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        if int(user_id) == group.admin.id:
            return Response({'error': 'The admin cannot be removed from the group.'}, status=status.HTTP_400_BAD_REQUEST)

        # --- FINANCIAL IMMUTABILITY CHECK ---
        # Import locally if needed to prevent circular imports
        from expenses.models import ExpenseSplit, Settlement
        
        # 1. Calculate what is owed TO this user in this group
        owed_to_user = ExpenseSplit.objects.filter(
            expense__group=group,
            expense__paid_by_id=user_id,
            expense__is_active=True
        ).exclude(user_id=user_id).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
        
        # 2. Calculate what is owed BY this user in this group
        owed_by_user = ExpenseSplit.objects.filter(
            expense__group=group,
            user_id=user_id,
            expense__is_active=True
        ).exclude(expense__paid_by_id=user_id).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
        
        # 3. Factor in confirmed settlements for this group
        settlements_sent = Settlement.objects.filter(
            group=group, payer_id=user_id, status__in=['CONFIRMED', 'confirmed'], is_active=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        settlements_received = Settlement.objects.filter(
            group=group, receiver_id=user_id, status__in=['CONFIRMED', 'confirmed'], is_active=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # 4. Net balance calculation
        net_balance = (owed_to_user - settlements_received) - (owed_by_user - settlements_sent)
        
        # If balance isn't zero, block removal and send exact balance to frontend modal
        if abs(net_balance) > 0.01:
            return Response({
                "detail": f"UNSETTLED_BALANCES:{net_balance}"
            }, status=status.HTTP_400_BAD_REQUEST)
        # ------------------------------------

        group.members.remove(user_id)
        # Note: In Phase 5, we will trigger the exact-match recalculation logic here
        return Response({'status': 'member removed'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='join')
    def join_group(self, request):
        """
        API to join a group using an 8-character invite code.
        Expects: {"invite_code": "ABCDEFGH"}
        """
        invite_code = request.data.get('invite_code')
        
        if not invite_code:
            return Response(
                {'error': 'invite_code is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Look for an active group matching the exact invite code
        group = Group.objects.filter(invite_code=invite_code, is_active=True).first()
        
        if not group:
            return Response(
                {'error': 'Invalid or inactive invite code.'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is already in the squad
        if request.user in group.members.all():
            return Response(
                {'message': 'You are already a member of this squad.'}, 
                status=status.HTTP_200_OK
            )

        # Add the user to the members ManyToMany field
        group.members.add(request.user)
        
        # Return the serialized group data so the frontend can immediately display it
        serializer = self.get_serializer(group)
        return Response({
            'message': 'Successfully joined the squad!',
            'group': serializer.data
        }, status=status.HTTP_200_OK)