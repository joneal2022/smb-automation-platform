from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NodeTypeViewSet, WorkflowTemplateViewSet, WorkflowViewSet,
    WorkflowExecutionViewSet, WorkflowAuditLogViewSet
)

router = DefaultRouter()
router.register(r'node-types', NodeTypeViewSet, basename='nodetype')
router.register(r'templates', WorkflowTemplateViewSet, basename='workflowtemplate')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'executions', WorkflowExecutionViewSet, basename='workflowexecution')
router.register(r'audit-logs', WorkflowAuditLogViewSet, basename='workflowauditlog')

app_name = 'workflows'
urlpatterns = [
    path('', include(router.urls)),
]