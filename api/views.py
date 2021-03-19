from django.conf import settings
from django.views.decorators.http import require_GET
from django.http import JsonResponse
import requests
import json


@require_GET
def get_data(request):
    try:
        res_body, result = verify(request.headers.get("Idtoken"))
    except:  # noqa
        return JsonResponse({"status": "failed"})

    if result == "success":
        res_dict = json.loads(res_body)
        user_id = res_dict["sub"]
        print(user_id)
        data = {"status": "success"}
        return JsonResponse(get_songs(data))

    elif result == "failed":
        res_dict = json.loads(res_body)
        return JsonResponse({"status": "failed", "description": res_dict["error_description"]})


def get_songs(data):
    return data


def verify(token):
    # LINE IDトークンの検証
    url = "https://api.line.me/oauth2/v2.1/verify"
    payload = {"id_token": token, "client_id": str(settings.LIFF_CHANNEL_ID)}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.text, "success"
    else:
        return response.text, "failed"
