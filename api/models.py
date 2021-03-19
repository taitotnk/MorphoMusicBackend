from django.db import models
import datetime


class Lineuser(models.Model):
    user_id = models.CharField(max_length=256)


class Song(models.Model):
    line_user = models.ForeignKey(Lineuser, on_delete=models.CASCADE)
    song_name = models.CharField(max_length=128)
    artist_name = models.CharField(max_length=128)
    buy_url = models.URLField()
    artwork_url = models.URLField()
    created_date = models.DateTimeField(default=datetime.datetime.now)
