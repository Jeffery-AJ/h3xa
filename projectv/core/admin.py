from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Company, Account, TransactionCategory, Transaction, 
    Budget, FinancialGoal
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'industry', 'currency', 'annual_revenue', 'is_active', 'created_at']
    list_filter = ['industry', 'currency', 'is_active', 'created_at']
    search_fields = ['name', 'registration_number', 'tax_id', 'owner__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'owner', 'industry', 'currency')
        }),
        ('Legal Details', {
            'fields': ('registration_number', 'tax_id', 'founded_date')
        }),
        ('Business Metrics', {
            'fields': ('employees_count', 'annual_revenue')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'account_type', 'current_balance', 'currency', 'is_active']
    list_filter = ['account_type', 'currency', 'is_active', 'created_at']
    search_fields = ['name', 'account_number', 'bank_name', 'company__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'available_balance']
    list_select_related = ['company']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'name', 'account_type', 'currency')
        }),
        ('Account Details', {
            'fields': ('account_number', 'bank_name', 'interest_rate')
        }),
        ('Balance Information', {
            'fields': ('initial_balance', 'current_balance', 'credit_limit', 'available_balance')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'parent', 'is_income', 'color_display', 'is_active']
    list_filter = ['is_income', 'is_active', 'created_at']
    search_fields = ['name', 'company__name']
    readonly_fields = ['id', 'created_at']
    list_select_related = ['company', 'parent']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 5px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'description_short', 'company', 'account', 'transaction_type', 
        'amount', 'transaction_date', 'status', 'is_anomaly'
    ]
    list_filter = [
        'transaction_type', 'status', 'is_anomaly', 'transaction_date', 
        'account__account_type', 'created_at'
    ]
    search_fields = [
        'description', 'reference_number', 'company__name', 
        'account__name', 'category__name'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_select_related = ['company', 'account', 'category', 'to_account']
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'account', 'to_account', 'transaction_type', 'category')
        }),
        ('Transaction Details', {
            'fields': ('amount', 'description', 'reference_number', 'transaction_date')
        }),
        ('Status & External', {
            'fields': ('status', 'external_id', 'external_source')
        }),
        ('Metadata', {
            'fields': ('tags', 'metadata'),
            'classes': ('collapse',)
        }),
        ('AI/ML Flags', {
            'fields': ('is_anomaly', 'confidence_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def description_short(self, obj):
        return obj.description[:50] + ('...' if len(obj.description) > 50 else '')
    description_short.short_description = 'Description'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'company', 'account', 'category', 'to_account'
        )


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'company', 'category', 'budgeted_amount', 
        'spent_amount', 'remaining_display', 'percentage_used_display'
    ]
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['name', 'company__name', 'category__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'remaining_amount', 'percentage_used']
    list_select_related = ['company', 'category']
    date_hierarchy = 'start_date'
    
    def remaining_display(self, obj):
        remaining = obj.remaining_amount
        color = 'green' if remaining >= 0 else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            remaining
        )
    remaining_display.short_description = 'Remaining'

    def percentage_used_display(self, obj):
        percentage = obj.percentage_used
        if percentage > 100:
            color = 'red'
        elif percentage > 80:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            percentage
        )
    percentage_used_display.short_description = '% Used'


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'company', 'goal_type', 'target_amount', 
        'current_amount', 'progress_display', 'target_date', 'is_achieved'
    ]
    list_filter = ['goal_type', 'is_achieved', 'target_date']
    search_fields = ['name', 'company__name']
    readonly_fields = ['id', 'created_at', 'progress_percentage']
    list_select_related = ['company']
    date_hierarchy = 'target_date'
    
    def progress_display(self, obj):
        percentage = obj.progress_percentage
        if percentage >= 100:
            color = 'green'
        elif percentage >= 75:
            color = 'blue'
        elif percentage >= 50:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            percentage
        )
    progress_display.short_description = 'Progress'
