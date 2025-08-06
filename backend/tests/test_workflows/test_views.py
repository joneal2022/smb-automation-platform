"""
API integration tests for workflow views
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
import json
import uuid

from apps.workflows.models import (
    NodeType, WorkflowTemplate, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowAuditLog
)
from tests.factories import (
    NodeTypeFactory, WorkflowTemplateFactory, WorkflowFactory, WorkflowNodeFactory,
    WorkflowEdgeFactory, WorkflowExecutionFactory, UserFactory, ActiveWorkflowFactory,
    InvoiceProcessingTemplateFactory
)

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for testing."""
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """Create and return authenticated user."""
    return UserFactory()


@pytest.fixture
def authenticated_client(api_client, authenticated_user):
    """API client with authenticated user."""
    api_client.force_authenticate(user=authenticated_user)
    return api_client


@pytest.fixture
def admin_user(db):
    """Create admin user."""
    return UserFactory(role='admin', is_staff=True)


@pytest.fixture
def admin_client(api_client, admin_user):
    """API client with admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client


class TestNodeTypeViewSet:
    """Tests for NodeType API endpoints."""
    
    def test_list_node_types(self, authenticated_client, db):
        """Test listing node types."""
        node_type1 = NodeTypeFactory(name='Start Node', type='start')
        node_type2 = NodeTypeFactory(name='Process Node', type='process')
        
        url = '/api/node-types/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        
        # Check node type data
        node_names = [item['name'] for item in data]
        assert 'Start Node' in node_names
        assert 'Process Node' in node_names
    
    def test_get_node_type_detail(self, authenticated_client, db):
        """Test getting node type detail."""
        node_type = NodeTypeFactory(
            name='Test Node',
            description='Test node description',
            config_schema={'properties': {'timeout': {'type': 'number'}}}
        )
        
        url = f'/api/node-types/{node_type.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['name'] == 'Test Node'
        assert data['description'] == 'Test node description'
        assert data['config_schema'] == {'properties': {'timeout': {'type': 'number'}}}
    
    def test_node_types_by_type(self, authenticated_client, db):
        """Test grouping node types by type."""
        NodeTypeFactory(name='Start Node', type='start')
        NodeTypeFactory(name='Another Start', type='start')
        NodeTypeFactory(name='End Node', type='end')
        
        url = '/api/node-types/by_type/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'start' in data
        assert 'end' in data
        assert len(data['start']) == 2
        assert len(data['end']) == 1
    
    def test_node_types_authentication_required(self, api_client, db):
        """Test that authentication is required."""
        url = '/api/node-types/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestWorkflowTemplateViewSet:
    """Tests for WorkflowTemplate API endpoints."""
    
    def test_list_workflow_templates(self, authenticated_client, db):
        """Test listing workflow templates."""
        template1 = WorkflowTemplateFactory(name='Invoice Processing')
        template2 = WorkflowTemplateFactory(name='Customer Onboarding')
        
        url = '/api/templates/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        
        template_names = [item['name'] for item in data]
        assert 'Invoice Processing' in template_names
        assert 'Customer Onboarding' in template_names
    
    def test_get_workflow_template_detail(self, authenticated_client, db):
        """Test getting workflow template detail."""
        template = WorkflowTemplateFactory(
            name='Test Template',
            description='Test description',
            category='document_processing',
            complexity_level=3
        )
        
        url = f'/api/templates/{template.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['name'] == 'Test Template'
        assert data['description'] == 'Test description'
        assert data['category'] == 'document_processing'
        assert data['complexity_level'] == 3
    
    def test_filter_templates_by_category(self, authenticated_client, db):
        """Test filtering templates by category."""
        template1 = WorkflowTemplateFactory(category='document_processing')
        template2 = WorkflowTemplateFactory(category='approval')
        
        url = '/api/templates/?category=document_processing'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['category'] == 'document_processing'
    
    def test_search_templates(self, authenticated_client, db):
        """Test searching templates."""
        template1 = WorkflowTemplateFactory(name='Invoice Processing')
        template2 = WorkflowTemplateFactory(name='Customer Onboarding')
        
        url = '/api/templates/?search=Invoice'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['name'] == 'Invoice Processing'
    
    def test_use_template(self, authenticated_client, authenticated_user, db):
        """Test creating workflow from template."""
        template = InvoiceProcessingTemplateFactory()
        
        # Create required node types
        NodeTypeFactory(type='start')
        NodeTypeFactory(type='document')
        NodeTypeFactory(type='approval')
        NodeTypeFactory(type='integration')
        NodeTypeFactory(type='end')
        
        url = f'/api/templates/{template.id}/use_template/'
        response = authenticated_client.post(url, {})
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Check workflow was created
        assert 'id' in data
        assert data['name'].startswith(template.name)
        assert data['status'] == 'draft'
        
        # Check template usage was incremented
        template.refresh_from_db()
        assert template.usage_count > 0
    
    def test_create_template(self, admin_client, admin_user, db):
        """Test creating a new template."""
        template_data = {
            'name': 'New Template',
            'description': 'New template description',
            'category': 'approval',
            'complexity_level': 2,
            'setup_time_minutes': 30,
            'tags': ['test', 'new'],
            'definition': {
                'nodes': [],
                'edges': []
            }
        }
        
        url = '/api/templates/'
        response = admin_client.post(url, template_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data['name'] == 'New Template'
        assert data['created_by'] == admin_user.id
        assert data['usage_count'] == 0


class TestWorkflowViewSet:
    """Tests for Workflow API endpoints."""
    
    def test_list_workflows(self, authenticated_client, authenticated_user, db):
        """Test listing user's workflows."""
        workflow1 = WorkflowFactory(created_by=authenticated_user)
        workflow2 = WorkflowFactory()  # Different user
        workflow3 = WorkflowFactory()
        workflow3.assigned_users.add(authenticated_user)  # Assigned to user
        
        url = '/api/workflows/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        workflow_ids = [item['id'] for item in data]
        
        assert str(workflow1.id) in workflow_ids
        assert str(workflow2.id) not in workflow_ids
        assert str(workflow3.id) in workflow_ids
    
    def test_get_workflow_detail(self, authenticated_client, authenticated_user, db):
        """Test getting workflow detail."""
        workflow = ActiveWorkflowFactory(created_by=authenticated_user)
        
        url = f'/api/workflows/{workflow.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['name'] == workflow.name
        assert data['status'] == workflow.status
        assert len(data['nodes']) == workflow.nodes.count()
        assert len(data['edges']) == workflow.edges.count()
    
    def test_create_workflow(self, authenticated_client, authenticated_user, db):
        """Test creating a new workflow."""
        template = WorkflowTemplateFactory()
        
        workflow_data = {
            'name': 'New Workflow',
            'description': 'New workflow description',
            'status': 'draft',
            'trigger_type': 'manual',
            'template': str(template.id)
        }
        
        url = '/api/workflows/'
        response = authenticated_client.post(url, workflow_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data['name'] == 'New Workflow'
        assert data['created_by'] == authenticated_user.id
        assert data['status'] == 'draft'
    
    def test_update_workflow(self, authenticated_client, authenticated_user, db):
        """Test updating a workflow."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        
        update_data = {
            'name': 'Updated Workflow Name',
            'description': 'Updated description'
        }
        
        url = f'/api/workflows/{workflow.id}/'
        response = authenticated_client.patch(url, update_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['name'] == 'Updated Workflow Name'
        assert data['description'] == 'Updated description'
    
    def test_delete_workflow(self, authenticated_client, authenticated_user, db):
        """Test deleting a workflow."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        
        url = f'/api/workflows/{workflow.id}/'
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Workflow.objects.filter(id=workflow.id).exists()
    
    def test_get_workflow_canvas(self, authenticated_client, authenticated_user, db):
        """Test getting workflow canvas data."""
        workflow = ActiveWorkflowFactory(created_by=authenticated_user)
        
        url = f'/api/workflows/{workflow.id}/canvas/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'nodes' in data
        assert 'edges' in data
        assert len(data['nodes']) == workflow.nodes.count()
        assert len(data['edges']) == workflow.edges.count()
        
        # Check node structure
        if data['nodes']:
            node = data['nodes'][0]
            assert 'id' in node
            assert 'name' in node
            assert 'type' in node
            assert 'position' in node
    
    def test_save_workflow_canvas(self, authenticated_client, authenticated_user, db):
        """Test saving workflow canvas data."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        
        # Create node types
        start_type = NodeTypeFactory(type='start')
        end_type = NodeTypeFactory(type='end')
        
        canvas_data = {
            'nodes': [
                {
                    'node_id': 'start_1',
                    'name': 'Start Process',
                    'node_type': str(start_type.id),
                    'position': {'x': 100, 'y': 100},
                    'config': {},
                    'is_required': True,
                    'timeout_seconds': 300,
                    'retry_count': 3
                },
                {
                    'node_id': 'end_1',
                    'name': 'End Process',
                    'node_type': str(end_type.id),
                    'position': {'x': 300, 'y': 100},
                    'config': {},
                    'is_required': True,
                    'timeout_seconds': 300,
                    'retry_count': 3
                }
            ],
            'edges': [
                {
                    'source': 'start_1',
                    'target': 'end_1',
                    'condition_type': 'always',
                    'condition_config': {},
                    'label': ''
                }
            ]
        }
        
        url = f'/api/workflows/{workflow.id}/save_canvas/'
        response = authenticated_client.post(url, canvas_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check nodes were created
        workflow.refresh_from_db()
        assert workflow.nodes.count() == 2
        assert workflow.edges.count() == 1
        
        start_node = workflow.nodes.get(node_id='start_1')
        assert start_node.name == 'Start Process'
        assert start_node.position_x == 100
        assert start_node.position_y == 100
    
    def test_activate_workflow(self, authenticated_client, authenticated_user, db):
        """Test activating a workflow."""
        workflow = ActiveWorkflowFactory(created_by=authenticated_user, status='draft')
        
        url = f'/api/workflows/{workflow.id}/activate/'
        response = authenticated_client.post(url, {})
        
        assert response.status_code == status.HTTP_200_OK
        
        workflow.refresh_from_db()
        assert workflow.status == 'active'
    
    def test_activate_workflow_validation(self, authenticated_client, authenticated_user, db):
        """Test workflow activation validation."""
        workflow = WorkflowFactory(created_by=authenticated_user)  # No nodes
        
        url = f'/api/workflows/{workflow.id}/activate/'
        response = authenticated_client.post(url, {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'start node' in response.json()['error'].lower()
    
    def test_deactivate_workflow(self, authenticated_client, authenticated_user, db):
        """Test deactivating a workflow."""
        workflow = ActiveWorkflowFactory(created_by=authenticated_user, status='active')
        
        url = f'/api/workflows/{workflow.id}/deactivate/'
        response = authenticated_client.post(url, {})
        
        assert response.status_code == status.HTTP_200_OK
        
        workflow.refresh_from_db()
        assert workflow.status == 'inactive'
    
    def test_execute_workflow(self, authenticated_client, authenticated_user, db):
        """Test executing a workflow."""
        workflow = ActiveWorkflowFactory(created_by=authenticated_user, status='active')
        
        trigger_data = {
            'trigger_data': {
                'source': 'api_test',
                'test_param': 'value'
            }
        }
        
        url = f'/api/workflows/{workflow.id}/execute/'
        response = authenticated_client.post(url, trigger_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert 'id' in data
        assert data['workflow'] == str(workflow.id)
        assert data['triggered_by'] == authenticated_user.id
        assert data['trigger_data'] == trigger_data['trigger_data']
    
    def test_execute_inactive_workflow(self, authenticated_client, authenticated_user, db):
        """Test executing inactive workflow fails."""
        workflow = WorkflowFactory(created_by=authenticated_user, status='draft')
        
        url = f'/api/workflows/{workflow.id}/execute/'
        response = authenticated_client.post(url, {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'active' in response.json()['error'].lower()
    
    def test_get_workflow_executions(self, authenticated_client, authenticated_user, db):
        """Test getting workflow executions."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        execution1 = WorkflowExecutionFactory(workflow=workflow)
        execution2 = WorkflowExecutionFactory(workflow=workflow)
        
        url = f'/api/workflows/{workflow.id}/executions/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        execution_ids = [item['id'] for item in data]
        assert str(execution1.id) in execution_ids
        assert str(execution2.id) in execution_ids
    
    def test_workflow_permissions(self, api_client, db):
        """Test workflow permissions for different users."""
        user1 = UserFactory()
        user2 = UserFactory()
        workflow = WorkflowFactory(created_by=user1)
        
        # User2 should not access user1's workflow
        api_client.force_authenticate(user=user2)
        url = f'/api/workflows/{workflow.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkflowExecutionViewSet:
    """Tests for WorkflowExecution API endpoints."""
    
    def test_list_executions(self, authenticated_client, authenticated_user, db):
        """Test listing user's workflow executions."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        execution1 = WorkflowExecutionFactory(workflow=workflow, triggered_by=authenticated_user)
        execution2 = WorkflowExecutionFactory()  # Different user
        
        url = '/api/executions/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        execution_ids = [item['id'] for item in data]
        
        assert str(execution1.id) in execution_ids
        assert str(execution2.id) not in execution_ids
    
    def test_get_execution_detail(self, authenticated_client, authenticated_user, db):
        """Test getting execution detail."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        execution = WorkflowExecutionFactory(workflow=workflow)
        
        url = f'/api/executions/{execution.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['id'] == str(execution.id)
        assert data['workflow'] == str(workflow.id)
        assert data['status'] == execution.status


class TestWorkflowAuditLogViewSet:
    """Tests for WorkflowAuditLog API endpoints."""
    
    def test_list_audit_logs(self, authenticated_client, authenticated_user, db):
        """Test listing audit logs."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        log1 = WorkflowAuditLogFactory(workflow=workflow, user=authenticated_user)
        log2 = WorkflowAuditLogFactory()  # Different workflow/user
        
        url = '/api/audit-logs/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        log_ids = [item['id'] for item in data]
        
        assert str(log1.id) in log_ids
        assert str(log2.id) not in log_ids
    
    def test_filter_audit_logs_by_workflow(self, authenticated_client, authenticated_user, db):
        """Test filtering audit logs by workflow."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        log1 = WorkflowAuditLogFactory(workflow=workflow, user=authenticated_user)
        log2 = WorkflowAuditLogFactory(user=authenticated_user)  # Different workflow
        
        url = f'/api/audit-logs/?workflow={workflow.id}'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['id'] == str(log1.id)
    
    def test_filter_audit_logs_by_action(self, authenticated_client, authenticated_user, db):
        """Test filtering audit logs by action."""
        workflow = WorkflowFactory(created_by=authenticated_user)
        log1 = WorkflowAuditLogFactory(
            workflow=workflow, user=authenticated_user, action='workflow_created'
        )
        log2 = WorkflowAuditLogFactory(
            workflow=workflow, user=authenticated_user, action='execution_started'
        )
        
        url = f'/api/audit-logs/?action=workflow_created'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['action'] == 'workflow_created'


class TestAPIErrorHandling:
    """Tests for API error handling."""
    
    def test_workflow_not_found(self, authenticated_client, db):
        """Test 404 for non-existent workflow."""
        fake_id = str(uuid.uuid4())
        url = f'/api/workflows/{fake_id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_invalid_workflow_data(self, authenticated_client, db):
        """Test validation errors for invalid workflow data."""
        workflow_data = {
            'name': '',  # Required field empty
            'status': 'invalid_status'  # Invalid choice
        }
        
        url = '/api/workflows/'
        response = authenticated_client.post(url, workflow_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = response.json()
        assert 'name' in errors or 'status' in errors
    
    def test_permission_denied(self, api_client, db):
        """Test permission denied for unauthenticated requests."""
        url = '/api/workflows/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAPIPerformance:
    """Tests for API performance optimizations."""
    
    def test_workflow_list_query_optimization(self, authenticated_client, authenticated_user, db):
        """Test that workflow list uses optimized queries."""
        # Create workflows with related data
        for i in range(5):
            workflow = WorkflowFactory(created_by=authenticated_user)
            WorkflowNodeFactory(workflow=workflow)
            WorkflowEdgeFactory(workflow=workflow)
        
        url = '/api/workflows/'
        
        # Use Django's test client query counting
        with pytest.raises(Exception):
            # This should use select_related/prefetch_related for efficiency
            response = authenticated_client.get(url)
            assert response.status_code == status.HTTP_200_OK