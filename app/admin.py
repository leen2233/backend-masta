from django.contrib import admin
from django.utils.html import format_html
from .models import (Artist, Album, Track, Genre,
                    UserProfile, EmailVerificationToken, PasswordResetToken)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    def avatar_img(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;border-radius:8px;object-fit:cover;" />',
                obj.avatar.url
            )
        return "None"
    
    avatar_img.short_description = 'Image'

    list_display = ['id','user','avatar_img','email_verified','date_of_birth']
    list_display_links = ['id','user']
    search_fields = ['id','user__username','user__email']
    list_filter = ['email_verified', 'date_of_birth']
    date_hierarchy = "created_at"

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['id','user','user__email','created_at','expires_at','is_used','is_valid']
    list_display_links = ['id','user']
    search_fields = ['token','user__username','id','user__email']
    list_filter = ['is_used']
    date_hierarchy = "created_at"

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['id','user','user__email','created_at','expires_at','is_used','is_valid']
    list_display_links = ['id','user']
    search_fields = ['token','user__username','id','user__email']
    list_filter = ['is_used']
    date_hierarchy = "created_at"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    def thumbnail_img(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;border-radius:8px;object-fit:cover;" />',
                obj.thumbnail.url
            )
        return "None"
    thumbnail_img.short_description = 'thumbnail'
    
    list_display = ['id','name','thumbnail_img']
    list_display_links = ['id','name']
    search_fields = ['id','name']


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    def profile_img(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;border-radius:8px;object-fit:cover;" />',
                obj.profile_picture.url
            )
        return "None"
    profile_img.short_description = 'profile_picture'

    list_display = ['id','profile_img','name','slug','views','followers','monthly_listeners','verified']
    list_display_links = ['id','profile_img','name']
    search_fields = ["name", "slug", "bio"]
    list_filter = ['verified']
    date_hierarchy = "created_at"


class TrackInline(admin.TabularInline):
    model = Track
    extra = 0


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    def cover_img(self, obj):
        if obj.cover:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;border-radius:8px;object-fit:cover;" />',
                obj.cover.url
            )
        return "None"
    cover_img.short_description = 'cover'

    list_display = ['id','title','cover_img','artist__name','album_type','track_count','release_date']
    list_display_links = ['id','title','cover_img']
    search_fields = ['title','artist__name']
    list_filter = ['album_type']
    inlines = [TrackInline]


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['id','title','album','order','duration','listens']
    list_display_links = ['id','title']
    search_fields = ("title", "album__title", "album__artist__name")

