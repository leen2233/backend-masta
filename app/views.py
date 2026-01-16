from django.shortcuts import render, get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count
from .models import Genre, Artist, Track, Album
from .serializers import (
    GenreSerializer,
    ArtistSerializer,
    ArtistDetailSerializer,
    AlbumSerializer,
    AlbumListSerializer,
    AlbumDetailSerializer,
    TrackSerializer,
    TrackDetailSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GenreListView(ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [AllowAny]


class ArtistListView(ListAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        order_by = self.request.query_params.get('order_by', 'id')
        return queryset.order_by(order_by)


class ArtistDetailView(RetrieveAPIView):
    queryset = Artist.objects.prefetch_related(
        'albums__tracks',
        'genres'
    ).all()
    serializer_class = ArtistDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class AlbumListView(ListAPIView):
    queryset = Album.objects.select_related('artist').all()
    serializer_class = AlbumListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        order_by = self.request.query_params.get('order_by', 'id')
        return queryset.order_by(order_by)


class AlbumDetailView(RetrieveAPIView):
    queryset = Album.objects.select_related('artist').prefetch_related('tracks').all()
    serializer_class = AlbumDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class TrackListView(ListAPIView):
    queryset = Track.objects.select_related('album__artist').all()
    serializer_class = TrackSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        order_by = self.request.query_params.get('order_by', 'id')
        return queryset.order_by(order_by)


class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if not query:
            return Response({
                'artists': [],
                'albums': [],
                'tracks': []
            })

        # Search artists
        artists = Artist.objects.filter(
            Q(name__icontains=query) |
            Q(bio__icontains=query)
        ).order_by('-views')[:10]

        # Search albums
        albums = Album.objects.filter(
            Q(title__icontains=query) |
            Q(artist__name__icontains=query)
        ).select_related('artist').order_by('-track_count')[:10]

        # Search tracks
        tracks = Track.objects.filter(
            Q(title__icontains=query) |
            Q(album__title__icontains=query) |
            Q(album__artist__name__icontains=query)
        ).select_related('album__artist').order_by('-listens')[:10]

        return Response({
            'artists': ArtistSerializer(artists, many=True).data,
            'albums': AlbumListSerializer(albums, many=True).data,
            'tracks': TrackSerializer(tracks, many=True).data,
        })
