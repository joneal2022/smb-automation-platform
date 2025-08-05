from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'document-types', views.DocumentTypeViewSet, basename='documenttype')
router.register(r'extractions', views.DocumentExtractionViewSet, basename='documentextraction')
router.register(r'batches', views.DocumentBatchViewSet, basename='documentbatch')

urlpatterns = [
    # ViewSet routes
    path('api/', include(router.urls)),
    
    # Custom endpoints
    path('api/upload/', views.upload_document, name='upload-document'),
    path('api/stats/', views.processing_stats, name='processing-stats'),
]