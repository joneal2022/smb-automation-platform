from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid


class Organization(models.Model):
    """Organization model for multi-tenant support"""
    
    PLAN_CHOICES = [
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    subscription_plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='starter')
    is_active = models.BooleanField(default=True)
    max_users = models.PositiveIntegerField(default=10)
    max_documents_per_month = models.PositiveIntegerField(default=1000)
    
    # Contact information
    contact_email = models.EmailField()
    phone_number = models.CharField(
        max_length=17,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid format")],
        blank=True
    )
    
    # Address
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    # Compliance
    gdpr_compliance_enabled = models.BooleanField(default=True)
    hipaa_compliance_enabled = models.BooleanField(default=False)
    data_retention_days = models.PositiveIntegerField(default=2555)  # 7 years default
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class User(AbstractUser):
    """Extended User model with role-based access and organization support"""
    
    ROLE_CHOICES = [
        ('business_owner', 'Business Owner/Manager'),
        ('operations_staff', 'Operations Staff'),
        ('document_processor', 'Document Processing Staff'),
        ('it_admin', 'IT Administrator'),
        ('customer_service', 'Customer Service Staff'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    # Profile information
    phone_number = models.CharField(
        max_length=17,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid format")],
        blank=True
    )
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    # Security settings
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret_key = models.CharField(max_length=32, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_reset_required = models.BooleanField(default=False)
    
    # Activity tracking
    last_activity = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    email_notifications = models.BooleanField(default=True)
    
    # Compliance tracking
    gdpr_consent_given = models.BooleanField(default=False)
    gdpr_consent_date = models.DateTimeField(null=True, blank=True)
    data_processing_consent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.organization.name})"
    
    @property
    def full_name(self):
        return self.get_full_name() or self.username
    
    def has_role(self, role):
        """Check if user has a specific role"""
        return self.role == role
    
    def can_access_feature(self, feature):
        """Role-based feature access control"""
        feature_permissions = {
            'business_owner': [
                'dashboard_executive', 'analytics_full', 'reports_financial', 
                'user_management', 'organization_settings', 'billing'
            ],
            'operations_staff': [
                'dashboard_operations', 'workflow_builder', 'workflow_management',
                'integration_management', 'document_processing', 'analytics_operational'
            ],
            'document_processor': [
                'dashboard_documents', 'document_upload', 'document_review',
                'data_extraction', 'batch_processing', 'quality_control'
            ],
            'it_admin': [
                'dashboard_admin', 'user_management', 'system_monitoring',
                'security_logs', 'integration_config', 'backup_management'
            ],
            'customer_service': [
                'dashboard_service', 'chatbot_management', 'customer_history',
                'escalation_management', 'response_templates'
            ],
        }
        
        return feature in feature_permissions.get(self.role, [])


class UserAuditLog(models.Model):
    """Audit log for user actions - GDPR/HIPAA compliance"""
    
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('password_change', 'Password Change'),
        ('profile_update', 'Profile Update'),
        ('document_access', 'Document Access'),
        ('document_download', 'Document Download'),
        ('workflow_create', 'Workflow Create'),
        ('workflow_execute', 'Workflow Execute'),
        ('data_export', 'Data Export'),
        ('settings_change', 'Settings Change'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50, blank=True)  # e.g., 'document', 'workflow'
    resource_id = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.created_at}"


class UserSession(models.Model):
    """Track user sessions for security and compliance"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"
