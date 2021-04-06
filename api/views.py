from django.conf import settings
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import requests
import json
from .models import Lineuser, Song


@require_GET
def get_data(request):
    try:
        auth_token = request.META.get('HTTP_AUTHORIZATION')
        res_body, result = verify(auth_token.replace("Idtoken ", ""))
    except:  # noqa
        return JsonResponse({"status": "failed"})

    if result == "success":
        res_dict = json.loads(res_body)
        user_id = res_dict["sub"]
        print(user_id)
        data = {"status": "success"}
        return JsonResponse(get_songs(data, user_id))

    elif result == "failed":
        res_dict = json.loads(res_body)
        return JsonResponse({"status": "failed", "description": res_dict["error_description"]})


def get_songs(data, user_id):
    user_data = get_object_or_404(Lineuser, user_id=user_id)
    song_data = Song.objects.filter(
        line_user=user_data).order_by("-created_date")
    datasets = []
    for item in song_data:
        dataset = {}
        dataset["id"] = item.id
        dataset["song_name"] = item.song_name
        dataset["artist_name"] = item.artist_name
        dataset["buy_url"] = item.buy_url
        dataset["artwork_url"] = item.artwork_url
        datasets.append(dataset)
    data["songs"] = datasets
    return data


def verify(token):
    # LINE IDトークンの検証
    url = "https://api.line.me/oauth2/v2.1/verify"
    payload = {"id_token": token, "client_id": str(settings.LIFF_CHANNEL_ID)}
    try:
        response = requests.post(url, data=payload, timeout=10.0)
        if response.status_code == 200:
            return response.text, "success"
        else:
            return response.text, "failed"
    except requests.exceptions.ConnectTimeout:
        return '{"error": "connection_timeout", "error_description": "LINE SDK Connection Timeout"}'
