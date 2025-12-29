from django.urls import path
from .views import GenreListView, ArtistListView, TrackListView

urlpatterns = [
    path("genres", GenreListView.as_view()),
    path("artists", ArtistListView.as_view()),
    path("tracks", TrackListView.as_view())
]
