import csv
import io
from decimal import Decimal
from django.db.models import Sum, F,Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from expenses.models import Expense, Settlement
from .models import Budget

def get_monthly_trends(user, group_id=None, months=6) -> list[dict]:
    # Returns total spending per month for the last N months.
    from expenses.models import ExpenseSplit
    end_date = timezone.now().date()
    start_date = (end_date - relativedelta(months=months)).replace(day=1)
    
    qs = ExpenseSplit.objects.filter(user=user, expense__date__gte=start_date, expense__is_active=True)
    if group_id:
        qs = qs.filter(expense__group_id=int(group_id))
        
    trends = (
        qs.annotate(month=TruncMonth('expense__date'))
        .values('month')
        .annotate(total=Sum('amount_owed'))
        .order_by('-month')
    )
    
    return [
        {
            'month': t['month'].strftime('%Y-%m') if t['month'] else '',
            'total': t['total'] or Decimal('0.00')
        } for t in trends
    ]

def get_category_breakdown(user, group_id=None, month=None, year=None) -> list[dict]:
    from expenses.models import ExpenseSplit
    qs = ExpenseSplit.objects.filter(user=user, expense__is_active=True)
    if group_id:
        qs = qs.filter(expense__group_id=int(group_id))
    if month:
        qs = qs.filter(expense__date__month=month)
    if year:
        qs = qs.filter(expense__date__year=year)
        
    breakdown = qs.values(category=F('expense__category')).annotate(total=Sum('amount_owed')).order_by('-total')
    total_spent = sum((item['total'] for item in breakdown if item['total']), Decimal('0.00'))
    
    result = []
    for item in breakdown:
        total = item['total'] or Decimal('0.00')
        pct = (total / total_spent * Decimal('100.0')) if total_spent else Decimal('0.00')
        result.append({
            'category': item['category'],
            'total': total,
            'percentage': pct.quantize(Decimal('0.01'))
        })
    return result

def get_budget_vs_actual(user, group_id, month, year) -> list[dict]:
    from expenses.models import ExpenseSplit
    # Fetches actual spending per category
    qs = ExpenseSplit.objects.filter(user=user, expense__date__month=month, expense__date__year=year, expense__is_active=True)
    if group_id:
        qs = qs.filter(expense__group_id=int(group_id))
        
    actuals = dict(qs.values_list('expense__category').annotate(total=Sum('amount_owed')))
    
    # Fetches Budget rows
    budgets_qs = Budget.objects.filter(user=user, month=month, year=year)
    if group_id:
        budgets_qs = budgets_qs.filter(group_id=int(group_id))
    budgets = {b.category: b for b in budgets_qs}
    
    all_categories = set(actuals.keys()) | set(budgets.keys())
    
    result = []
    for cat in all_categories:
        actual_spent = actuals.get(cat, Decimal('0.00')) or Decimal('0.00')
        budget = budgets.get(cat)
        
        if budget:
            limit = budget.amount_limit
            remaining = limit - actual_spent
            pct_used = (actual_spent / limit * Decimal('100.0')) if limit else Decimal('0.0')
            over_budget = actual_spent > limit
            
            result.append({
                'category': cat,
                'budget_limit': limit,
                'actual_spent': actual_spent,
                'remaining': remaining,
                'percentage_used': pct_used.quantize(Decimal('0.01')),
                'over_budget': over_budget,
                'budget_id': budget.id
            })
        else:
            result.append({
                'category': cat,
                'budget_limit': None,
                'actual_spent': actual_spent,
                'remaining': None,
                'percentage_used': None,
                'over_budget': None,
                'budget_id': None
            })
    return result

def get_spending_insights(user) -> list[dict]:
    insights = []
    today = timezone.now().date()
    this_month = today.month
    this_year = today.year
    
    last_month_date = today - relativedelta(months=1)
    last_month = last_month_date.month
    last_year = last_month_date.year

    # Rule 1: overspend alert
    bva = get_budget_vs_actual(user, None, this_month, this_year)
    for cat_data in bva:
        if cat_data['budget_limit'] and cat_data['actual_spent'] > cat_data['budget_limit'] * Decimal('1.20'):
            insights.append({
                'type': 'OVERSPEND_ALERT',
                'message': f"You have spent significantly over your budget for {cat_data['category']} this month.",
                'severity': 'HIGH'
            })

    # Rule 2: trend alert
    # BUG 4 FIX: pass Decimal('0.00') as start to sum() so int+Decimal TypeError cannot occur
    this_month_spent = sum(
        (item['total'] for item in get_category_breakdown(user, month=this_month, year=this_year)),
        Decimal('0.00')
    )
    last_month_spent = sum(
        (item['total'] for item in get_category_breakdown(user, month=last_month, year=last_year)),
        Decimal('0.00')
    )
    
    if last_month_spent > 0 and this_month_spent > last_month_spent * Decimal('1.15'):
         insights.append({
             'type': 'TREND_ALERT',
             'message': f"Your spending this month is 15% higher than last month.",
             'severity': 'MEDIUM'
         })
         
    # Rule 3: settlement nudge
    # Not fully implemented yet due to complexity of balance journey per group.
    
    return insights

def export_to_csv(user, group_id=None) -> str:
    from expenses.models import ExpenseSplit
    from django.db.models import Prefetch

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'date', 'title', 'category', 'amount', 'currency', 'paid_by', 'split_type', 'your_share'
    ])
    writer.writeheader()
    
    expenses_qs = Expense.objects.filter(is_active=True)
    if group_id:
        expenses_qs = expenses_qs.filter(group_id=int(group_id))

    # BUG 3 FIX: use Prefetch to load the user's splits in one extra query
    # instead of one query per expense inside the loop.
    expenses_qs = expenses_qs.filter(splits__user=user).distinct().prefetch_related(
        Prefetch(
            'splits',
            queryset=ExpenseSplit.objects.filter(user=user),
            to_attr='user_splits'
        )
    ).select_related('paid_by')
    
    for exp in expenses_qs:
        split = exp.user_splits[0] if exp.user_splits else None
        share = split.amount_owed if split else Decimal('0.00')
        writer.writerow({
            'date': exp.date.isoformat(),
            'title': exp.title,
            'category': exp.category,
            'amount': str(exp.amount),
            'currency': exp.currency,
            'paid_by': exp.paid_by.username,
            'split_type': exp.split_type,
            'your_share': str(share)
        })
        
    # Settlements...
    settlements_qs = Settlement.objects.filter(is_active=True, status='CONFIRMED')
    if group_id:
         settlements_qs = settlements_qs.filter(group_id=group_id)
         
    # Settlements where user is payer or receiver
    settlements_qs = settlements_qs.filter(Q(payer=user) | Q(receiver=user))

    
    for stl in settlements_qs:
        writer.writerow({
            'date': stl.created_at.date().isoformat(),
            'title': f"Settlement: {stl.payer.username} -> {stl.receiver.username}",
            'category': 'SETTLEMENT',
            'amount': str(stl.amount),
            'currency': stl.currency,
            'paid_by': stl.payer.username,
            'split_type': 'N/A',
            'your_share': str(stl.amount) if stl.payer == user else str(-stl.amount)
        })
        
    return output.getvalue()

def check_budget_alerts(group_id, category, month, year) -> None:
    pass # Implementation deferred to Celery task later
