from rest_framework.serializers import ModelSerializer, SerializerMethodField
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings

from .models import Genre, Artist, Track, Album, UserProfile, UserPreferences, NotificationPreference, ListeningHistory, SavedAlbum, FollowedArtist, FavoriteTrack

User = get_user_model()


class GenreSerializer(ModelSerializer):
    class Meta:
        model = Genre
        fields = "__all__"


class ArtistSerializer(ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = "__all__"

    def get_image_url(self, obj):
        """Get the absolute URL for the artist profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None


class AlbumSerializer(ModelSerializer):
    artist = ArtistSerializer()

    class Meta:
        model = Album
        fields = "__all__"


class TrackSerializer(ModelSerializer):
    """Track serializer with nested album and artist data"""
    album = AlbumSerializer()
    artist = SerializerMethodField()
    audioUrl = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = "__all__"

    def get_artist(self, obj):
        return ArtistSerializer(obj.album.artist).data

    def get_audioUrl(self, obj):
        """Get the audio URL from file or yt_id"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class AlbumDetailSerializer(ModelSerializer):
    """Detailed album serializer with tracks"""
    artist = ArtistSerializer()
    tracks = TrackSerializer(many=True, read_only=True)

    class Meta:
        model = Album
        fields = "__all__"


class ArtistDetailSerializer(ModelSerializer):
    """Detailed artist serializer with albums and top tracks"""
    genres = GenreSerializer(many=True, read_only=True)
    albums = AlbumDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Artist
        fields = "__all__"


class AlbumListSerializer(ModelSerializer):
    """Lightweight album serializer for list views"""
    artist = ArtistSerializer()

    class Meta:
        model = Album
        fields = "__all__"


class TrackDetailSerializer(ModelSerializer):
    """Detailed track serializer with full album and artist info"""
    album = AlbumDetailSerializer()
    artist = SerializerMethodField()
    audioUrl = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = "__all__"

    def get_artist(self, obj):
        return ArtistSerializer(obj.album.artist).data

    def get_audioUrl(self, obj):
        """Get the audio URL from file or yt_id"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


# =============================================================================
# Authentication Serializers
# =============================================================================

class UserProfileSerializer(ModelSerializer):
    """Serializer for UserProfile model"""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ('email_verified', 'avatar', 'avatar_url', 'date_of_birth',
                  'oauth_provider', 'oauth_uid', 'created_at', 'updated_at')
        read_only_fields = ('email_verified', 'oauth_provider', 'oauth_uid',
                           'created_at', 'updated_at')

    def get_avatar_url(self, obj):
        """Return full URL for avatar"""
        if obj.avatar and obj.avatar.name:
            request = self.context.get('request')
            if request:
                # ImageField has .url property that returns the relative URL
                return request.build_absolute_uri(obj.avatar.url)
        return None


class UserPreferencesSerializer(ModelSerializer):
    """Serializer for UserPreferences model"""

    class Meta:
        model = UserPreferences
        fields = ('crossfade_duration', 'gapless_playback',
                  'private_account', 'show_activity_status', 'share_listening_history',
                  'created_at', 'updated_at')


class NotificationPreferenceSerializer(ModelSerializer):
    """Serializer for NotificationPreference model"""

    class Meta:
        model = NotificationPreference
        fields = ('email_new_releases', 'email_recommendations',
                  'app_playlist_updates', 'app_friend_activity', 'app_concert_alerts',
                  'created_at', 'updated_at')


class UserSerializer(ModelSerializer):
    """Serializer for User model with profile data"""

    profile = SerializerMethodField()
    preferences = UserPreferencesSerializer(read_only=True)
    notifications = NotificationPreferenceSerializer(source='notification_preferences', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login', 'profile', 'preferences', 'notifications')
        read_only_fields = ('id', 'date_joined', 'last_login')

    def get_profile(self, obj):
        return UserProfileSerializer(obj.profile, context=self.context).data


class UserPublicSerializer(ModelSerializer):
    """Public user serializer (limited fields)"""

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')
        read_only_fields = ('id', 'username')


class RegisterSerializer(ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm',
                  'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')

        # Create user (inactive - requires email verification)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=False  # Require email verification
        )

        # Create profile for user
        UserProfile.objects.create(user=user)

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user data"""
    # Keep username field but accept email in it
    # The custom authentication backend will handle email/username lookup

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        token['username'] = user.username
        return token

    def validate(self, attrs):
        # Map email to username for JWT authentication
        # The custom backend will handle the lookup
        data = super().validate(attrs)
        # Add user data to response
        data['user'] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""

    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters")
        return value


class UpdateProfileSerializer(ModelSerializer):
    """Serializer for updating user profile"""

    class Meta:
        model = User
        fields = ('first_name', 'last_name')

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()
        return instance


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset"""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters")
        return value


# =============================================================================
# Settings Serializers
# =============================================================================

class ListeningHistorySerializer(ModelSerializer):
    """Serializer for ListeningHistory model"""

    track_title = serializers.CharField(source='track.title', read_only=True)
    track_duration = serializers.IntegerField(source='track.duration', read_only=True)
    album_title = serializers.CharField(source='track.album.title', read_only=True)
    artist_name = serializers.CharField(source='track.album.artist.name', read_only=True)
    album_cover = serializers.ImageField(source='track.album.cover', read_only=True)
    artist_slug = serializers.SlugField(source='track.album.artist.slug', read_only=True)
    album_slug = serializers.SlugField(source='track.album.slug', read_only=True)
    track_file = serializers.FileField(source='track.file', read_only=True)
    track_yt_id = serializers.CharField(source='track.yt_id', read_only=True)

    class Meta:
        model = ListeningHistory
        fields = ('id', 'track', 'track_title', 'track_duration', 'album_title',
                  'artist_name', 'album_cover', 'artist_slug', 'album_slug',
                  'played_at', 'play_duration', 'track_file', 'track_yt_id')


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user listening statistics"""

    tracks_played = serializers.IntegerField(read_only=True)
    hours_streamed = serializers.FloatField(read_only=True)
    playlists_created = serializers.IntegerField(read_only=True)
    artists_discovered = serializers.IntegerField(read_only=True)


class SavedAlbumSerializer(ModelSerializer):
    """Serializer for saved albums"""

    album = AlbumDetailSerializer(read_only=True)

    class Meta:
        model = SavedAlbum
        fields = ('id', 'album', 'created_at')


class FollowedArtistSerializer(ModelSerializer):
    """Serializer for followed artists"""

    artist = ArtistDetailSerializer(read_only=True)

    class Meta:
        model = FollowedArtist
        fields = ('id', 'artist', 'created_at')


class FavoriteTrackSerializer(ModelSerializer):
    """Serializer for favorite (liked) tracks"""

    track = TrackDetailSerializer(read_only=True)

    class Meta:
        model = FavoriteTrack
        fields = ('id', 'track', 'created_at')


class UserSettingsSerializer(ModelSerializer):
    """Combined serializer for user settings including profile, preferences, and notifications"""
    profile = SerializerMethodField()
    preferences = UserPreferencesSerializer(read_only=False)
    notifications = NotificationPreferenceSerializer(source='notification_preferences', read_only=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login', 'profile', 'preferences', 'notifications')
        read_only_fields = ('id', 'date_joined', 'last_login')

    def get_profile(self, obj):
        return UserProfileSerializer(obj.profile, context=self.context).data

    def update(self, instance, validated_data):
        # Extract nested data (pop before iterating over validated_data)
        profile_data = validated_data.pop('profile', {})
        preferences_data = validated_data.pop('preferences', {})
        # When using source='notification_preferences', DRF puts the data under the field name
        # But we need to check both possibilities
        notifications_data = validated_data.pop('notifications', None)
        if notifications_data is None:
            notifications_data = validated_data.pop('notification_preferences', {})

        # Update user fields (excluding nested fields)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile
        if profile_data:
            for attr, value in profile_data.items():
                if attr not in ['email_verified', 'oauth_provider', 'oauth_uid',
                               'created_at', 'updated_at']:
                    setattr(instance.profile, attr, value)
            instance.profile.save()

        # Update or create preferences
        if preferences_data:
            obj, created = UserPreferences.objects.get_or_create(
                user=instance,
                defaults=preferences_data
            )
            if not created:
                for attr, value in preferences_data.items():
                    setattr(obj, attr, value)
                obj.save()

        # Update or create notifications
        if notifications_data:
            obj, created = NotificationPreference.objects.get_or_create(
                user=instance,
                defaults=notifications_data
            )
            if not created:
                for attr, value in notifications_data.items():
                    setattr(obj, attr, value)
                obj.save()

        # Refresh from database to get latest values for serialization
        instance.refresh_from_db()

        return instance


class AvatarUploadSerializer(serializers.Serializer):
    """Serializer for avatar upload"""

    avatar = serializers.ImageField(required=True, help_text="Avatar image file")

