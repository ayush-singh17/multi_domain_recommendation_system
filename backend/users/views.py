"""
Users App — Views
Handles registration, profile retrieval, and Google OAuth.
Login/logout is handled by SimpleJWT token endpoints in urls.py.
"""

from rest_framework               import generics, permissions, status  # Added status here
from rest_framework.response      import Response
from rest_framework.views         import APIView
from django.contrib.auth          import get_user_model  # Added this
from .serializers                 import RegisterSerializer, UserSerializer
from google.oauth2                import id_token
from google.auth.transport        import requests as google_requests
from rest_framework.permissions   import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
import os

User = get_user_model()  # Added this


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — create a new user account."""
    serializer_class   = RegisterSerializer
    permission_classes = [AllowAny]


class ProfileView(APIView):
    """GET /api/auth/profile/ — return the logged-in user's details."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class GoogleLoginView(APIView):
    """POST /api/auth/social/google/ — verify Google token, return JWT."""
    permission_classes = [AllowAny]

    def post(self, request):
        GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
        token = request.data.get('id_token')

        if not token:
            return Response(
                {'error': 'id_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response(
                {'error': 'Invalid Google token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        email = info.get('email')
        name  = info.get('name', email.split('@')[0] if email else 'User')

        if not email:
            return Response(
                {'error': 'Could not get email from Google'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get existing user or create new one
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'name': name}
        )

        # Update name if it was missing
        if not created and not user.name:
            user.name = name
            user.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        })
