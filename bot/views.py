from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
import json
import requests
import urllib
from django.views.decorators.csrf import csrf_exempt
from api.models import Song, Lineuser
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerSendMessage,
)


# アクセストークンとシークレットの取得
line_bot_api = LineBotApi(
    channel_access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(channel_secret=settings.LINE_CHANNEL_SECRET)


@csrf_exempt
def callback(request):
    # ヘッダーから署名のための値抽出
    signature = request.META['HTTP_X_LINE_SIGNATURE']
    # リクエストのボディ抽出
    body = request.body.decode('utf-8')

    try:
        # 署名検証が通れば関数呼び出し
        handler.handle(body, signature)

    except LineBotApiError as err:
        print("LINE Messaging API Error: %s\n" % err.message)

    except InvalidSignatureError:
        # 署名検証失敗のときは例外
        return HttpResponseForbidden()
    return HttpResponse('OK', status=200)

# メッセージイベント処理


@handler.add(MessageEvent, message=TextMessage)
def handle_song_message(event):
    # 送信されたメッセージ
    text = event.message.text
    # 送信したユーザーのuserId
    user_id = event.source.user_id

    # 送信されたメッセージが20文字より多い場合はエラー処理
    if len(text) > 20:
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text="20文字以下のメッセージを送ってください"),
                StickerSendMessage(package_id="11537", sticker_id="52002739")
            ]
        )
    else:
        word_lis = morpho_analysis(text)
        user_data = Song.objects.get_or_create(line_user=user_id)
        for word in word_lis:
            data = search_song(word)
            for i in range(3):
                # ユーザーがDBに存在したらユーザーを関連付けて曲情報を格納し、存在しなかったら新規作成して曲情報追加
                Song.objects.create(
                    line_user=user_data, song_name=data[i]["title"], artist_name=data[i]["artist"], artwork_url=data[i]["url"])

                # 検索結果を返信
                line_bot_api.reply_message(
                    event.reply_token,
                    [
                        TextSendMessage(
                            text="曲名：" + data[i]["title"] + "\n"
                            "アーティスト名：" + data[i]["artist"] + "\n"
                            "アルバム：" + data[i]["album"] + "\n"
                            "URL:" + data[i]["url"] + "\n"
                        ),
                    ]
                )


GCP_API＿KEY = settings.GCP_API_KEY
GCP_URL = "https://language.googleapis.com/v1/documents:analyzeSyntax?key=" + GCP_API＿KEY

# 送信されたメッセージを形態素解析して単語のリストを返す関数


def morpho_analysis(text):
    header = {'Content-Type': 'application/json'}
    body = {
        "document": {
            "type": "PLAIN_TEXT",
            "language": "JA",
            "content": text
        },
        "encodingType": "UTF8"
    }

    # json形式で結果を受け取る
    response = requests.post(GCP_URL, headers=header, json=body).json()
    word_len = len(response["tokens"])
    word_list = []
    for i in range(word_len):
        word = response["tokens"][i]["lemma"]
        # 二文字以上の単語はリストに追加する
        if(len(word) >= 2):
            word_list += response["tokens"][i]["lemma"]
    return word_list

# paramsをitunesAPIで使えるようにエンコードする関数


def song_search_encode(data):
    query = ""
    for key, val in data.items():
        # termに空白があったら+に置き換える
        if key == "term":
            val.replace(" ", "+")
        query += key + "=" + val + "&"
    query = query[0:-1]
    return query

# 曲のjsonデータを使いやすいようにパースする関数


def song_parser(json_data):
    lst_in = json_data.get("results")
    lst_ret = []

    for d in lst_in:
        d_ret = {
            "title": d.get("trackName"),
            "artist": d.get("artistName"),
            "album": d.get("collectionName"),
            "url": urllib.parse.unquote(d.get("trackViewUrl")),
            "id_track": d.get("trackId"),
            "id_artist": d.get("artistId"),
            "id_album": d.get("collectionId"),
            "no_disk": d.get("discNumber"),
            "no_track": d.get("trackNumber"),
        }
        lst_ret.append(d_ret)
    return lst_ret

# 曲を検索してjsonデータを返す関数


def search_song(word):
    ITUNES_URL = 'https://itunes.apple.com/search?'
    params = {
        "term": word,
        "media": "music",
        "entity": "song",
        "attribute": "songTerm",
        "country": "JP",
        "lang": "ja_jp",  # "en_us",
        "limit": "3",
    }

    ITUNES_URL = ITUNES_URL + song_search_encode(params)
    res = requests.get(ITUNES_URL)
    json_d = json.loads(res.text)
    data = song_parser(json_d)
    return data
