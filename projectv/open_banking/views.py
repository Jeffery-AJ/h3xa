from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import logging

from .models import (
    BankProvider, BankConnection, LinkedBankAccount,
    SyncLog, PaymentInitiation, ConsentManagement
)
from .serializers import (
    BankProviderSerializer, BankConnectionSerializer, LinkedBankAccountSerializer,
    SyncLogSerializer, PaymentInitiationSerializer, ConsentManagementSerializer,
    BankConnectionCreateSerializer, PaymentRequestSerializer
)
from .services import open_banking_service, OpenBankingException
from core.permissions import IsCompanyOwner

logger = logging.getLogger(__name__)


class BankProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for bank providers"""
    queryset = BankProvider.objects.filter(is_active=True)
    serializer_class = BankProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['provider_type', 'country_code', 'supports_payments']

    @action(detail=False, methods=['get'])
    def countries(self, request):
        """Get list of supported countries"""
        countries = self.queryset.values_list('country_code', flat=True).distinct()
        return Response({'countries': list(countries)})

    @action(detail=False, methods=['get'])
    def provider_types(self, request):
        """Get list of provider types"""
        provider_types = [
            {'value': choice[0], 'label': choice[1]}
            for choice in BankProvider.PROVIDER_TYPES
        ]
        return Response({'provider_types': provider_types})


class BankConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for bank connections"""
    serializer_class = BankConnectionSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'provider__provider_type', 'auto_sync_enabled']

    def get_queryset(self):
        return BankConnection.objects.filter(
            company__owner=self.request.user
        ).select_related('provider')

    def perform_create(self, serializer):
        # Get the user's company (assuming one company per user for now)
        company = self.request.user.companies.first()
        if not company:
            raise ValueError("User must have a company to create bank connections")
        serializer.save(company=company)

    @action(detail=False, methods=['post'])
    def initiate_connection(self, request):
        """Initiate a new bank connection"""
        serializer = BankConnectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                company = request.user.companies.first()
                if not company:
                    return Response(
                        {'error': 'User must have a company'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                result = open_banking_service.initiate_connection(
                    company=company,
                    **serializer.validated_data
                )
                
                return Response(result, status=status.HTTP_201_CREATED)
                
            except OpenBankingException as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete_auth(self, request, pk=None):
        """Complete authentication after user authorization"""
        connection = self.get_object()
        auth_code = request.data.get('auth_code')
        
        if not auth_code:
            return Response(
                {'error': 'Authorization code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            provider_service = open_banking_service.get_provider(
                connection.provider.provider_type,
                connection.provider
            )
            
            # Exchange code for token (implementation depends on provider)
            if hasattr(provider_service, 'exchange_code_for_token'):
                token_data = provider_service.exchange_code_for_token(connection, auth_code)
            elif hasattr(provider_service, 'exchange_public_token'):
                token_data = provider_service.exchange_public_token(connection, auth_code)
            else:
                raise OpenBankingException("Provider does not support token exchange")
            
            # Sync accounts after successful authentication
            sync_result = open_banking_service.sync_accounts(connection)
            
            return Response({
                'status': 'success',
                'connection_status': connection.status,
                'sync_result': sync_result
            })
            
        except OpenBankingException as e:
            logger.error(f"Auth completion failed for connection {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def sync_accounts(self, request, pk=None):
        """Manually sync accounts for a connection"""
        connection = self.get_object()
        
        if connection.status != 'CONNECTED':
            return Response(
                {'error': 'Connection must be in CONNECTED status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = open_banking_service.sync_accounts(connection)
            return Response(result)
            
        except OpenBankingException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def sync_transactions(self, request, pk=None):
        """Manually sync transactions for a connection"""
        connection = self.get_object()
        
        if connection.status != 'CONNECTED':
            return Response(
                {'error': 'Connection must be in CONNECTED status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse date range from request
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        
        # Default to last 30 days if no dates provided
        if not from_date:
            from_date = timezone.now() - timedelta(days=30)
        if not to_date:
            to_date = timezone.now()
        
        try:
            result = open_banking_service.sync_transactions(
                connection, from_date, to_date
            )
            return Response(result)
            
        except OpenBankingException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect and revoke bank connection"""
        connection = self.get_object()
        
        try:
            # Update connection status
            connection.status = 'REVOKED'
            connection.access_token = None
            connection.refresh_token = None
            connection.save()
            
            # Deactivate linked accounts
            connection.linked_accounts.update(is_active=False, sync_transactions=False)
            
            return Response({
                'status': 'success',
                'message': 'Connection disconnected successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to disconnect connection {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to disconnect connection'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get detailed status of bank connection"""
        connection = self.get_object()
        
        # Get latest sync log
        latest_sync = connection.sync_logs.first()
        
        # Get account count
        account_count = connection.linked_accounts.filter(is_active=True).count()
        
        # Get recent transaction count
        recent_transactions = 0
        if connection.last_sync:
            since_last_sync = timezone.now() - timedelta(days=7)
            for account in connection.linked_accounts.filter(is_active=True):
                if account.local_account:
                    recent_transactions += account.local_account.transactions.filter(
                        created_at__gte=since_last_sync
                    ).count()
        
        return Response({
            'connection_id': connection.id,
            'status': connection.status,
            'bank_name': connection.bank_name,
            'provider': connection.provider.name,
            'connected_accounts': account_count,
            'recent_transactions': recent_transactions,
            'last_sync': connection.last_sync,
            'next_sync': connection.next_sync,
            'consent_expires_at': connection.consent_expires_at,
            'days_until_expiry': connection.days_until_expiry,
            'auto_sync_enabled': connection.auto_sync_enabled,
            'latest_sync_status': latest_sync.status if latest_sync else None,
        })


class LinkedBankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for linked bank accounts"""
    serializer_class = LinkedBankAccountSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account_type', 'is_active', 'sync_transactions']

    def get_queryset(self):
        return LinkedBankAccount.objects.filter(
            connection__company__owner=self.request.user
        ).select_related('connection', 'local_account')

    @action(detail=True, methods=['post'])
    def create_local_account(self, request, pk=None):
        """Create a local account linked to this bank account"""
        linked_account = self.get_object()
        
        if linked_account.local_account:
            return Response(
                {'error': 'Local account already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            local_account = open_banking_service._create_local_account_from_linked(linked_account)
            
            return Response({
                'status': 'success',
                'local_account_id': local_account.id,
                'message': 'Local account created successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to create local account for {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to create local account'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def sync_balance(self, request, pk=None):
        """Manually sync balance for this account"""
        linked_account = self.get_object()
        
        if linked_account.connection.status != 'CONNECTED':
            return Response(
                {'error': 'Connection must be active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            provider_service = open_banking_service.get_provider(
                linked_account.connection.provider.provider_type,
                linked_account.connection.provider
            )
            
            open_banking_service._sync_account_balance(
                linked_account.connection, linked_account, provider_service
            )
            
            linked_account.refresh_from_db()
            
            return Response({
                'status': 'success',
                'current_balance': linked_account.current_balance,
                'available_balance': linked_account.available_balance,
                'last_updated': timezone.now()
            })
            
        except OpenBankingException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for sync logs"""
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sync_type', 'status']

    def get_queryset(self):
        return SyncLog.objects.filter(
            connection__company__owner=self.request.user
        ).select_related('connection')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get sync summary statistics"""
        queryset = self.get_queryset()
        
        # Recent sync stats (last 7 days)
        recent_date = timezone.now() - timedelta(days=7)
        recent_syncs = queryset.filter(started_at__gte=recent_date)
        
        total_syncs = recent_syncs.count()
        successful_syncs = recent_syncs.filter(status='SUCCESS').count()
        failed_syncs = recent_syncs.filter(status='FAILED').count()
        
        success_rate = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
        
        # Latest sync by type
        latest_syncs = {}
        for sync_type in ['ACCOUNTS', 'TRANSACTIONS', 'BALANCES', 'FULL']:
            latest = queryset.filter(sync_type=sync_type).first()
            latest_syncs[sync_type.lower()] = {
                'status': latest.status if latest else None,
                'started_at': latest.started_at if latest else None,
                'completed_at': latest.completed_at if latest else None,
            }
        
        return Response({
            'recent_stats': {
                'total_syncs': total_syncs,
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'success_rate': round(success_rate, 2)
            },
            'latest_syncs': latest_syncs
        })


class PaymentInitiationViewSet(viewsets.ModelViewSet):
    """ViewSet for payment initiation"""
    serializer_class = PaymentInitiationSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['payment_type', 'status', 'currency']

    def get_queryset(self):
        return PaymentInitiation.objects.filter(
            connection__company__owner=self.request.user
        ).select_related('connection')

    @action(detail=False, methods=['post'])
    def initiate_payment(self, request):
        """Initiate a new payment"""
        serializer = PaymentRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                connection = get_object_or_404(
                    BankConnection,
                    id=serializer.validated_data['connection_id'],
                    company__owner=request.user,
                    status='CONNECTED'
                )
                
                if not connection.provider.supports_payments:
                    return Response(
                        {'error': 'Provider does not support payments'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create payment record
                payment = PaymentInitiation.objects.create(
                    connection=connection,
                    **{k: v for k, v in serializer.validated_data.items() 
                       if k != 'connection_id'}
                )
                
                # Initiate payment with provider
                provider_service = open_banking_service.get_provider(
                    connection.provider.provider_type,
                    connection.provider
                )
                
                payment_result = provider_service.initiate_payment(
                    connection, serializer.validated_data
                )
                
                # Update payment with result
                payment.external_payment_id = payment_result.get('payment_id')
                payment.status = payment_result.get('status', 'INITIATED')
                payment.save()
                
                return Response({
                    'payment_id': payment.id,
                    'external_payment_id': payment.external_payment_id,
                    'status': payment.status,
                    'auth_url': payment_result.get('auth_url')
                }, status=status.HTTP_201_CREATED)
                
            except OpenBankingException as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        """Check payment status with bank"""
        payment = self.get_object()
        
        try:
            provider_service = open_banking_service.get_provider(
                payment.connection.provider.provider_type,
                payment.connection.provider
            )
            
            # Check status with provider
            status_result = provider_service.check_payment_status(
                payment.connection, payment.external_payment_id
            )
            
            # Update payment status
            payment.status = status_result.get('status', payment.status)
            if status_result.get('executed_at'):
                payment.executed_at = status_result['executed_at']
            payment.save()
            
            return Response({
                'payment_id': payment.id,
                'status': payment.status,
                'executed_at': payment.executed_at
            })
            
        except OpenBankingException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ConsentManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for consent management"""
    serializer_class = ConsentManagementSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['consent_type', 'status']

    def get_queryset(self):
        return ConsentManagement.objects.filter(
            connection__company__owner=self.request.user
        ).select_related('connection')

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a consent"""
        consent = self.get_object()
        
        try:
            consent.status = 'REVOKED'
            consent.revoked_at = timezone.now()
            consent.save()
            
            # If this was the main consent, also update connection status
            if consent.consent_type == 'ACCOUNT_INFO':
                consent.connection.status = 'REVOKED'
                consent.connection.save()
            
            return Response({
                'status': 'success',
                'message': 'Consent revoked successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to revoke consent {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to revoke consent'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
