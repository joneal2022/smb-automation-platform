"""
Factory classes for generating test data
"""
import factory
import factory.fuzzy
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.documents.models import (
    DocumentType, Document, DocumentExtraction, 
    DocumentProcessingLog, DocumentBatch, DocumentBatchItem
)
from apps.workflows.models import (
    NodeType, WorkflowTemplate, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowNodeExecution, WorkflowAuditLog
)
from apps.users.models import Organization
import uuid
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone

User = get_user_model()


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
    
    name = factory.Faker('company')
    slug = factory.Faker('slug')
    subscription_plan = factory.Iterator(['starter', 'professional', 'enterprise'])
    contact_email = factory.Faker('email')
    max_users = factory.fuzzy.FuzzyInteger(10, 1000)
    max_documents_per_month = factory.fuzzy.FuzzyInteger(100, 10000)
    is_active = True


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    organization = factory.SubFactory(OrganizationFactory)
    role = factory.Iterator(['business_owner', 'operations_staff', 'document_processor', 'it_admin', 'customer_service'])
    
    @factory.post_generation
    def set_password(self, create, extracted, **kwargs):
        if create:
            self.set_password('testpass123')
            self.save()


class DocumentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentType
    
    name = factory.Iterator(['Invoice', 'Contract', 'Receipt', 'Form', 'Report'])
    description = factory.Faker('text', max_nb_chars=200)
    ocr_enabled = True
    ai_extraction_enabled = True
    extraction_template = factory.LazyFunction(lambda: {
        "fields": [
            {"name": "document_title", "type": "text", "description": "Main title"},
            {"name": "date", "type": "date", "description": "Document date"},
            {"name": "amount", "type": "currency", "description": "Total amount"}
        ]
    })
    validation_rules = factory.LazyFunction(lambda: {"required_fields": ["amount"]})
    required_fields = factory.LazyFunction(lambda: ["amount"])
    max_file_size_mb = 50
    allowed_extensions = factory.LazyFunction(lambda: ['pdf', 'png', 'jpg', 'jpeg'])
    is_active = True


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document
    
    original_filename = factory.Faker('file_name', extension='pdf')
    file = factory.LazyAttribute(lambda obj: SimpleUploadedFile(
        obj.original_filename,
        b'fake file content',
        content_type='application/pdf'
    ))
    file_size = factory.fuzzy.FuzzyInteger(1024, 10*1024*1024)  # 1KB to 10MB
    file_hash = factory.LazyFunction(lambda: uuid.uuid4().hex)
    mime_type = factory.Iterator(['application/pdf', 'image/png', 'image/jpeg'])
    document_type = factory.SubFactory(DocumentTypeFactory)
    status = factory.Iterator([
        'uploaded', 'processing', 'ocr_complete', 'extraction_complete',
        'review_required', 'approved', 'rejected', 'error'
    ])
    priority = factory.Iterator(['low', 'normal', 'high', 'urgent'])
    ocr_text = factory.Faker('text', max_nb_chars=1000)
    ocr_confidence = factory.fuzzy.FuzzyFloat(0.5, 1.0)
    ocr_language = 'en'
    uploaded_by = factory.SubFactory(UserFactory)
    tags = factory.LazyFunction(lambda: ['invoice', 'business'])
    metadata = factory.LazyFunction(lambda: {'source': 'upload', 'version': '1.0'})
    contains_pii = factory.Faker('boolean', chance_of_getting_true=30)
    contains_phi = factory.Faker('boolean', chance_of_getting_true=10)
    data_classification = factory.Iterator(['public', 'internal', 'confidential', 'restricted'])


class DocumentExtractionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentExtraction
    
    document = factory.SubFactory(DocumentFactory)
    field_name = factory.Iterator(['document_title', 'date', 'amount', 'vendor_name', 'total'])
    field_value = factory.Faker('word')
    field_type = factory.Iterator(['text', 'number', 'date', 'currency', 'email'])
    confidence = factory.fuzzy.FuzzyFloat(0.6, 1.0)
    bounding_box = factory.LazyFunction(lambda: {'x': 10, 'y': 20, 'width': 100, 'height': 30})
    is_verified = factory.Faker('boolean', chance_of_getting_true=70)
    original_value = factory.SelfAttribute('field_value')
    
    @factory.post_generation
    def set_verified_data(self, create, extracted, **kwargs):
        if create and self.is_verified:
            if not self.verified_by:
                self.verified_by = UserFactory()
            if not self.verified_at:
                self.verified_at = timezone.now()
            self.save()


class DocumentProcessingLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentProcessingLog
    
    document = factory.SubFactory(DocumentFactory)
    step = factory.Iterator([
        'upload', 'validation', 'classification', 'ocr', 
        'extraction', 'validation_rules', 'review', 'approval', 'error'
    ])
    status = factory.Iterator(['started', 'completed', 'failed', 'skipped'])
    message = factory.Faker('sentence')
    details = factory.LazyFunction(lambda: {'processing_time': 2.5, 'confidence': 0.95})
    duration_seconds = factory.fuzzy.FuzzyFloat(0.1, 10.0)
    performed_by = factory.SubFactory(UserFactory)


class DocumentBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentBatch
    
    name = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=300)
    document_type = factory.SubFactory(DocumentTypeFactory)
    auto_approve_threshold = factory.fuzzy.FuzzyFloat(0.8, 0.95)
    status = factory.Iterator(['created', 'processing', 'completed', 'failed', 'partially_completed'])
    total_documents = factory.fuzzy.FuzzyInteger(1, 50)
    processed_documents = factory.LazyAttribute(lambda obj: min(obj.total_documents, 
                                                               factory.fuzzy.FuzzyInteger(0, obj.total_documents).fuzz()))
    successful_documents = factory.LazyAttribute(lambda obj: min(obj.processed_documents,
                                                               factory.fuzzy.FuzzyInteger(0, obj.processed_documents).fuzz()))
    failed_documents = factory.LazyAttribute(lambda obj: obj.processed_documents - obj.successful_documents)
    created_by = factory.SubFactory(UserFactory)


class DocumentBatchItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentBatchItem
    
    batch = factory.SubFactory(DocumentBatchFactory)
    document = factory.SubFactory(DocumentFactory)
    processing_order = factory.Sequence(lambda n: n + 1)


# Specialized factories for specific test scenarios
class PendingDocumentFactory(DocumentFactory):
    """Factory for documents needing processing"""
    status = 'uploaded'
    ocr_text = ''
    ocr_confidence = None


class ReviewRequiredDocumentFactory(DocumentFactory):
    """Factory for documents requiring manual review"""
    status = 'review_required'
    ocr_confidence = factory.fuzzy.FuzzyFloat(0.5, 0.79)  # Low confidence


class CompletedDocumentFactory(DocumentFactory):
    """Factory for fully processed documents"""
    status = 'approved'
    ocr_confidence = factory.fuzzy.FuzzyFloat(0.9, 1.0)  # High confidence
    processing_completed_at = factory.Faker('date_time', tzinfo=dt_timezone.utc)


class ErrorDocumentFactory(DocumentFactory):
    """Factory for documents with processing errors"""
    status = 'error'
    error_message = factory.Faker('sentence')
    retry_count = factory.fuzzy.FuzzyInteger(1, 3)


# Test file factories
class TestFileFactory:
    """Factory for creating test files"""
    
    @staticmethod
    def create_pdf_file(filename='test.pdf', content=b'%PDF-1.4 fake pdf content'):
        return SimpleUploadedFile(filename, content, content_type='application/pdf')
    
    @staticmethod
    def create_image_file(filename='test.jpg', content=b'fake image content'):
        return SimpleUploadedFile(filename, content, content_type='image/jpeg')
    
    @staticmethod
    def create_png_file(filename='test.png', content=b'fake png content'):
        return SimpleUploadedFile(filename, content, content_type='image/png')
    
    @staticmethod
    def create_large_file(filename='large.pdf', size_mb=60):
        content = b'0' * (size_mb * 1024 * 1024)
        return SimpleUploadedFile(filename, content, content_type='application/pdf')
    
    @staticmethod
    def create_invalid_file(filename='invalid.txt', content=b'invalid file type'):
        return SimpleUploadedFile(filename, content, content_type='text/plain')


# Workflow Factory Classes
class NodeTypeFactory(factory.django.DjangoModelFactory):
    """Factory for NodeType model."""
    
    class Meta:
        model = NodeType
    
    name = factory.Iterator([
        'Start Process', 'End Process', 'Document Processing', 'Decision Point',
        'Approval Required', 'Send Notification', 'Integration Call', 'Data Processing'
    ])
    type = factory.Iterator([
        'start', 'end', 'process', 'decision', 'approval', 
        'document', 'integration', 'notification'
    ])
    icon = factory.Iterator(['play', 'stop', 'cog', 'git-branch', 'check-circle', 'file', 'link', 'bell'])
    color = factory.Iterator(['#28a745', '#dc3545', '#007bff', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14', '#20c997'])
    description = factory.Faker('sentence')
    config_schema = factory.LazyFunction(lambda: {
        "properties": {
            "timeout": {"type": "number", "default": 300},
            "retry_count": {"type": "number", "default": 3}
        }
    })
    requires_user_action = factory.Iterator([True, False])
    allows_multiple_outputs = factory.Iterator([True, False])


class WorkflowTemplateFactory(factory.django.DjangoModelFactory):
    """Factory for WorkflowTemplate model."""
    
    class Meta:
        model = WorkflowTemplate
    
    name = factory.Iterator([
        'Invoice Processing', 'Customer Onboarding', 'Contract Review',
        'Expense Processing', 'Support Ticket Resolution'
    ])
    description = factory.Faker('text', max_nb_chars=500)
    category = factory.Iterator([
        'document_processing', 'approval', 'customer_service', 
        'integration', 'compliance'
    ])
    definition = factory.LazyFunction(lambda: {
        "nodes": [
            {
                "node_id": "start_1",
                "name": "Start Process",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "config": {}
            },
            {
                "node_id": "process_1",
                "name": "Process Document",
                "type": "process",
                "position": {"x": 300, "y": 100},
                "config": {"timeout_seconds": 300}
            },
            {
                "node_id": "end_1",
                "name": "End Process",
                "type": "end",
                "position": {"x": 500, "y": 100},
                "config": {}
            }
        ],
        "edges": [
            {
                "source": "start_1",
                "target": "process_1",
                "condition_type": "always"
            },
            {
                "source": "process_1",
                "target": "end_1",
                "condition_type": "success"
            }
        ]
    })
    setup_time_minutes = factory.fuzzy.FuzzyInteger(15, 120)
    complexity_level = factory.fuzzy.FuzzyInteger(1, 5)
    tags = factory.LazyFunction(lambda: ['business', 'automation', 'process'])
    usage_count = factory.fuzzy.FuzzyInteger(0, 100)
    is_active = True
    created_by = factory.SubFactory(UserFactory)


class WorkflowFactory(factory.django.DjangoModelFactory):
    """Factory for Workflow model."""
    
    class Meta:
        model = Workflow
    
    name = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=300)
    created_by = factory.SubFactory(UserFactory)
    status = factory.Iterator(['draft', 'active', 'paused', 'inactive', 'archived'])
    trigger_type = factory.Iterator(['manual', 'schedule', 'event', 'webhook', 'document_upload'])
    definition = factory.LazyFunction(lambda: {
        "nodes": [],
        "edges": [],
        "version": 1
    })
    template = factory.SubFactory(WorkflowTemplateFactory)
    schedule_config = factory.LazyFunction(lambda: {"interval": "daily", "time": "09:00"})
    total_executions = factory.fuzzy.FuzzyInteger(0, 1000)
    successful_executions = factory.LazyAttribute(
        lambda obj: factory.fuzzy.FuzzyInteger(0, obj.total_executions).fuzz()
    )
    failed_executions = factory.LazyAttribute(
        lambda obj: obj.total_executions - obj.successful_executions
    )
    average_duration_seconds = factory.fuzzy.FuzzyFloat(1.0, 300.0)
    
    @factory.post_generation
    def assigned_users(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            for user in extracted:
                self.assigned_users.add(user)
        else:
            # Add the creator as an assigned user
            self.assigned_users.add(self.created_by)


class WorkflowNodeFactory(factory.django.DjangoModelFactory):
    """Factory for WorkflowNode model."""
    
    class Meta:
        model = WorkflowNode
    
    workflow = factory.SubFactory(WorkflowFactory)
    node_type = factory.SubFactory(NodeTypeFactory)
    node_id = factory.Sequence(lambda n: f"node_{n}")
    name = factory.Faker('sentence', nb_words=3)
    description = factory.Faker('sentence')
    position_x = factory.fuzzy.FuzzyFloat(50, 800)
    position_y = factory.fuzzy.FuzzyFloat(50, 600)
    config = factory.LazyFunction(lambda: {
        "timeout_seconds": 300,
        "retry_count": 3,
        "priority": "normal"
    })
    is_required = True
    timeout_seconds = 300
    retry_count = 3
    assigned_user = factory.SubFactory(UserFactory)


class WorkflowEdgeFactory(factory.django.DjangoModelFactory):
    """Factory for WorkflowEdge model."""
    
    class Meta:
        model = WorkflowEdge
    
    workflow = factory.SubFactory(WorkflowFactory)
    source_node = factory.SubFactory(WorkflowNodeFactory)
    target_node = factory.SubFactory(WorkflowNodeFactory)
    condition_type = factory.Iterator([
        'always', 'success', 'failure', 'conditional', 
        'approval_yes', 'approval_no'
    ])
    condition_config = factory.LazyFunction(lambda: {"threshold": 0.8})
    label = factory.Faker('word')


class WorkflowExecutionFactory(factory.django.DjangoModelFactory):
    """Factory for WorkflowExecution model."""
    
    class Meta:
        model = WorkflowExecution
    
    workflow = factory.SubFactory(WorkflowFactory)
    status = factory.Iterator(['queued', 'running', 'paused', 'completed', 'failed', 'cancelled'])
    triggered_by = factory.SubFactory(UserFactory)
    trigger_data = factory.LazyFunction(lambda: {"source": "test", "batch_id": str(uuid.uuid4())})
    current_node = factory.SubFactory(WorkflowNodeFactory)
    context_data = factory.LazyFunction(lambda: {
        "variables": {"user_id": 123, "document_count": 5},
        "metadata": {"start_time": timezone.now().isoformat()}
    })
    completed_at = factory.Maybe(
        'status',
        yes_declaration=factory.Faker('date_time', tzinfo=dt_timezone.utc),
        no_declaration=None,
        condition=lambda obj: obj.status in ['completed', 'failed', 'cancelled']
    )
    duration_seconds = factory.Maybe(
        'completed_at',
        yes_declaration=factory.fuzzy.FuzzyFloat(1.0, 600.0),
        no_declaration=None
    )
    error_message = factory.Maybe(
        'status',
        yes_declaration=factory.Faker('sentence'),
        no_declaration='',
        condition=lambda obj: obj.status == 'failed'
    )
    error_details = factory.Maybe(
        'status',
        yes_declaration=factory.LazyFunction(lambda: {
            "error_type": "ProcessingError",
            "stack_trace": "Mock stack trace"
        }),
        no_declaration=factory.LazyFunction(dict),
        condition=lambda obj: obj.status == 'failed'
    )


class WorkflowNodeExecutionFactory(factory.django.DjangoModelFactory):
    """Factory for WorkflowNodeExecution model."""
    
    class Meta:
        model = WorkflowNodeExecution
    
    workflow_execution = factory.SubFactory(WorkflowExecutionFactory)
    workflow_node = factory.SubFactory(WorkflowNodeFactory)
    status = factory.Iterator(['pending', 'running', 'completed', 'failed', 'skipped', 'waiting_approval'])
    input_data = factory.LazyFunction(lambda: {"input_param": "test_value"})
    output_data = factory.LazyFunction(lambda: {"result": "success", "processed_count": 5})
    started_at = factory.Maybe(
        'status',
        yes_declaration=factory.Faker('date_time', tzinfo=dt_timezone.utc),
        no_declaration=None,
        condition=lambda obj: obj.status != 'pending'
    )
    completed_at = factory.Maybe(
        'status',
        yes_declaration=factory.Faker('date_time', tzinfo=dt_timezone.utc),
        no_declaration=None,
        condition=lambda obj: obj.status in ['completed', 'failed', 'skipped']
    )
    duration_seconds = factory.Maybe(
        'completed_at',
        yes_declaration=factory.fuzzy.FuzzyFloat(0.1, 60.0),
        no_declaration=None
    )
    error_message = factory.Maybe(
        'status',
        yes_declaration=factory.Faker('sentence'),
        no_declaration='',
        condition=lambda obj: obj.status == 'failed'
    )
    retry_count = factory.fuzzy.FuzzyInteger(0, 3)
    approved_by = factory.Maybe(
        'status',
        yes_declaration=factory.SubFactory(UserFactory),
        no_declaration=None,
        condition=lambda obj: obj.status == 'waiting_approval'
    )
    approval_notes = factory.Maybe(
        'approved_by',
        yes_declaration=factory.Faker('sentence'),
        no_declaration='',
        condition=lambda obj: obj.approved_by is not None
    )


class WorkflowAuditLogFactory(factory.django.DjangoModelFactory):
    """Factory for WorkflowAuditLog model."""
    
    class Meta:
        model = WorkflowAuditLog
    
    workflow = factory.SubFactory(WorkflowFactory)
    workflow_execution = factory.SubFactory(WorkflowExecutionFactory)
    user = factory.SubFactory(UserFactory)
    user_ip = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')
    action = factory.Iterator([
        'workflow_created', 'workflow_updated', 'workflow_activated',
        'workflow_deactivated', 'execution_started', 'execution_completed',
        'execution_failed', 'node_approved', 'node_rejected',
        'data_accessed', 'data_modified'
    ])
    description = factory.Faker('sentence')
    metadata = factory.LazyFunction(lambda: {
        "browser": "Chrome",
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4())
    })


# Specialized workflow factories for specific test scenarios
class ActiveWorkflowFactory(WorkflowFactory):
    """Factory for active workflows ready for execution."""
    status = 'active'
    
    @factory.post_generation
    def add_basic_nodes(self, create, extracted, **kwargs):
        if not create:
            return
        
        # Create start node
        start_node_type = NodeTypeFactory(type='start')
        start_node = WorkflowNodeFactory(
            workflow=self,
            node_type=start_node_type,
            node_id='start_1',
            name='Start Process',
            position_x=100,
            position_y=100
        )
        
        # Create end node
        end_node_type = NodeTypeFactory(type='end')
        end_node = WorkflowNodeFactory(
            workflow=self,
            node_type=end_node_type,
            node_id='end_1',
            name='End Process',
            position_x=300,
            position_y=100
        )
        
        # Create edge
        WorkflowEdgeFactory(
            workflow=self,
            source_node=start_node,
            target_node=end_node,
            condition_type='always'
        )


class CompletedWorkflowExecutionFactory(WorkflowExecutionFactory):
    """Factory for completed workflow executions."""
    status = 'completed'
    completed_at = factory.Faker('date_time', tzinfo=dt_timezone.utc)
    duration_seconds = factory.fuzzy.FuzzyFloat(10.0, 300.0)
    
    @factory.post_generation
    def add_node_executions(self, create, extracted, **kwargs):
        if not create:
            return
        
        # Create successful node executions for all workflow nodes
        for node in self.workflow.nodes.all():
            WorkflowNodeExecutionFactory(
                workflow_execution=self,
                workflow_node=node,
                status='completed',
                started_at=self.started_at,
                completed_at=self.completed_at,
                duration_seconds=factory.fuzzy.FuzzyFloat(1.0, 10.0).fuzz()
            )


class FailedWorkflowExecutionFactory(WorkflowExecutionFactory):
    """Factory for failed workflow executions."""
    status = 'failed'
    completed_at = factory.Faker('date_time', tzinfo=dt_timezone.utc)
    duration_seconds = factory.fuzzy.FuzzyFloat(1.0, 60.0)
    error_message = factory.Faker('sentence')
    error_details = factory.LazyFunction(lambda: {
        "error_type": "NodeExecutionError",
        "failed_node": "process_1",
        "stack_trace": "Mock error stack trace"
    })


class InvoiceProcessingTemplateFactory(WorkflowTemplateFactory):
    """Factory for Invoice Processing workflow template."""
    name = 'Invoice Processing Workflow'
    category = 'document_processing'
    tags = ['invoice', 'accounting', 'approval']
    definition = factory.LazyFunction(lambda: {
        "nodes": [
            {
                "node_id": "start_1",
                "name": "Start Invoice Processing",
                "type": "start",
                "position": {"x": 100, "y": 200},
                "config": {}
            },
            {
                "node_id": "document_1", 
                "name": "Extract Invoice Data",
                "type": "document",
                "position": {"x": 300, "y": 200},
                "config": {"ocr_enabled": True, "ai_extraction": True}
            },
            {
                "node_id": "approval_1",
                "name": "Finance Approval",
                "type": "approval",
                "position": {"x": 500, "y": 200},
                "config": {"approver_role": "finance_manager", "timeout": 86400}
            },
            {
                "node_id": "integration_1",
                "name": "Update Accounting System",
                "type": "integration",
                "position": {"x": 700, "y": 200},
                "config": {"system": "quickbooks", "action": "create_bill"}
            },
            {
                "node_id": "end_1",
                "name": "Invoice Processed",
                "type": "end",
                "position": {"x": 900, "y": 200},
                "config": {}
            }
        ],
        "edges": [
            {"source": "start_1", "target": "document_1", "condition_type": "always"},
            {"source": "document_1", "target": "approval_1", "condition_type": "success"},
            {"source": "approval_1", "target": "integration_1", "condition_type": "approval_yes"},
            {"source": "integration_1", "target": "end_1", "condition_type": "success"}
        ]
    })


# Performance testing factories
class BulkWorkflowFactory:
    """Factory for creating bulk workflows for performance testing."""
    
    @staticmethod
    def create_workflows_batch(count=100, with_executions=True):
        """Create a batch of workflows for performance testing."""
        workflows = []
        
        for i in range(count):
            workflow = ActiveWorkflowFactory(
                name=f'Performance Test Workflow {i+1}',
                description=f'Performance testing workflow number {i+1}'
            )
            workflows.append(workflow)
            
            if with_executions:
                # Create some executions for each workflow
                for j in range(factory.fuzzy.FuzzyInteger(1, 10).fuzz()):
                    if j % 2 == 0:
                        CompletedWorkflowExecutionFactory(workflow=workflow)
                    else:
                        WorkflowExecutionFactory(
                            workflow=workflow,
                            status=factory.Iterator(['queued', 'running']).fuzz()
                        )
        
        return workflows
    
    @staticmethod
    def create_concurrent_executions(workflow, count=50):
        """Create multiple concurrent executions for a workflow."""
        executions = []
        
        for i in range(count):
            execution = WorkflowExecutionFactory(
                workflow=workflow,
                status='running',
                triggered_by=UserFactory()
            )
            executions.append(execution)
        
        return executions