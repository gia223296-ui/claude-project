from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, PushMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import yfinance as yf
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import json, os, base64

app = Flask(__name__)

configuration = Configuration(access_token=os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
MY_USER_ID = 'U0f77cc6eef0ee1070ea10b9a48ab17ed'
SHEET_ID = '1abKvPsMOz4k2q5jvQz1d4zHfvqKamKRXSGKCukSebOo'

def get_sheets_service():
    try:
        raw = os.environ.get('GOOGLE_CREDENTIALS_B64', '')
        creds_info = json.loads(base64.b64decode(raw).decode('utf-8'))
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f'Sheets error: {e}')
        return None

def save_note(text):
    service = get_sheets_service()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    values = [[now, text]]
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range='A:B',
        valueInputOption='RAW',
        body={'values': values}
    ).execute()

def get_recent_notes(n=5):
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range='A:B'
    ).execute()
    rows = result.get('values', [])
    if not rows:
        return '這個月還沒有筆記！'
    recent = rows[-n:] if len(rows) >= n else rows
    return '\n'.join([f'{r[0]}: {r[1]}' for r in recent if len(r) >= 2])

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
        reply = '✅ 已記錄！'

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply)]))

if __name__ == '__main__':
    app.run()