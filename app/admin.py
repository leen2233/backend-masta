from django.contrib import admin

from .models import Artist, Album, Track, Genre


class TrackInline(admin.TabularInline):
    model = Track
    extra = 0


admin.site.register(Genre)

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "bio")
    search_fields = ("name", "slug", "bio")


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "type", "track_count", "release_date")
    inlines = [TrackInline]


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "album__title")
    search_fields = ("title", "album__title", "album__artist__name")

