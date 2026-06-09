from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, PushMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import yfinance as yf
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime
import json, os

app = Flask(__name__)

configuration = Configuration(access_token=os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
MY_USER_ID = 'U0f77cc6eef0ee1070ea10b9a48ab17ed'
FOLDER_ID = '14UCyQ1rKcwawKP23tu4q8eIWYUQK-AcF'

def get_drive_service():
    raw = os.environ.get('GOOGLE_CREDENTIALS', '{}').strip().strip("'\"")
    creds_info = json.loads(raw)

def save_note(text):
    service = get_drive_service()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    filename = f'notes_{datetime.now().strftime("%Y%m")}.txt'
    new_line = f'{now}: {text}\n'

    # 找看看這個月的檔案存在嗎
    results = service.files().list(
        q=f"name='{filename}' and '{FOLDER_ID}' in parents and trashed=false",
        fields='files(id)').execute()
    files = results.get('files', [])

    if files:
        # 檔案存在，讀出來再追加
        file_id = files[0]['id']
        existing = service.files().get_media(fileId=file_id).execute()
        updated = existing.decode('utf-8') + new_line
        media = MediaInMemoryUpload(updated.encode('utf-8'), mimetype='text/plain')
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        # 新建檔案
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        media = MediaInMemoryUpload(new_line.encode('utf-8'), mimetype='text/plain')
        service.files().create(body=file_metadata, media_body=media).execute()

def get_recent_notes(n=5):
    service = get_drive_service()
    filename = f'notes_{datetime.now().strftime("%Y%m")}.txt'
    results = service.files().list(
        q=f"name='{filename}' and '{FOLDER_ID}' in parents and trashed=false",
        fields='files(id)').execute()
    files = results.get('files', [])
    if not files:
        return '這個月還沒有筆記！'
    file_id = files[0]['id']
    content = service.files().get_media(fileId=file_id).execute()
    lines = content.decode('utf-8').strip().split('\n')
    recent = lines[-n:] if len(lines) >= n else lines
    return '\n'.join(recent)

def get_change(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period='2d')
    if len(hist) >= 2:
        prev = hist['Close'].iloc[-2]
        curr = hist['Close'].iloc[-1]
        change = (curr - prev) / prev * 100
        return curr, change
    return None, None

@app.route('/')
def home():
    return 'Alison Bot is running!'

@app.route('/check_stock')
def check_stock():
    alerts = []
    for symbol, name, currency in [('SOXX', 'SOXX', 'USD'), ('2330.TW', 'TSMC', 'TWD')]:
        price, change = get_change(symbol)
        if change is not None and change <= -3:
            alerts.append(f'{name} 下跌 {change:.1f}% 價格：{price:.2f} {currency}')
    if alerts:
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).push_message(
                PushMessageRequest(to=MY_USER_ID, messages=[TextMessage(text='\n'.join(alerts))]))
    return 'OK'

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip()
    upper = text.upper()

    if upper == 'SOXX':
        price, change = get_change('SOXX')
        reply = f'SOXX：{price:.2f} USD（{change:+.1f}%）'
    elif upper in ['台積電', 'TSMC', '2330']:
        price, change = get_change('2330.TW')
        reply = f'台積電：{price:.0f} TWD（{change:+.1f}%）'
    elif upper == '00919':
        price, change = get_change('00919.TW')
        reply = f'00919：{price:.2f} TWD（{change:+.1f}%）'
    elif upper == '00878':
        price, change = get_change('00878.TW')
        reply = f'00878：{price:.2f} TWD（{change:+.1f}%）'
    elif upper in ['筆記', '最近', 'NOTE', 'NOTES']:
        reply = get_recent_notes(5)
    else:
        save_note(text)
        reply = f'✅ 已記錄！'

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply)]))

if __name__ == '__main__':
    app.run()