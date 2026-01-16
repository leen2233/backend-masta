from rest_framework.serializers import ModelSerializer, SerializerMethodField
from .models import Genre, Artist, Track, Album


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
