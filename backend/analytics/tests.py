from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from users.models import User
from analytics.models import Budget
from groups.models import Group
from analytics.services import get_monthly_trends, get_category_breakdown

class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='pwd')
        self.group = Group.objects.create(name='Test Group', admin=self.user)
        self.group.members.add(self.user)

    def test_budget_creation(self):
        budget = Budget.objects.create(
            user=self.user,
            group=self.group,
            category='FOOD',
            amount_limit=Decimal('100.00'),
            month=1,
            year=2026
        )
        self.assertEqual(Budget.objects.count(), 1)
        self.assertEqual(budget.amount_limit, Decimal('100.00'))

    def test_get_monthly_trends_empty(self):
        trends = get_monthly_trends(self.user, months=6)
        self.assertEqual(trends, [])

    def test_get_category_breakdown_empty(self):
        breakdown = get_category_breakdown(self.user)
        self.assertEqual(breakdown, [])
