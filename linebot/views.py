from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden

import requests

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
        word_list = morpho_analysis(text)


GCP_API＿KEY = "AIzaSyCYoldfc45jmShnLyM0AD0pjxrwn8hJ8Fc"
GCP_URL = "https://language.googleapis.com/v1/documents:analyzeSyntax?key=" + GCP_API＿KEY

# 送信されたメッセージを形態素解析する関数


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
