from django.http import HttpResponse
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from .models import Budget
from .serializers import (
    BudgetSerializer, MonthlyTrendSerializer, 
    CategoryBreakdownSerializer, BudgetVsActualSerializer, 
    SpendingInsightSerializer
)
from .services import (
    get_monthly_trends, get_category_breakdown, 
    get_budget_vs_actual, get_spending_insights, export_to_csv
)

from rest_framework.viewsets import ViewSet

class AnalyticsView(ViewSet):
    permission_classes = [IsAuthenticated]

    def get_trends(self, request):
        group_id = request.query_params.get('group_id')
        months = int(request.query_params.get('months', 6))
        data = get_monthly_trends(request.user, group_id, months)
        return Response(MonthlyTrendSerializer(data, many=True).data)

    def get_categories(self, request):
        group_id = request.query_params.get('group_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        month = int(month) if month else None
        year = int(year) if year else None
        
        data = get_category_breakdown(request.user, group_id, month, year)
        return Response(CategoryBreakdownSerializer(data, many=True).data)

    def get_budget(self, request):
        group_id = request.query_params.get('group_id')
        today = timezone.now().date()
        month = int(request.query_params.get('month', today.month))
        year = int(request.query_params.get('year', today.year))
        
        data = get_budget_vs_actual(request.user, group_id, month, year)

        return Response(BudgetVsActualSerializer(data, many=True).data)

    def get_insights(self, request):
        data = get_spending_insights(request.user)
        return Response(SpendingInsightSerializer(data, many=True).data)

    def export(self, request):
        group_id = request.query_params.get('group_id')
        csv_string = export_to_csv(request.user, group_id)
        
        response = HttpResponse(csv_string, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="resolv_export.csv"'
        return response

class BudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
        
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
