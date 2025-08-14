from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Company, Account, TransactionCategory, Transaction, 
    Budget, FinancialGoal, AccountType, TransactionType, TransactionStatus,
    BulkUpload, BulkUploadError
)


class CompanySerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    total_accounts = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'registration_number', 'tax_id', 'industry',
            'founded_date', 'employees_count', 'annual_revenue', 'currency',
            'owner', 'owner_name', 'created_at', 'updated_at', 'is_active',
            'total_accounts', 'total_balance'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner', 'owner_name', 'total_accounts', 'total_balance']

    def get_total_accounts(self, obj):
        return obj.accounts.filter(is_active=True).count()

    def get_total_balance(self, obj):
        return sum(account.current_balance for account in obj.accounts.filter(is_active=True))


class AccountSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    available_balance = serializers.ReadOnlyField()
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'company', 'company_name', 'name', 'account_type', 'account_type_display',
            'account_number', 'bank_name', 'currency', 'current_balance', 'initial_balance',
            'credit_limit', 'interest_rate', 'available_balance', 'transaction_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_balance', 'available_balance']

    def get_transaction_count(self, obj):
        return obj.transactions.count()


class TransactionCategorySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    subcategories = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TransactionCategory
        fields = [
            'id', 'company', 'company_name', 'name', 'parent', 'parent_name',
            'color', 'icon', 'is_income', 'subcategories', 'transaction_count',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'subcategories', 'transaction_count']

    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_active=True)
        return TransactionCategorySerializer(subcategories, many=True, context=self.context).data

    def get_transaction_count(self, obj):
        return obj.transaction_set.count()


class TransactionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'company', 'company_name', 'account', 'account_name',
            'to_account', 'to_account_name', 'transaction_type', 'transaction_type_display',
            'category', 'category_name', 'amount', 'description', 'reference_number',
            'transaction_date', 'status', 'status_display', 'external_id', 'external_source',
            'tags', 'metadata', 'is_anomaly', 'confidence_score',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_anomaly', 'confidence_score']

    def validate(self, data):
        """Custom validation for transactions"""
        transaction_type = data.get('transaction_type')
        to_account = data.get('to_account')
        account = data.get('account')
        
        # Transfer validation
        if transaction_type == TransactionType.TRANSFER:
            if not to_account:
                raise serializers.ValidationError("Transfer transactions must have a destination account.")
            if to_account == account:
                raise serializers.ValidationError("Cannot transfer to the same account.")
        
        # Category validation
        category = data.get('category')
        if category:
            if transaction_type == TransactionType.INCOME and not category.is_income:
                raise serializers.ValidationError("Income transactions must use income categories.")
            elif transaction_type == TransactionType.EXPENSE and category.is_income:
                raise serializers.ValidationError("Expense transactions must use expense categories.")
        
        return data


class BudgetSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    remaining_amount = serializers.ReadOnlyField()
    percentage_used = serializers.ReadOnlyField()
    
    class Meta:
        model = Budget
        fields = [
            'id', 'company', 'company_name', 'name', 'category', 'category_name',
            'budgeted_amount', 'spent_amount', 'remaining_amount', 'percentage_used',
            'start_date', 'end_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'spent_amount']

    def validate(self, data):
        """Validate budget dates"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("End date must be after start date.")
        
        return data


class FinancialGoalSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    goal_type_display = serializers.CharField(source='get_goal_type_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = FinancialGoal
        fields = [
            'id', 'company', 'company_name', 'name', 'goal_type', 'goal_type_display',
            'target_amount', 'current_amount', 'progress_percentage', 'target_date',
            'is_achieved', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'current_amount', 'is_achieved']


# Analytics Serializers
class AccountBalanceAnalyticsSerializer(serializers.Serializer):
    """Serializer for account balance analytics"""
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance_change = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance_change_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class CashFlowAnalyticsSerializer(serializers.Serializer):
    """Serializer for cash flow analytics"""
    period = serializers.CharField()
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_cash_flow = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()


class CategoryAnalyticsSerializer(serializers.Serializer):
    """Serializer for category-wise spending analytics"""
    category_id = serializers.UUIDField(allow_null=True)
    category_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()
    percentage_of_total = serializers.DecimalField(max_digits=5, decimal_places=2)


class FinancialHealthSerializer(serializers.Serializer):
    """Serializer for overall financial health metrics"""
    health_score = serializers.DecimalField(max_digits=3, decimal_places=1)
    total_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_liabilities = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_worth = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    cash_flow_ratio = serializers.DecimalField(max_digits=5, decimal_places=2)
    debt_to_income_ratio = serializers.DecimalField(max_digits=5, decimal_places=2)


class BulkUploadSerializer(serializers.ModelSerializer):
    """Serializer for bulk CSV uploads"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_type_display = serializers.CharField(source='get_upload_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = BulkUpload
        fields = [
            'id', 'user', 'user_name', 'company', 'company_name', 'upload_type', 
            'upload_type_display', 'file_name', 'status', 'status_display',
            'total_records', 'successful_records', 'failed_records', 'success_rate',
            'error_details', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'success_rate']
    
    def get_success_rate(self, obj):
        """Calculate success rate percentage"""
        if obj.total_records > 0:
            return round((obj.successful_records / obj.total_records) * 100, 2)
        return 0.0


class BulkUploadErrorSerializer(serializers.ModelSerializer):
    """Serializer for bulk upload errors"""
    
    class Meta:
        model = BulkUploadError
        fields = [
            'id', 'bulk_upload', 'row_number', 'field_name', 
            'error_message', 'row_data', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
