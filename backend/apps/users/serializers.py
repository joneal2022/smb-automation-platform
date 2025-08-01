from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Organization, UserAuditLog


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'subscription_plan', 'is_active',
            'max_users', 'max_documents_per_month', 'contact_email',
            'phone_number', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country',
            'gdpr_compliance_enabled', 'hipaa_compliance_enabled',
            'data_retention_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    organization_name = serializers.CharField(write_only=True, required=False)
    gdpr_consent = serializers.BooleanField(write_only=True, required=True)
    data_processing_consent = serializers.BooleanField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password',
            'password_confirm', 'phone_number', 'job_title', 'department',
            'role', 'organization_name', 'gdpr_consent', 'data_processing_consent'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        if not attrs.get('gdpr_consent'):
            raise serializers.ValidationError("GDPR consent is required")
        
        if not attrs.get('data_processing_consent'):
            raise serializers.ValidationError("Data processing consent is required")
        
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        organization_name = validated_data.pop('organization_name', None)
        gdpr_consent = validated_data.pop('gdpr_consent')
        data_processing_consent = validated_data.pop('data_processing_consent')
        
        # Create or get organization
        if organization_name:
            organization, created = Organization.objects.get_or_create(
                name=organization_name,
                defaults={
                    'slug': organization_name.lower().replace(' ', '-'),
                    'contact_email': validated_data['email']
                }
            )
        else:
            # If no organization provided, create a default one
            organization = Organization.objects.create(
                name=f"{validated_data['first_name']} {validated_data['last_name']}'s Organization",
                slug=f"{validated_data['username']}-org",
                contact_email=validated_data['email']
            )
        
        # Create user
        user = User.objects.create_user(
            password=password,
            organization=organization,
            gdpr_consent_given=gdpr_consent,
            data_processing_consent=data_processing_consent,
            **validated_data
        )
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            if user.account_locked_until:
                from django.utils import timezone
                if timezone.now() < user.account_locked_until:
                    raise serializers.ValidationError('Account is temporarily locked')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information"""
    
    organization = OrganizationSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone_number', 'job_title', 'department',
            'role', 'organization', 'mfa_enabled', 'timezone',
            'language', 'email_notifications', 'last_activity',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'username', 'role', 'organization', 'last_activity',
            'created_at', 'updated_at'
        ]


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list (minimal info for admin)"""
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'role',
            'organization_name', 'is_active', 'last_activity',
            'created_at'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords do not match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class UserAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for user audit logs"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserAuditLog
        fields = [
            'id', 'user_username', 'action', 'resource_type',
            'resource_id', 'ip_address', 'user_agent', 'details',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MFASetupSerializer(serializers.Serializer):
    """Serializer for MFA setup"""
    
    secret_key = serializers.CharField(read_only=True)
    qr_code_url = serializers.CharField(read_only=True)
    backup_codes = serializers.ListField(child=serializers.CharField(), read_only=True)


class MFAVerifySerializer(serializers.Serializer):
    """Serializer for MFA token verification"""
    
    token = serializers.CharField(max_length=6, min_length=6)
    
    def validate_token(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Token must be 6 digits")
        return value