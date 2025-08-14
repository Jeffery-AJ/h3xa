"""
Open Banking Service Layer
Handles integration with various Open Banking providers
"""

import requests
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import BankProvider, BankConnection, LinkedBankAccount, SyncLog, PaymentInitiation
from core.models import Account, Transaction, TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


class OpenBankingException(Exception):
    """Base exception for Open Banking operations"""
    pass


class AuthenticationError(OpenBankingException):
    """Authentication related errors"""
    pass


class RateLimitError(OpenBankingException):
    """Rate limit exceeded"""
    pass


class BaseOpenBankingProvider:
    """Base class for Open Banking providers"""
    
    def __init__(self, provider: BankProvider):
        self.provider = provider
        self.base_url = provider.base_url
        self.client_id = getattr(settings, f'{provider.provider_type}_CLIENT_ID', '')
        self.client_secret = getattr(settings, f'{provider.provider_type}_CLIENT_SECRET', '')
        self.redirect_uri = getattr(settings, 'OPEN_BANKING_REDIRECT_URI', '')
        
    def authenticate(self, connection: BankConnection) -> Dict:
        """Authenticate and get access token"""
        raise NotImplementedError
        
    def refresh_token(self, connection: BankConnection) -> Dict:
        """Refresh access token"""
        raise NotImplementedError
        
    def get_accounts(self, connection: BankConnection) -> List[Dict]:
        """Get list of accounts"""
        raise NotImplementedError
        
    def get_transactions(self, connection: BankConnection, account_id: str, 
                        from_date: datetime = None, to_date: datetime = None) -> List[Dict]:
        """Get transactions for an account"""
        raise NotImplementedError
        
    def get_balance(self, connection: BankConnection, account_id: str) -> Dict:
        """Get account balance"""
        raise NotImplementedError
        
    def initiate_payment(self, connection: BankConnection, payment_data: Dict) -> Dict:
        """Initiate a payment"""
        raise NotImplementedError


class UKOpenBankingProvider(BaseOpenBankingProvider):
    """UK Open Banking provider implementation"""
    
    def authenticate(self, connection: BankConnection) -> Dict:
        """Authenticate using UK Open Banking standards"""
        auth_url = f"{self.base_url}/oauth2/authorize"
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'accounts payments',
            'state': str(connection.id),
            'request': self._create_jwt_request(connection)
        }
        
        return {
            'auth_url': f"{auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}",
            'state': params['state']
        }
    
    def exchange_code_for_token(self, connection: BankConnection, auth_code: str) -> Dict:
        """Exchange authorization code for access token"""
        token_url = f"{self.base_url}/oauth2/token"
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            
            # Update connection with tokens
            connection.access_token = token_data.get('access_token')
            connection.refresh_token = token_data.get('refresh_token')
            connection.consent_expires_at = timezone.now() + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )
            connection.status = 'CONNECTED'
            connection.save()
            
            return token_data
        else:
            raise AuthenticationError(f"Token exchange failed: {response.text}")
    
    def get_accounts(self, connection: BankConnection) -> List[Dict]:
        """Get accounts using UK Open Banking API"""
        url = f"{self.base_url}/aisp/v3.1/accounts"
        headers = self._get_headers(connection)
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('Data', {}).get('Account', [])
        else:
            self._handle_api_error(response)
    
    def get_transactions(self, connection: BankConnection, account_id: str,
                        from_date: datetime = None, to_date: datetime = None) -> List[Dict]:
        """Get transactions for an account"""
        url = f"{self.base_url}/aisp/v3.1/accounts/{account_id}/transactions"
        headers = self._get_headers(connection)
        
        params = {}
        if from_date:
            params['fromBookingDateTime'] = from_date.isoformat()
        if to_date:
            params['toBookingDateTime'] = to_date.isoformat()
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get('Data', {}).get('Transaction', [])
        else:
            self._handle_api_error(response)
    
    def get_balance(self, connection: BankConnection, account_id: str) -> Dict:
        """Get account balance"""
        url = f"{self.base_url}/aisp/v3.1/accounts/{account_id}/balances"
        headers = self._get_headers(connection)
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            balances = data.get('Data', {}).get('Balance', [])
            # Return the first available balance
            return balances[0] if balances else {}
        else:
            self._handle_api_error(response)
    
    def _get_headers(self, connection: BankConnection) -> Dict:
        """Get standard headers for API requests"""
        return {
            'Authorization': f'Bearer {connection.access_token}',
            'x-fapi-financial-id': getattr(settings, 'FAPI_FINANCIAL_ID', ''),
            'x-fapi-interaction-id': self._generate_interaction_id(),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _create_jwt_request(self, connection: BankConnection) -> str:
        """Create JWT request for authentication"""
        # This would normally create a proper JWT
        # For demo purposes, returning a placeholder
        return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    
    def _generate_interaction_id(self) -> str:
        """Generate unique interaction ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _handle_api_error(self, response):
        """Handle API errors"""
        if response.status_code == 401:
            raise AuthenticationError("Access token expired or invalid")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        else:
            raise OpenBankingException(f"API error: {response.status_code} - {response.text}")


class PlaidProvider(BaseOpenBankingProvider):
    """Plaid provider for US banking"""
    
    def authenticate(self, connection: BankConnection) -> Dict:
        """Authenticate using Plaid Link"""
        link_token_url = f"{self.base_url}/link/token/create"
        
        data = {
            'client_id': self.client_id,
            'secret': self.client_secret,
            'client_name': 'ProjectV AI CFO',
            'country_codes': ['US'],
            'language': 'en',
            'user': {
                'client_user_id': str(connection.company.id)
            },
            'products': ['transactions', 'accounts', 'identity']
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(link_token_url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise AuthenticationError(f"Plaid Link token creation failed: {response.text}")
    
    def exchange_public_token(self, connection: BankConnection, public_token: str) -> Dict:
        """Exchange public token for access token"""
        exchange_url = f"{self.base_url}/link/token/exchange"
        
        data = {
            'client_id': self.client_id,
            'secret': self.client_secret,
            'public_token': public_token
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(exchange_url, json=data, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            
            connection.access_token = token_data.get('access_token')
            connection.status = 'CONNECTED'
            connection.save()
            
            return token_data
        else:
            raise AuthenticationError(f"Token exchange failed: {response.text}")


class OpenBankingService:
    """Main service for handling Open Banking operations"""
    
    def __init__(self):
        self.providers = {
            'UK_OPEN_BANKING': UKOpenBankingProvider,
            'PLAID': PlaidProvider,
            # Add more providers as needed
        }
    
    def get_provider(self, provider_type: str, provider: BankProvider):
        """Get provider instance"""
        provider_class = self.providers.get(provider_type)
        if not provider_class:
            raise OpenBankingException(f"Unsupported provider type: {provider_type}")
        return provider_class(provider)
    
    def initiate_connection(self, company, provider_id: str, **kwargs) -> Dict:
        """Initiate bank connection process"""
        try:
            provider = BankProvider.objects.get(id=provider_id, is_active=True)
            
            connection = BankConnection.objects.create(
                company=company,
                provider=provider,
                bank_name=kwargs.get('bank_name', provider.name),
                status='CONNECTING',
                auto_sync_enabled=kwargs.get('auto_sync_enabled', True),
                sync_frequency_hours=kwargs.get('sync_frequency_hours', 24)
            )
            
            provider_service = self.get_provider(provider.provider_type, provider)
            auth_data = provider_service.authenticate(connection)
            
            return {
                'connection_id': connection.id,
                'auth_url': auth_data.get('auth_url'),
                'status': 'initiated'
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate connection: {str(e)}")
            raise OpenBankingException(f"Connection initiation failed: {str(e)}")
    
    def sync_accounts(self, connection: BankConnection) -> Dict:
        """Sync accounts from bank"""
        sync_log = SyncLog.objects.create(
            connection=connection,
            sync_type='ACCOUNTS',
            status='STARTED'
        )
        
        try:
            provider_service = self.get_provider(connection.provider.provider_type, connection.provider)
            accounts_data = provider_service.get_accounts(connection)
            
            created_count = 0
            updated_count = 0
            
            for account_data in accounts_data:
                linked_account, created = LinkedBankAccount.objects.update_or_create(
                    connection=connection,
                    external_account_id=account_data.get('AccountId'),
                    defaults={
                        'account_name': account_data.get('Nickname', account_data.get('AccountId')),
                        'account_type': self._map_account_type(account_data.get('AccountType')),
                        'currency': account_data.get('Currency', 'USD'),
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                # Sync balance for this account
                self._sync_account_balance(connection, linked_account, provider_service)
            
            sync_log.status = 'SUCCESS'
            sync_log.records_processed = len(accounts_data)
            sync_log.records_created = created_count
            sync_log.records_updated = updated_count
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            connection.last_sync = timezone.now()
            connection.save()
            
            return {
                'status': 'success',
                'accounts_synced': len(accounts_data),
                'created': created_count,
                'updated': updated_count
            }
            
        except Exception as e:
            sync_log.status = 'FAILED'
            sync_log.error_message = str(e)
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            logger.error(f"Account sync failed for connection {connection.id}: {str(e)}")
            raise OpenBankingException(f"Account sync failed: {str(e)}")
    
    def sync_transactions(self, connection: BankConnection, 
                         from_date: datetime = None, to_date: datetime = None) -> Dict:
        """Sync transactions from bank"""
        sync_log = SyncLog.objects.create(
            connection=connection,
            sync_type='TRANSACTIONS',
            status='STARTED'
        )
        
        try:
            provider_service = self.get_provider(connection.provider.provider_type, connection.provider)
            
            total_processed = 0
            total_created = 0
            total_updated = 0
            
            for linked_account in connection.linked_accounts.filter(sync_transactions=True):
                transactions_data = provider_service.get_transactions(
                    connection, 
                    linked_account.external_account_id,
                    from_date,
                    to_date
                )
                
                for tx_data in transactions_data:
                    # Create or update transaction
                    transaction, created = self._create_or_update_transaction(
                        linked_account, tx_data
                    )
                    
                    total_processed += 1
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1
                
                linked_account.last_transaction_sync = timezone.now()
                linked_account.save()
            
            sync_log.status = 'SUCCESS'
            sync_log.records_processed = total_processed
            sync_log.records_created = total_created
            sync_log.records_updated = total_updated
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            connection.last_sync = timezone.now()
            connection.save()
            
            return {
                'status': 'success',
                'transactions_processed': total_processed,
                'created': total_created,
                'updated': total_updated
            }
            
        except Exception as e:
            sync_log.status = 'FAILED'
            sync_log.error_message = str(e)
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            logger.error(f"Transaction sync failed for connection {connection.id}: {str(e)}")
            raise OpenBankingException(f"Transaction sync failed: {str(e)}")
    
    def _sync_account_balance(self, connection: BankConnection, 
                             linked_account: LinkedBankAccount, provider_service):
        """Sync balance for a specific account"""
        try:
            balance_data = provider_service.get_balance(connection, linked_account.external_account_id)
            
            if balance_data:
                linked_account.current_balance = Decimal(str(balance_data.get('Amount', {}).get('Amount', 0)))
                linked_account.available_balance = Decimal(str(balance_data.get('Amount', {}).get('Amount', 0)))
                linked_account.save()
                
                # Update linked local account if exists
                if linked_account.local_account:
                    linked_account.local_account.current_balance = linked_account.current_balance
                    linked_account.local_account.save()
                    
        except Exception as e:
            logger.warning(f"Failed to sync balance for account {linked_account.id}: {str(e)}")
    
    def _create_or_update_transaction(self, linked_account: LinkedBankAccount, tx_data: Dict):
        """Create or update transaction from bank data"""
        external_id = tx_data.get('TransactionId') or tx_data.get('AccountTransactionId')
        
        # Determine transaction type and amount
        amount = Decimal(str(tx_data.get('Amount', {}).get('Amount', 0)))
        credit_debit = tx_data.get('CreditDebitIndicator', 'Debit')
        
        transaction_type = TransactionType.EXPENSE if credit_debit == 'Debit' else TransactionType.INCOME
        
        # Get or create local account
        local_account = linked_account.local_account
        if not local_account:
            local_account = self._create_local_account_from_linked(linked_account)
        
        transaction_data = {
            'company': linked_account.connection.company,
            'account': local_account,
            'transaction_type': transaction_type,
            'amount': abs(amount),
            'description': tx_data.get('TransactionInformation', ''),
            'transaction_date': self._parse_transaction_date(tx_data.get('BookingDateTime')),
            'status': TransactionStatus.COMPLETED,
            'external_id': external_id,
            'external_source': 'open_banking',
            'metadata': {
                'bank_data': tx_data,
                'linked_account_id': str(linked_account.id)
            }
        }
        
        transaction, created = Transaction.objects.update_or_create(
            external_id=external_id,
            external_source='open_banking',
            defaults=transaction_data
        )
        
        return transaction, created
    
    def _create_local_account_from_linked(self, linked_account: LinkedBankAccount):
        """Create local account from linked bank account"""
        from core.models import AccountType
        
        account_type_mapping = {
            'CURRENT': AccountType.CHECKING,
            'SAVINGS': AccountType.SAVINGS,
            'CREDIT_CARD': AccountType.CREDIT_CARD,
            'LOAN': AccountType.LOAN,
            'INVESTMENT': AccountType.INVESTMENT,
        }
        
        local_account = Account.objects.create(
            company=linked_account.connection.company,
            name=linked_account.account_name,
            account_type=account_type_mapping.get(linked_account.account_type, AccountType.OTHER),
            bank_name=linked_account.connection.bank_name,
            currency=linked_account.currency,
            current_balance=linked_account.current_balance,
            initial_balance=linked_account.current_balance
        )
        
        linked_account.local_account = local_account
        linked_account.save()
        
        return local_account
    
    def _map_account_type(self, bank_account_type: str) -> str:
        """Map bank account type to our account types"""
        mapping = {
            'Current': 'CURRENT',
            'Savings': 'SAVINGS',
            'CreditCard': 'CREDIT_CARD',
            'Loan': 'LOAN',
            'Investment': 'INVESTMENT',
        }
        return mapping.get(bank_account_type, 'OTHER')
    
    def _parse_transaction_date(self, date_str: str) -> datetime:
        """Parse transaction date string"""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return timezone.now()


# Initialize service instance
open_banking_service = OpenBankingService()
