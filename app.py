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
