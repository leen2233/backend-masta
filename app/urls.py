from django.urls import path
from .views import (
    GenreListView,
    ArtistListView,
    ArtistDetailView,
    AlbumListView,
    AlbumDetailView,
    TrackListView,
    SearchView,
)

urlpatterns = [
    path("genres/", GenreListView.as_view()),
    path("artists/", ArtistListView.as_view()),
    path("artists/<slug:slug>/", ArtistDetailView.as_view()),
    path("albums/", AlbumListView.as_view()),
    path("albums/<slug:slug>/", AlbumDetailView.as_view()),
    path("tracks/", TrackListView.as_view()),
    path("search/", SearchView.as_view()),
]
