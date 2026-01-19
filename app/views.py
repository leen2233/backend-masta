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
from django.db.models import Q, Count, Sum
from django.contrib.auth import get_user_model

from .models import Genre, Artist, Track, Album, ListeningHistory, UserPreferences, NotificationPreference, SavedAlbum, FollowedArtist, FavoriteTrack
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
    UserSettingsSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    ResetPasswordSerializer,
    ListeningHistorySerializer,
    UserStatsSerializer,
    SavedAlbumSerializer,
    FollowedArtistSerializer,
    FavoriteTrackSerializer,
    AvatarUploadSerializer,
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
    user = request.user

    # Ensure preferences and notifications exist for the user
    try:
        _ = user.preferences
    except UserPreferences.DoesNotExist:
        UserPreferences.objects.create(user=user)
    try:
        _ = user.notification_preferences
    except NotificationPreference.DoesNotExist:
        NotificationPreference.objects.create(user=user)

    serializer = UserSerializer(user, context={"request": request})
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


# =============================================================================
# Settings Views
# =============================================================================

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def settings_view(request):
    """
    GET: Retrieve user settings including profile, preferences, and notifications
    PATCH: Update user settings
    """
    user = request.user

    # Ensure preferences and notifications exist for the user
    try:
        _ = user.preferences
    except UserPreferences.DoesNotExist:
        UserPreferences.objects.create(user=user)
    try:
        _ = user.notification_preferences
    except NotificationPreference.DoesNotExist:
        NotificationPreference.objects.create(user=user)

    if request.method == 'GET':
        serializer = UserSettingsSerializer(user)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        serializer = UserSettingsSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar_view(request):
    """Upload or update user avatar"""
    serializer = AvatarUploadSerializer(data=request.data)
    if serializer.is_valid():
        avatar = serializer.validated_data['avatar']
        # Save avatar file path - Django's ImageField will handle the storage
        request.user.profile.avatar = avatar
        request.user.profile.save()
        # Refresh from DB to get the stored file path (not the InMemoryUploadedFile)
        request.user.profile.refresh_from_db()
        # Build the URL - avatar.name contains the path relative to MEDIA_ROOT
        avatar_url = request.build_absolute_uri(request.user.profile.avatar.url)
        return Response({'avatar': request.user.profile.avatar.name, 'avatar_url': avatar_url})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account_view(request):
    """Permanently delete user account"""
    user = request.user
    # Logout user first by blacklisting refresh token
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
    except:
        pass

    # Delete user (this will cascade delete profile, preferences, etc.)
    user.delete()
    return Response({'message': 'Account deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_data_view(request):
    """Export user data as JSON"""
    user = request.user
    user_serializer = UserSettingsSerializer(user)

    # Get listening history
    history = ListeningHistory.objects.filter(user=user)
    history_serializer = ListeningHistorySerializer(history, many=True)

    data = {
        'user': user_serializer.data,
        'listening_history': history_serializer.data,
        'exported_at': timezone.now().isoformat()
    }

    response = Response(data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="masta_user_data.json"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_history_view(request):
    """Clear all listening history for the user"""
    user = request.user
    deleted_count = ListeningHistory.objects.filter(user=user).delete()[0]
    return Response({
        'message': f'{deleted_count} listening history entries cleared'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listening_history_view(request):
    """Get user's listening history"""
    user = request.user
    history = ListeningHistory.objects.filter(user=user).select_related(
        'track__album__artist'
    )[:100]  # Limit to last 100 entries
    serializer = ListeningHistorySerializer(history, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats_view(request):
    """Get user listening statistics"""
    user = request.user

    # Get listening history
    history = ListeningHistory.objects.filter(user=user)

    # Calculate stats
    tracks_played = history.count()

    # Sum play duration and convert to hours
    total_duration = history.aggregate(total=Sum('play_duration'))['total'] or 0
    hours_streamed = round(total_duration / 3600, 1)

    # Count distinct artists from listening history
    artists_discovered = history.values('track__album__artist').distinct().count()

    # Placeholder for playlists (to be implemented later)
    playlists_created = 0

    data = {
        'tracks_played': tracks_played,
        'hours_streamed': hours_streamed,
        'playlists_created': playlists_created,
        'artists_discovered': artists_discovered,
    }

    serializer = UserStatsSerializer(data)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_play_view(request, pk):
    """Track when a user plays a track - creates listening history entry"""
    user = request.user

    try:
        track = Track.objects.get(pk=pk)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)

    # Create listening history entry
    ListeningHistory.objects.create(
        user=user,
        track=track,
        play_duration=0  # Will be updated if duration tracking is added later
    )

    # Increment track listen count
    track.listens = (track.listens or 0) + 1
    track.save(update_fields=['listens'])

    return Response({'message': 'Play tracked'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def saved_albums_view(request):
    """Get user's saved albums"""
    user = request.user
    saved_albums = SavedAlbum.objects.filter(user=user).select_related('album__artist').order_by('-created_at')
    serializer = SavedAlbumSerializer(saved_albums, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def save_album_view(request, pk):
    """Save or unsave an album"""
    user = request.user

    try:
        album = Album.objects.get(pk=pk)
    except Album.DoesNotExist:
        return Response({'error': 'Album not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        # Save album (create if doesn't exist)
        saved_album, created = SavedAlbum.objects.get_or_create(
            user=user,
            album=album
        )
        if created:
            return Response({'message': 'Album saved'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Album already saved'}, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        # Unsave album
        deleted_count, _ = SavedAlbum.objects.filter(user=user, album=album).delete()
        if deleted_count > 0:
            return Response({'message': 'Album removed from library'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Album not in library'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def followed_artists_view(request):
    """Get user's followed artists"""
    user = request.user
    followed = FollowedArtist.objects.filter(user=user).select_related('artist').order_by('-created_at')
    serializer = FollowedArtistSerializer(followed, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def follow_artist_view(request, pk):
    """Follow or unfollow an artist"""
    user = request.user

    try:
        artist = Artist.objects.get(pk=pk)
    except Artist.DoesNotExist:
        return Response({'error': 'Artist not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        # Follow artist (create if doesn't exist)
        followed_artist, created = FollowedArtist.objects.get_or_create(
            user=user,
            artist=artist
        )
        if created:
            # Increment artist followers count
            artist.followers = (artist.followers or 0) + 1
            artist.save(update_fields=['followers'])
            return Response({'message': 'Artist followed'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Already following this artist'}, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        # Unfollow artist
        deleted_count, _ = FollowedArtist.objects.filter(user=user, artist=artist).delete()
        if deleted_count > 0:
            # Decrement artist followers count
            artist.followers = max(0, (artist.followers or 0) - 1)
            artist.save(update_fields=['followers'])
            return Response({'message': 'Artist unfollowed'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Not following this artist'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorite_tracks_view(request):
    """Get user's favorite (liked) tracks"""
    user = request.user
    favorites = FavoriteTrack.objects.filter(user=user).select_related(
        'track__album__artist'
    ).order_by('-created_at')
    serializer = FavoriteTrackSerializer(favorites, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def favorite_track_view(request, pk):
    """Like or unlike a track"""
    user = request.user

    try:
        track = Track.objects.get(pk=pk)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        # Like track (create if doesn't exist)
        favorite, created = FavoriteTrack.objects.get_or_create(
            user=user,
            track=track
        )
        if created:
            return Response({'message': 'Track liked'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Already liked'}, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        # Unlike track
        deleted_count, _ = FavoriteTrack.objects.filter(user=user, track=track).delete()
        if deleted_count > 0:
            return Response({'message': 'Track unliked'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Track not in favorites'}, status=status.HTTP_404_NOT_FOUND)


# Import timezone for download_data_view
from django.utils import timezone
