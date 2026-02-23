from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
import os
import secrets


class UserProfile(models.Model):
    """Extended user profile with additional fields"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Additional fields
    email_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    # OAuth fields
    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    oauth_uid = models.CharField(max_length=255, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class EmailVerificationToken(models.Model):
    """Token for email verification"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Token for {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
        ]
        verbose_name = 'Email Verification Token'
        verbose_name_plural = 'Email Verification Tokens'


class PasswordResetToken(models.Model):
    """Token for password reset"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Password reset token for {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
        ]
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'


class Genre(models.Model):
    name = models.CharField(max_length=255)
    thumbnail = models.ImageField(upload_to="genres/", blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'


def artist_profile_picture_path(instance, filename):
    ext = filename.split('.')[-1]
    artist  = slugify(instance.name)
    return os.path.join("music",artist , f"folder.{ext}")

def artist_banner_path(instance, filename):
    ext = filename.split('.')[-1]
    artist  = slugify(instance.name)
    return os.path.join("music", artist, f"backdrop.{ext}")

def album_cover_path(instance, filename):
    ext = filename.split('.')[-1]
    artist = slugify(instance.artist.name)
    album = slugify(instance.title)

    return os.path.join("music", artist, album, f"cover.{ext}")


def track_file_path(instance, filename):
    ext = filename.split('.')[-1]

    artist_slug = slugify(instance.album.artist.name)
    album_slug = slugify(instance.album.title)
    track_slug = slugify(instance.title)

    return os.path.join(
        "music",
        artist_slug,
        album_slug,
        f"{instance.order}-{track_slug}.{ext}"
    )


class Artist(models.Model):
    name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to=artist_profile_picture_path, blank=True, null=True)
    banner = models.ImageField(upload_to=artist_banner_path, blank=True, null=True)
    views = models.IntegerField(default=0, blank=True, null=True)

    parse_tracks = models.BooleanField(default=True)
    genres = models.ManyToManyField(Genre)
    slug = models.SlugField(blank=True, unique=True)
    yt_id = models.CharField(blank=True, null=True, max_length=255)

    # Frontend integration fields
    followers = models.IntegerField(default=0, blank=True, null=True)
    monthly_listeners = models.IntegerField(default=0, blank=True, null=True)
    verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # generate slug only if not set
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 1
            # ensure slug uniqueness
            while Artist.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Album(models.Model):
    
    type_list = [
        ('single','Single'),
        ("album", "Album"),
        ("ep", "EP")
    ]

    title = models.CharField(max_length=255)
    cover = models.ImageField(upload_to=album_cover_path, blank=True, null=True)
    track_count = models.IntegerField(default=0, blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)
    album_type = models.CharField(max_length=10, choices=type_list, default="album")

    slug = models.SlugField(blank=True, null=True)
    artist = models.ForeignKey(Artist, related_name="albums", on_delete=models.CASCADE)

    yt_id = models.CharField(blank=True, null=True, max_length=255)

    def save(self, *args, **kwargs):
        # generate slug only if not set
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            i = 1
            # ensure slug uniqueness
            while Artist.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        if self.artist:
            return f"{self.title} ({self.artist.name})"
        else:
            return f"{self.title}"

class Track(models.Model):
    title = models.CharField(max_length=255)
    order = models.IntegerField(default=0, blank=True)
    duration = models.IntegerField(default=0, blank=True, null=True)

    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="tracks")
    featured_artists = models.ManyToManyField(Artist, blank=True)

    listens = models.IntegerField(default=0)
    track_file = models.FileField(upload_to=track_file_path, blank=True, null=True,max_length=500)
    yt_id = models.CharField(blank=True, null=True, max_length=255)

    def __str__(self):
        return f"{self.title}"
# =============================================================================
# User Settings Models
# =============================================================================

class UserPreferences(models.Model):
    """User preferences for playback and privacy settings"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    # Playback settings
    crossfade_duration = models.IntegerField(default=0, help_text="Crossfade duration in seconds (0-12)")
    gapless_playback = models.BooleanField(default=True, help_text="Enable gapless playback between tracks")

    # Privacy settings
    private_account = models.BooleanField(default=False, help_text="Only approved followers can see your activity")
    show_activity_status = models.BooleanField(default=True, help_text="Let others see when you're listening")
    share_listening_history = models.BooleanField(default=True, help_text="Used for personalized recommendations")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s preferences"

    class Meta:
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'


class NotificationPreference(models.Model):
    """User notification preferences"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')

    # Email notifications
    email_new_releases = models.BooleanField(default=True, help_text="New releases from followed artists")
    email_recommendations = models.BooleanField(default=True, help_text="Weekly music recommendations")

    # In-app notifications
    app_playlist_updates = models.BooleanField(default=True, help_text="When playlists you follow are updated")
    app_friend_activity = models.BooleanField(default=False, help_text="When friends share music or playlists")
    app_concert_alerts = models.BooleanField(default=False, help_text="Concert announcements near you")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s notifications"

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'


class ListeningHistory(models.Model):
    """Track listening history for users"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listening_history')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='listening_history')
    played_at = models.DateTimeField(auto_now_add=True)
    play_duration = models.IntegerField(default=0, help_text="Duration played in seconds")

    def __str__(self):
        return f"{self.user.username} - {self.track.title}"

    class Meta:
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['user', '-played_at']),
            models.Index(fields=['track', '-played_at']),
        ]


class SavedAlbum(models.Model):
    """User's saved albums for library"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_albums')
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Saved Album'
        verbose_name_plural = 'Saved Albums'
        unique_together = ['user', 'album']  # Prevent duplicate saves
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.album.title}"


class FollowedArtist(models.Model):
    """Artists that user follows"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followed_artists')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='followed_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Followed Artist'
        verbose_name_plural = 'Followed Artists'
        unique_together = ['user', 'artist']  # Prevent duplicate follows
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} follows {self.artist.name}"


class FavoriteTrack(models.Model):
    """User's favorite (liked) tracks"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorite Track'
        verbose_name_plural = 'Favorite Tracks'
        unique_together = ['user', 'track']  # Prevent duplicate favorites
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.track.title}"
