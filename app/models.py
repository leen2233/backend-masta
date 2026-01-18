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
    avatar = models.URLField(blank=True, null=True)
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


def artist_profile_picture_path(instance, filename):
    ext = filename.split('.')[-1]
    return os.path.join("music", instance.name, f"folder.{ext}")

def artist_banner_path(instance, filename):
    ext = filename.split('.')[-1]
    return os.path.join("music", instance.name, f"backdrop.{ext}")

def album_cover_path(instance, filename):
    ext = filename.split('.')[-1]
    return os.path.join("music", instance.artist.name, instance.title, f"cover.{ext}")

def track_file_path(instance, filename):
    ext = filename.split('.')[-1]
    return os.path.join(
            "music",
            instance.album.artist.name,
            instance.album.title,
            f"{instance.order}. {instance.title}.{ext}"
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
    class Types(models.TextChoices):
        SINGLE  =  ("single", "Single")
        ALBUM   =  ("album", "Album")
        EP      =  ("ep", "EP")

    title = models.CharField(max_length=255)
    cover = models.ImageField(upload_to=album_cover_path, blank=True, null=True)
    track_count = models.IntegerField(default=0, blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)
    type = models.CharField(max_length=10, choices=Types, default="album")

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
            return f"{self.title} (" + self.artist.name + ")"
        else:
            return f"{self.title}"

class Track(models.Model):
    title = models.CharField(max_length=255)
    order = models.IntegerField(default=0, blank=True)
    duration = models.IntegerField(default=0, blank=True, null=True)

    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="tracks")
    featured_artists = models.ManyToManyField(Artist, blank=True)

    listens = models.IntegerField(default=0)
    file = models.FileField(upload_to=track_file_path, blank=True, null=True)
    yt_id = models.CharField(blank=True, null=True, max_length=255)

