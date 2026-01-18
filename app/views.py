from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from .models import Genre, Artist, Track, Album
from .serializers import (
    GenreSerializer,
    ArtistSerializer,
    ArtistDetailSerializer,
    AlbumSerializer,
    AlbumListSerializer,
    AlbumDetailSerializer,
    TrackSerializer,
    TrackDetailSerializer,
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    ResetPasswordSerializer,
)
from .services.email_service import EmailService

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GenreListView(ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [AllowAny]


class ArtistListView(ListAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        order_by = self.request.query_params.get('order_by', 'id')
        return queryset.order_by(order_by)


class ArtistDetailView(RetrieveAPIView):
    queryset = Artist.objects.prefetch_related(
        'albums__tracks',
        'genres'
    ).all()
    serializer_class = ArtistDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class AlbumListView(ListAPIView):
    queryset = Album.objects.select_related('artist').all()
    serializer_class = AlbumListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        order_by = self.request.query_params.get('order_by', 'id')
        return queryset.order_by(order_by)


class AlbumDetailView(RetrieveAPIView):
    queryset = Album.objects.select_related('artist').prefetch_related('tracks').all()
    serializer_class = AlbumDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class TrackListView(ListAPIView):
    queryset = Track.objects.select_related('album__artist').all()
    serializer_class = TrackSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        order_by = self.request.query_params.get('order_by', 'id')
        return queryset.order_by(order_by)


class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if not query:
            return Response({
                'artists': [],
                'albums': [],
                'tracks': []
            })

        # Search artists
        artists = Artist.objects.filter(
            Q(name__icontains=query) |
            Q(bio__icontains=query)
        ).order_by('-views')[:10]

        # Search albums
        albums = Album.objects.filter(
            Q(title__icontains=query) |
            Q(artist__name__icontains=query)
        ).select_related('artist').order_by('-track_count')[:10]

        # Search tracks
        tracks = Track.objects.filter(
            Q(title__icontains=query) |
            Q(album__title__icontains=query) |
            Q(album__artist__name__icontains=query)
        ).select_related('album__artist').order_by('-listens')[:10]

        return Response({
            'artists': ArtistSerializer(artists, many=True).data,
            'albums': AlbumListSerializer(albums, many=True).data,
            'tracks': TrackSerializer(tracks, many=True).data,
        })


# =============================================================================
# Authentication Views
# =============================================================================

class LoginRateThrottle(AnonRateThrottle):
    """Rate limit for login endpoints"""
    rate = '10/minute'


class RegisterView(generics.CreateAPIView):
    """Register a new user"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [LoginRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email
        try:
            EmailService.send_verification_email(user)
        except Exception as e:
            # Log error but don't fail registration
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send verification email: {e}")

        return Response({
            'message': 'Registration successful. Please check your email to verify your account.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with JWT tokens"""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class CustomTokenRefreshView(TokenRefreshView):
    """Refresh access token"""
    pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout and blacklist the refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Get current authenticated user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_view(request):
    """Verify email address using token from URL"""
    token = request.data.get('token')
    if not token:
        return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)

    result = EmailService.verify_email_token(token)

    if result['valid']:
        # Generate tokens for auto-login
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(result['user'])
        return Response({
            'message': 'Email verified successfully',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(result['user']).data
        })
    else:
        return Response({
            'error': result['message']
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_view(request):
    """Resend verification email"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        # Check if already verified
        if hasattr(user, 'profile') and user.profile.email_verified:
            return Response({'message': 'Email already verified'}, status=status.HTTP_200_OK)

        EmailService.send_verification_email(user)
        return Response({'message': 'Verification email sent'}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class UpdateProfileView(generics.UpdateAPIView):
    """Update user profile"""
    serializer_class = UpdateProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password updated successfully'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset_view(request):
    """Request password reset email"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        # Create reset token and send email
        EmailService.send_password_reset_email(user)
        return Response({'message': 'Password reset email sent'})
    except User.DoesNotExist:
        # Don't reveal if user exists
        return Response({'message': 'Password reset email sent'})


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_view(request):
    """Reset password using token"""
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']

    # Verify token
    result = EmailService.verify_password_reset_token(token)
    if not result['valid']:
        return Response({'error': result['message']}, status=status.HTTP_400_BAD_REQUEST)

    # Update password
    user = result['user']
    user.set_password(new_password)
    user.save()

    # Mark token as used
    EmailService.mark_password_reset_token_used(token)

    return Response({'message': 'Password reset successfully'})
