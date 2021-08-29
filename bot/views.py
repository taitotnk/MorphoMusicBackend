from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import urllib
import re
import json
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from api.models import Song, Lineuser
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerSendMessage, FlexSendMessage
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
        Lineuser_obj = Lineuser.objects.get(user_id=user_id)
        # 停止されていれば20文字以上のメッセージを送信できる
        if Lineuser_obj.stop is False:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="20文字以下のメッセージを送ってください"),
                    StickerSendMessage(package_id="11537",
                                       sticker_id="52002739")
                ]
            )
    elif text == "履歴":
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text="こちらから履歴が見られます" + "\n"
                                "URL: https://liff.line.me/1655768482-PVW85dOD")
            ]
        )
    elif text == "停止":
        Lineuser_obj = Lineuser.objects.get(user_id=user_id)
        # すでに停止状態
        if Lineuser_obj.stop is True:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="既にbotは停止状態です。")
                ]
            )
        # 停止されていなければ停止状態に更新する
        else:
            Lineuser_obj.stop = True
            Lineuser_obj.save()
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="bot返信機能を停止しました。")
                ]
            )
    elif text == "解除":
        Lineuser_obj = Lineuser.objects.get(user_id=user_id)
        # 停止されていれば解除する
        if Lineuser_obj.stop is True:
            Lineuser_obj.stop = False
            Lineuser_obj.save()
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="bot返信機能の停止を解除しました。")
                ]
            )
        # 停止されていなければそのまま
        else:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="停止していないので解除状態です。")
                ]
            )
    else:
        word_lis = morpho_analysis(text)
        # 形態素解析したリストの中身が空だったらエラー処理して返す
        if len(word_lis) == 0:
            print("error:analysis result is empty")
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text="もう少し長い文章でメッセージを送ってください。\n例：今日の天気はいいですね。"
                    ),
                ]
            )
            return
        # timeoutしたらエラー処理
        if word_lis == "requests.exceptions.Timeout":
            print("error:timeout")
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(
                        text="サーバー側に問題があるようです。\n復旧するまでお待ちください。\n"
                    ),
                ]
            )
            return

        user_data, _ = Lineuser.objects.get_or_create(user_id=user_id)

        # 曲情報をまとめたリスト
        song_info = []

        for word in word_lis:
            data = search_song(word)
            # 検索結果が0件だったら次のワードで検索
            if len(data) == 0:
                continue
            song_info.append(data)

        # 曲情報が空だった場合は見つからない返信をする
        if len(song_info) == 0:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="この文章では曲が見つかりませんでした。\n他の文章でお試しください。")
                ]
            )
            return
        # ユーザーがDBに存在したらユーザーを関連付けて曲情報を格納し、存在しなかったら新規作成して曲情報追加
        create_list = []
        msg_array = []
        print(f"type:{type(song_info)}")
        print(f"song_info:{(song_info)}")
        for i in range(len(song_info)):
            for j in range(len(song_info[i])):
                song_name = song_info[i][j].get("title")
                artist_name = song_info[i][j].get("artist")
                buy_url = song_info[i][j].get("url")
                artwork_url = song_info[i][j].get("artwork")
                create_list.append(Song(
                    line_user=user_data,
                    song_name=song_name,
                    artist_name=artist_name,
                    buy_url=buy_url,
                    artwork_url=artwork_url
                ))
                msg = render_to_string(
                    "message.json", {"artwork": artwork_url,
                                     "title": song_name, "artist": artist_name, "url": buy_url}
                )
                print(msg)
                msg_array.append(FlexSendMessage(
                    alt_text=f"曲名：{song_name}",
                    contents=json.loads(msg)
                ))
        Song.objects.bulk_create(create_list)

        # userのstopカラムがFalseだったら返信をする
        if user_data.stop is False:
            # 検索結果を返信
            try:
                line_bot_api.reply_message(event.reply_token, msg_array)
            except LineBotApiError as e:
                print(e)
                line_bot_api.reply_message(
                    event.reply_token, [
                        TextSendMessage(
                            text="検索曲数が多いので、返信できませんでした。\nお手数ですが、「履歴」と返信し検索結果を確認してください。\n")
                    ])


# GCP APIキー
GCP_API＿KEY = settings.GCP_API_KEY
GCP_URL = "https://language.googleapis.com/v1/documents:analyzeSyntax?key=" + GCP_API＿KEY

# Spotify APIキー
SPOTIFY_CLIENT_ID = settings.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET

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

    # connect, read timeoutを10秒に設定
    try:
        # json形式で結果を受け取る
        response = requests.post(GCP_URL, headers=header,
                                 json=body, timeout=10.0).json()
    # timeoutならエラー処理
    except requests.exceptions.ConnectTimeout:
        return "requests.exceptions.Timeout"

    word_len = len(response["tokens"])
    word_list = []
    # 漢字用パターン
    kanji = re.compile(r'^[\u4E00-\u9FD0]+$')
    for i in range(word_len):
        word = response["tokens"][i]["lemma"]
        # 二文字以上の単語はリストに追加する
        if(len(word) >= 2):
            word_list.append(response["tokens"][i]["lemma"])
        # wordが漢字なら一文字でも追加
        elif kanji.fullmatch(word):
            word_list.append(response["tokens"][i]["lemma"])
    return word_list


# 曲のjsonデータを使いやすいようにパースする関数
def song_parser(json_data):
    lst_ret = []

    for track in json_data['tracks']['items']:
        d_ret = {
            "title": track['name'],
            "artist": track['album']['artists'][0]['name'],
            "artwork": track['album']['images'][1]['url'],
            "url": urllib.parse.unquote(track['external_urls']['spotify']),
        }
        lst_ret.append(d_ret)
    return lst_ret

# 曲を検索してjsonデータを返す関数


def search_song(word):
    client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(
        SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    spotify = spotipy.Spotify(
        client_credentials_manager=client_credentials_manager)
    results = spotify.search(q='track:' + word, limit=1,
                             offset=0, type='track', market=None)
    # 曲が1件も見つからなかったら空リストを返す
    if results['tracks']['items'] == []:
        return []
    data = song_parser(results)
    return data
