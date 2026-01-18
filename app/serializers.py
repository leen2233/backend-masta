from rest_framework.serializers import ModelSerializer, SerializerMethodField
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Genre, Artist, Track, Album, UserProfile

User = get_user_model()


class GenreSerializer(ModelSerializer):
    class Meta:
        model = Genre
        fields = "__all__"


class ArtistSerializer(ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Artist
        fields = "__all__"


class AlbumSerializer(ModelSerializer):
    artist = ArtistSerializer()

    class Meta:
        model = Album
        fields = "__all__"


class TrackSerializer(ModelSerializer):
    """Track serializer with nested album and artist data"""
    album = AlbumSerializer()

    class Meta:
        model = Track
        fields = "__all__"


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

    class Meta:
        model = Track
        fields = "__all__"


# =============================================================================
# Authentication Serializers
# =============================================================================

class UserProfileSerializer(ModelSerializer):
    """Serializer for UserProfile model"""

    class Meta:
        model = UserProfile
        fields = ('email_verified', 'avatar', 'date_of_birth',
                  'oauth_provider', 'oauth_uid', 'created_at', 'updated_at')
        read_only_fields = ('email_verified', 'oauth_provider', 'oauth_uid',
                           'created_at', 'updated_at')


class UserSerializer(ModelSerializer):
    """Serializer for User model with profile data"""

    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login', 'profile')
        read_only_fields = ('id', 'date_joined', 'last_login')


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

