from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .models import User, Organization
from .serializers import UserProfileSerializer, UserListSerializer, OrganizationSerializer

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that includes user data in response"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Get the user from the validated token
            from rest_framework_simplejwt.tokens import UntypedToken
            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
            from django.contrib.auth import get_user_model
            
            try:
                # Extract user from the access token
                access_token = response.data['access']
                decoded_token = UntypedToken(access_token)
                user_id = decoded_token['user_id']
                user = get_user_model().objects.get(id=user_id)
                
                # Serialize user data
                user_serializer = UserProfileSerializer(user)
                
                # Add user data to response
                response.data['user'] = user_serializer.data
                
            except (InvalidToken, TokenError, User.DoesNotExist):
                pass  # If anything fails, just return the original token response
        
        return response


class CurrentUserView(generics.RetrieveAPIView):
    """Get current authenticated user's profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    """Logout user by blacklisting refresh token"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management operations"""
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see users from their own organization
        return User.objects.filter(organization=self.request.user.organization)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password"""
        user = self.get_object()
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({"error": "Invalid old password"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
