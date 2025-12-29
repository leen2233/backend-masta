from rest_framework.serializers import ModelSerializer
from .models import Genre, Artist, Track, Album


class GenreSerializer(ModelSerializer):
    class Meta:
        model = Genre
        fields = "__all__"


class ArtistSerializer(ModelSerializer):
    class Meta:
        model = Artist
        fields = "__all__"


class AlbumSerializer(ModelSerializer):
    artist = ArtistSerializer()

    class Meta:
        model = Album
        fields = "__all__"


class TrackSerializer(ModelSerializer):
    album = AlbumSerializer()
    class Meta:
        model = Track
        fields = "__all__"

