from django.urls import path
from .views import (
    GenreListView,
    ArtistListView,
    ArtistDetailView,
    AlbumListView,
    AlbumDetailView,
    TrackListView,
    SearchView,
    # Auth views
    RegisterView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    logout_view,
    me_view,
    verify_email_view,
    resend_verification_view,
    UpdateProfileView,
    change_password_view,
    request_password_reset_view,
    reset_password_view,
    # Settings views
    settings_view,
    upload_avatar_view,
    delete_account_view,
    download_data_view,
    clear_history_view,
    listening_history_view,
    user_stats_view,
    track_play_view,
    # Library views
    saved_albums_view,
    save_album_view,
    followed_artists_view,
    follow_artist_view,
    favorite_tracks_view,
    favorite_track_view,
)

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", logout_view, name="logout"),
    path("auth/me/", me_view, name="me"),
    path("auth/verify-email/", verify_email_view, name="verify_email"),
    path("auth/resend-verification/", resend_verification_view, name="resend_verification"),
    path("auth/profile/", UpdateProfileView.as_view(), name="update_profile"),
    path("auth/change-password/", change_password_view, name="change_password"),
    path("auth/request-password-reset/", request_password_reset_view, name="request_password_reset"),
    path("auth/reset-password/", reset_password_view, name="reset_password"),

    # Settings endpoints
    path("settings/", settings_view, name="settings"),
    path("settings/avatar/", upload_avatar_view, name="upload_avatar"),
    path("settings/delete-account/", delete_account_view, name="delete_account"),
    path("settings/download-data/", download_data_view, name="download_data"),
    path("settings/clear-history/", clear_history_view, name="clear_history"),
    path("settings/listening-history/", listening_history_view, name="listening_history"),
    path("settings/stats/", user_stats_view, name="user_stats"),

    # Music endpoints
    path("genres/", GenreListView.as_view()),
    path("artists/", ArtistListView.as_view()),
    path("artists/<slug:slug>/", ArtistDetailView.as_view()),
    path("albums/", AlbumListView.as_view()),
    path("albums/<slug:slug>/", AlbumDetailView.as_view()),
    path("tracks/", TrackListView.as_view()),
    path("tracks/<int:pk>/play/", track_play_view, name="track_play"),
    path("search/", SearchView.as_view()),

    # Library endpoints
    path("library/saved-albums/", saved_albums_view, name="saved_albums"),
    path("library/saved-albums/<int:pk>/", save_album_view, name="save_album"),
    path("library/followed-artists/", followed_artists_view, name="followed_artists"),
    path("library/followed-artists/<int:pk>/", follow_artist_view, name="follow_artist"),
    path("library/favorite-tracks/", favorite_tracks_view, name="favorite_tracks"),
    path("library/favorite-tracks/<int:pk>/", favorite_track_view, name="favorite_track"),
]
