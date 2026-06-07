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

configuration = Configuration(access_token='12bFycKJF3vNyK1k70lDopzFbqIJe8SeOiYh5rlx3jaSUwKMNLE1HwKS7ssyUXrH17cs9Ukt0PyKPRLDc0rPpaZbN7JUUSdvSw26Kp5dv0dQbuVkq/1NqBKEGOzghgCC+lYWQZMyv/W+7If2aY0QnwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('722c39d14647e4ab0e138badc75bda8b')
MY_USER_ID = 'U0f77cc6eef0ee1070ea10b9a48ab17ed'
FOLDER_ID = '14UCyQ1rKcwawKP23tu4q8eIWYUQK-AcF'
CREDS_INFO = json.loads(os.environ.get('GOOGLE_CREDENTIALS', '{}'))

def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(CREDS_INFO, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=creds)

def save_note(text):
    service = get_drive_service()
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    content = f'{today}: {text}\n'
    file_metadata = {'name': f'notes_{datetime.now().strftime("%Y%m%d")}.txt', 'parents': [FOLDER_ID]}
    media = MediaInMemoryUpload(content.encode('utf-8'), mimetype='text/plain')
    service.files().create(body=file_metadata, media_body=media).execute()

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
    return 'Hello!'

@app.route('/check_stock')
def check_stock():
    alerts = []
    for symbol, name, currency in [('SOXX', 'SOXX', 'USD'), ('2330.TW', 'TSMC', 'TWD')]:
        price, change = get_change(symbol)
        if change is not None and change <= -3:
            alerts.append(f'{name} 下跌 {change:.1f}% 價格：{price:.2f} {currency}')
    if alerts:
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).push_message(PushMessageRequest(to=MY_USER_ID, messages=[TextMessage(text='\n'.join(alerts))]))
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
        reply = f'SOXX： USD（{change:+.1f}%）'
    elif upper in ['台積電', 'TSMC', '2330']:
        price, change = get_change('2330.TW')
        reply = f'台積電：{price:.0f} TWD（{change:+.1f}%）'
    elif upper == '00919':
        price, change = get_change('00919.TW')
        reply = f'00919：{price:.2f} TWD（{change:+.1f}%）'
    elif upper == '00878':
        price, change = get_change('00878.TW')
        reply = f'00878：{price:.2f} TWD（{change:+.1f}%）'
    else:
        save_note(text)
        reply = '已記錄！'
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply)]))

if __name__ == '__main__':
    app.run()
