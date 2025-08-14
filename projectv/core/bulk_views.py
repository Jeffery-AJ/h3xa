import json
import os
import tempfile
import csv
import io
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from django.db import transaction as db_transaction
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from .models import Company, BulkUpload, BulkUploadError, Account, Transaction, TransactionCategory, TransactionStatus
from .serializers import BulkUploadSerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class BulkUploadViewSet(viewsets.ModelViewSet):
    """ViewSet for managing bulk CSV uploads with LlamaIndex RAG"""
    
    serializer_class = BulkUploadSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter uploads by user's companies"""
        return BulkUpload.objects.filter(company__owner=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """
        Smart CSV upload with both RAG analysis and Django model creation
        
        This endpoint:
        1. Validates and processes CSV data into Django models 
        2. Creates LlamaIndex documents for AI analysis
        3. Provides detailed error reporting
        
        Parameters:
        - file: CSV file to upload
        - upload_type: 'transactions', 'accounts', 'categories', or 'rag_only'
        - company_id: Company ID (optional, will use user's default)
        
        Usage:
        POST /api/v1/bulk-uploads/upload/
        Content-Type: multipart/form-data
        
        Form data:
        - file: <csv_file>
        - upload_type: transactions|accounts|categories|rag_only
        - company_id: <company_uuid> (optional)
        """
        try:
            # Validate file
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            csv_file = request.FILES['file']
            
            # Validate file type
            if not csv_file.name.endswith('.csv'):
                return Response(
                    {'error': 'File must be a CSV file'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get upload type
            upload_type = request.data.get('upload_type', 'rag_only').lower()
            valid_types = ['transactions', 'accounts', 'categories', 'rag_only']
            
            if upload_type not in valid_types:
                return Response({
                    'error': f'Invalid upload_type. Must be one of: {", ".join(valid_types)}',
                    'available_types': valid_types
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get or create company
            company = None
            if 'company_id' in request.data:
                try:
                    company = Company.objects.get(
                        id=request.data['company_id'],
                        owner=request.user
                    )
                except Company.DoesNotExist:
                    return Response(
                        {'error': 'Company not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Use user's first company or create default
                company = request.user.companies.first()
                if not company:
                    company = Company.objects.create(
                        name=f"{request.user.username}'s Company",
                        owner=request.user
                    )

            # Create bulk upload record
            bulk_upload = BulkUpload.objects.create(
                company=company,
                user=request.user,
                upload_type=upload_type,
                file_name=csv_file.name,
                file_size=csv_file.size,
                status='processing',
                started_at=timezone.now()
            )

            logger.info(f"Starting CSV upload: {bulk_upload.id} - {upload_type}")

            # Process CSV content
            try:
                # Read CSV content with proper encoding
                csv_file.seek(0)
                content = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(content))
                rows = list(csv_reader)
                
                bulk_upload.total_rows = len(rows)
                bulk_upload.save()
                
                logger.info(f"Processing {len(rows)} rows of type: {upload_type}")
                
                successful_rows = 0
                failed_rows = 0
                
                # Process based on upload type
                if upload_type == 'transactions':
                    successful_rows, failed_rows = self._process_transactions(rows, bulk_upload, company)
                elif upload_type == 'accounts':
                    successful_rows, failed_rows = self._process_accounts(rows, bulk_upload, company)
                elif upload_type == 'categories':
                    successful_rows, failed_rows = self._process_categories(rows, bulk_upload, company)
                else:  # rag_only
                    successful_rows = len(rows)
                    failed_rows = 0

                # Update bulk upload record
                bulk_upload.successful_rows = successful_rows
                bulk_upload.failed_rows = failed_rows
                
                if failed_rows == 0:
                    bulk_upload.status = 'completed'
                elif successful_rows > 0:
                    bulk_upload.status = 'partial'
                else:
                    bulk_upload.status = 'failed'
                
                bulk_upload.completed_at = timezone.now()
                bulk_upload.save()

                # Add LlamaIndex RAG processing if requested
                ai_insights = None
                if upload_type == 'rag_only' or request.data.get('include_rag', 'false').lower() == 'true':
                    try:
                        ai_insights = self._create_rag_analysis(csv_file, company, bulk_upload)
                    except Exception as e:
                        logger.warning(f"RAG analysis failed: {str(e)}")
                        ai_insights = f"RAG analysis failed: {str(e)}"

                return Response({
                    'success': True,
                    'bulk_upload_id': bulk_upload.id,
                    'status': bulk_upload.status,
                    'total_rows': bulk_upload.total_rows,
                    'successful_rows': successful_rows,
                    'failed_rows': failed_rows,
                    'success_rate': bulk_upload.success_rate,
                    'message': f'Upload completed. {successful_rows} rows processed successfully, {failed_rows} rows failed.',
                    'data_summary': {
                        'file_name': csv_file.name,
                        'file_size': csv_file.size,
                        'upload_type': upload_type,
                        'company': company.name
                    },
                    'ai_insights': ai_insights,
                    'error_details': self._get_error_summary(bulk_upload) if failed_rows > 0 else None
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Update bulk upload status to failed
                bulk_upload.status = 'failed'
                bulk_upload.error_summary = str(e)
                bulk_upload.completed_at = timezone.now()
                bulk_upload.save()

                logger.error(f"CSV processing failed: {str(e)}")
                return Response({
                    'bulk_upload_id': bulk_upload.id,
                    'error': f'CSV processing failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return Response(
                {'error': f'Upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_transactions(self, rows, bulk_upload, company):
        """Process transaction CSV rows with proper validation and robust balance updates."""
        successful_rows = 0
        failed_rows = 0
        required_fields = ['account_name', 'amount', 'description', 'date']
        
        logger.info(f"Processing {len(rows)} transaction rows for company {company.id}")
        
        valid_transactions_data = []
        accounts_to_update = {}

        # Step 1: Validate all rows and prepare data
        for row_num, row in enumerate(rows, start=2):
            try:
                transaction_data = self._validate_transaction_data(row, row_num, bulk_upload, company)
                if transaction_data:
                    valid_transactions_data.append(transaction_data)
                    
                    # Aggregate balance changes
                    account = transaction_data['account']
                    amount = transaction_data['amount']
                    ttype = transaction_data['transaction_type']
                    
                    change = amount if ttype == 'income' else -amount
                    accounts_to_update[account.id] = accounts_to_update.get(account.id, Decimal('0.0')) + change
                else:
                    failed_rows += 1
            except Exception as e:
                logger.error(f"Critical validation error in row {row_num}: {str(e)}")
                self._add_error(bulk_upload, row_num, 'critical_error', str(e), row)
                failed_rows += 1

        # Step 2: Perform database operations in a single transaction
        if valid_transactions_data:
            try:
                with db_transaction.atomic():
                    # Bulk create transactions
                    transactions_to_create = [Transaction(**data) for data in valid_transactions_data]
                    Transaction.objects.bulk_create(transactions_to_create)
                    successful_rows = len(transactions_to_create)
                    
                    # Bulk update account balances
                    accounts = Account.objects.filter(id__in=accounts_to_update.keys())
                    for account in accounts:
                        account.current_balance += accounts_to_update[account.id]
                    
                    Account.objects.bulk_update(accounts, ['current_balance'])
                    
                    logger.info(f"Successfully created {successful_rows} transactions and updated {len(accounts)} accounts.")

            except Exception as e:
                logger.error(f"Database transaction failed: {str(e)}")
                # If the entire transaction fails, mark all as failed
                failed_rows += len(valid_transactions_data)
                successful_rows = 0
                self._add_error(bulk_upload, 0, 'db_transaction_error', str(e), {})

        return successful_rows, failed_rows
    
    def _validate_transaction_data(self, row, row_num, bulk_upload, company):
        """Validate transaction row data with detailed error reporting"""
        try:
            # Find account by name
            account_name = str(row['account_name']).strip()
            try:
                account = Account.objects.get(company=company, name=account_name)
            except Account.DoesNotExist:
                self._add_error(bulk_upload, row_num, 'validation', 
                              f"Account '{account_name}' not found. Please create the account first.", row)
                return None
            
            # Validate amount
            try:
                amount_str = str(row['amount']).strip().replace('$', '').replace(',', '')
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                self._add_error(bulk_upload, row_num, 'validation', 
                              f"Invalid amount format: {row['amount']}. Use format like: 100.00 or -50.25", row)
                return None
            
            # Validate and parse date
            date_str = str(row['date']).strip()
            transaction_date = self._parse_date(date_str)
            if not transaction_date:
                self._add_error(bulk_upload, row_num, 'validation', 
                              f"Invalid date format: {date_str}. Use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY", row)
                return None
            
            # Determine transaction type
            transaction_type = str(row.get('transaction_type', '')).lower().strip()
            if not transaction_type:
                # Auto-determine based on amount
                transaction_type = 'expense' if amount < 0 else 'income'
            
            # Validate transaction type
            valid_types = ['income', 'expense', 'transfer']
            if transaction_type not in valid_types:
                self._add_error(bulk_upload, row_num, 'validation', 
                              f"Invalid transaction type '{transaction_type}'. Valid types: {', '.join(valid_types)}", row)
                return None
            
            # Handle category
            category = None
            category_name = str(row.get('category', '')).strip()
            if category_name:
                try:
                    category = TransactionCategory.objects.get(company=company, name=category_name)
                except TransactionCategory.DoesNotExist:
                    # Auto-create category
                    category = TransactionCategory.objects.create(
                        company=company,
                        name=category_name,
                        is_income=(transaction_type == 'income')
                    )
                    logger.info(f"Auto-created category: {category_name}")
            
            # Prepare transaction data
            transaction_data = {
                'company': company,
                'account': account,
                'category': category,
                'transaction_type': transaction_type,
                'amount': abs(amount),  # Store as positive, type determines income/expense
                'description': str(row['description']).strip(),
                'transaction_date': transaction_date,  # Keep as datetime
                'reference_number': str(row.get('reference_number', '')).strip() or None,
                'status': TransactionStatus.COMPLETED.value  # Use the string value from the enum
            }
            
            return transaction_data
            
        except Exception as e:
            self._add_error(bulk_upload, row_num, 'validation_error', str(e), row)
            return None
    
    def _process_accounts(self, rows, bulk_upload, company):
        """Process account CSV rows"""
        successful_rows = 0
        failed_rows = 0
        required_fields = ['name', 'account_type', 'balance']
        
        for row_num, row in enumerate(rows, start=2):
            try:
                # Validate required fields
                missing_fields = []
                for field in required_fields:
                    if field not in row or not str(row[field]).strip():
                        missing_fields.append(field)
                
                if missing_fields:
                    self._add_error(bulk_upload, row_num, 'missing_fields', 
                                  f"Missing required fields: {', '.join(missing_fields)}", row)
                    failed_rows += 1
                    continue
                
                # Validate account data
                account_data = self._validate_account_data(row, row_num, bulk_upload, company)
                if not account_data:
                    failed_rows += 1
                    continue
                
                # Create account
                with db_transaction.atomic():
                    Account.objects.create(**account_data)
                    successful_rows += 1
                    
            except Exception as e:
                self._add_error(bulk_upload, row_num, 'processing_error', str(e), row)
                failed_rows += 1
        
        return successful_rows, failed_rows
    
    def _validate_account_data(self, row, row_num, bulk_upload, company):
        """Validate account row data"""
        try:
            name = str(row['name']).strip()
            if not name:
                self._add_error(bulk_upload, row_num, 'validation', "Account name cannot be empty", row)
                return None
            
            # Check for duplicate account names
            if Account.objects.filter(company=company, name=name).exists():
                self._add_error(bulk_upload, row_num, 'duplicate', f"Account '{name}' already exists", row)
                return None
            
            # Validate account type
            account_type = str(row['account_type']).lower().strip()
            valid_account_types = ['checking', 'savings', 'credit_card', 'cash', 'investment', 'loan']
            
            if account_type not in valid_account_types:
                self._add_error(bulk_upload, row_num, 'validation', 
                              f"Invalid account type '{account_type}'. Valid types: {', '.join(valid_account_types)}", row)
                return None
            
            # Validate balance
            try:
                balance_str = str(row['balance']).strip().replace('$', '').replace(',', '')
                balance = Decimal(balance_str)
            except (InvalidOperation, ValueError):
                self._add_error(bulk_upload, row_num, 'validation', f"Invalid balance format: {row['balance']}", row)
                return None
            
            return {
                'company': company,
                'name': name,
                'account_type': account_type,
                'current_balance': balance,
                'initial_balance': balance,
                'account_number': str(row.get('account_number', '')).strip() or None,
                'bank_name': str(row.get('bank_name', '')).strip() or None,
                'currency': str(row.get('currency', 'USD')).strip().upper(),
                'is_active': str(row.get('is_active', 'true')).lower() in ['true', '1', 'yes', 'active']
            }
            
        except Exception as e:
            self._add_error(bulk_upload, row_num, 'validation_error', str(e), row)
            return None
    
    def _process_categories(self, rows, bulk_upload, company):
        """Process category CSV rows using get_or_create to avoid duplicates."""
        successful_rows = 0
        failed_rows = 0
        skipped_rows = 0
        required_fields = ['name', 'is_income']
        
        for row_num, row in enumerate(rows, start=2):
            try:
                # Validate required fields
                missing_fields = [field for field in required_fields if field not in row or not str(row[field]).strip()]
                if missing_fields:
                    self._add_error(bulk_upload, row_num, 'missing_fields', f"Missing required fields: {', '.join(missing_fields)}", row)
                    failed_rows += 1
                    continue
                
                # Validate and prepare category data
                category_data, error = self._validate_category_data(row, row_num, bulk_upload, company)
                if error:
                    failed_rows += 1
                    continue
                
                # Use get_or_create to avoid duplicate errors
                category, created = TransactionCategory.objects.get_or_create(
                    company=company,
                    name=category_data['name'],
                    defaults=category_data
                )
                
                if created:
                    successful_rows += 1
                    logger.info(f"Created new category: {category.name}")
                else:
                    skipped_rows += 1
                    logger.info(f"Skipped existing category: {category.name}")
                    
            except Exception as e:
                self._add_error(bulk_upload, row_num, 'processing_error', str(e), row)
                failed_rows += 1
        
        logger.info(f"Category processing complete. Successful: {successful_rows}, Failed: {failed_rows}, Skipped: {skipped_rows}")
        return successful_rows, failed_rows

    def _validate_category_data(self, row, row_num, bulk_upload, company):
        """Validate category row data and return a dictionary for creation."""
        try:
            name = str(row['name']).strip()
            if not name:
                self._add_error(bulk_upload, row_num, 'validation', "Category name cannot be empty", row)
                return None, True

            # Validate is_income
            is_income_str = str(row.get('is_income', '')).lower().strip()
            if is_income_str in ['true', '1', 'yes', 'income']:
                is_income = True
            elif is_income_str in ['false', '0', 'no', 'expense']:
                is_income = False
            else:
                self._add_error(bulk_upload, row_num, 'validation', 
                              f"Invalid is_income value '{is_income_str}'. Use: true/false, 1/0, yes/no, income/expense", row)
                return None, True
            
            # This dictionary is now only used for defaults in get_or_create
            return {
                'name': name,
                'is_income': is_income,
                'is_active': str(row.get('is_active', 'true')).lower() in ['true', '1', 'yes', 'active']
            }, False
            
        except Exception as e:
            self._add_error(bulk_upload, row_num, 'validation_error', str(e), row)
            return None, True
    
    def _parse_date(self, date_str):
        """Parse date string with multiple format support"""
        date_formats = [
            '%Y-%m-%d',           # 2023-12-01
            '%m/%d/%Y',           # 12/01/2023
            '%d/%m/%Y',           # 01/12/2023
            '%Y-%m-%d %H:%M:%S',  # 2023-12-01 10:30:00
            '%m/%d/%Y %H:%M:%S',  # 12/01/2023 10:30:00
        ]
        
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                # Make timezone aware
                if timezone.is_naive(parsed_date):
                    parsed_date = timezone.make_aware(parsed_date)
                return parsed_date
            except ValueError:
                continue
        
        return None
    
    def _add_error(self, bulk_upload, row_number, error_type, error_message, row_data):
        """Add an error to the bulk upload with proper timezone handling"""
        logger.warning(f"Error in row {row_number}: {error_message}")
        
        BulkUploadError.objects.create(
            bulk_upload=bulk_upload,
            row_number=row_number,
            field_name='',
            error_type=error_type,
            error_message=error_message,
            row_data=row_data
        )
    
    def _get_error_summary(self, bulk_upload):
        """Get a summary of errors for the upload"""
        errors = BulkUploadError.objects.filter(bulk_upload=bulk_upload)[:5]  # Get first 5 errors
        return [
            {
                'row': error.row_number,
                'type': error.error_type,
                'message': error.error_message
            }
            for error in errors
        ]
    
    def _create_rag_analysis(self, csv_file, company, bulk_upload):
        """Create RAG analysis using LlamaIndex SimpleDirectoryReader"""
        try:
            from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
            from llama_index.llms.openai import OpenAI
            from llama_index.embeddings.openai import OpenAIEmbedding

            # Configure LlamaIndex for GitHub Models API
            Settings.llm = OpenAI(
                api_key=settings.OPENAI_API_KEY, 
                model="gpt-3.5-turbo", 
                temperature=0.3,
                api_base="https://models.github.ai/inference"
            )
            Settings.embed_model = OpenAIEmbedding(
                api_key=settings.OPENAI_API_KEY,
                api_base="https://models.github.ai/inference"
            )

            # Create temporary directory and save CSV file
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save uploaded file to temp directory
                temp_file_path = os.path.join(temp_dir, csv_file.name)
                csv_file.seek(0)  # Reset file pointer
                with open(temp_file_path, 'wb+') as temp_file:
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)
                
                # Use SimpleDirectoryReader to load the CSV
                reader = SimpleDirectoryReader(input_dir=temp_dir)
                documents = reader.load_data()
                
                # Add metadata to documents
                for doc in documents:
                    doc.metadata.update({
                        'company_id': str(company.id),
                        'company_name': company.name,
                        'upload_date': timezone.now().isoformat(),
                        'file_name': csv_file.name,
                        'bulk_upload_id': str(bulk_upload.id)
                    })
                
                # Create vector index from documents
                index = VectorStoreIndex.from_documents(documents)
                query_engine = index.as_query_engine(response_mode="tree_summarize")
                
                # Generate insights
                insights_query = f"""
                Analyze this CSV data from {csv_file.name} and provide:
                1. Summary of the data structure and content
                2. Key patterns and trends
                3. Notable records or outliers
                4. Data quality assessment
                5. Business insights and recommendations
                """
                
                insights = query_engine.query(insights_query)
                return str(insights)
                
        except Exception as e:
            logger.error(f"RAG analysis failed: {str(e)}")
            return f"RAG analysis failed: {str(e)}"
    
    @action(detail=True, methods=['post'], url_path='query')
    def query_data(self, request, pk=None):
        """
        Query the uploaded CSV data using AI
        
        Parameters:
        - query: Natural language query about the data
        
        Usage:
        POST /api/v1/bulk-uploads/{bulk_upload_id}/query/
        {
            "query": "What are the top 5 expenses?"
        }
        """
        try:
            bulk_upload = self.get_object()
            
            if bulk_upload.status != 'completed':
                return Response(
                    {'error': 'Upload is not completed yet'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            query_text = request.data.get('query')
            if not query_text:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # TODO: Implement querying logic with stored vector index
            # For now, return a placeholder response
            return Response({
                'bulk_upload_id': bulk_upload.id,
                'query': query_text,
                'answer': 'Query functionality will be implemented when vector index persistence is added.',
                'suggestions': [
                    'The vector index needs to be persisted to enable querying',
                    'Consider implementing vector store persistence with ChromaDB or similar',
                    'Current implementation recreates index on each upload'
                ]
            })
            
        except Exception as e:
            return Response(
                {'error': f'Query failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='upload-history')
    def upload_history(self, request):
        """Get upload history for the user's companies"""
        try:
            uploads = self.get_queryset().order_by('-created_at')
            
            # Filter by status if specified
            status_filter = request.query_params.get('status')
            if status_filter:
                uploads = uploads.filter(status=status_filter)
            
            # Pagination
            page_size = int(request.query_params.get('page_size', 20))
            page = int(request.query_params.get('page', 1))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            total_count = uploads.count()
            uploads_page = uploads[start_idx:end_idx]
            
            # Use the ViewSet's serializer class
            serializer = self.get_serializer(uploads_page, many=True)
            
            return Response({
                'results': serializer.data,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': end_idx < total_count,
                'has_previous': page > 1
            })
            
        except Exception as e:
            logger.error(f"Failed to retrieve upload history: {str(e)}")
            return Response(
                {'error': f'Failed to retrieve upload history: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        """Download a sample CSV template"""
        template_content = """date,description,amount,category,account_name
2025-08-01,Office Rent,-2500.00,Office Expenses,Business Checking
2025-08-02,Client Payment - Project A,5000.00,Revenue,Business Checking
2025-08-03,Marketing Campaign - Google Ads,-1200.00,Marketing,Business Credit
2025-08-04,Software Subscription - Adobe,-99.00,Software,Business Credit
2025-08-05,Client Payment - Project B,3500.00,Revenue,Business Checking"""
        
        response = Response(template_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_template.csv"'
        return response
