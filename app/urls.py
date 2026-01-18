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

    # Music endpoints
    path("genres/", GenreListView.as_view()),
    path("artists/", ArtistListView.as_view()),
    path("artists/<slug:slug>/", ArtistDetailView.as_view()),
    path("albums/", AlbumListView.as_view()),
    path("albums/<slug:slug>/", AlbumDetailView.as_view()),
    path("tracks/", TrackListView.as_view()),
    path("search/", SearchView.as_view()),
]
