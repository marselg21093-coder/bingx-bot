"""
BingX Telegram Auto-Poster
Отправляет пост с картинкой и актуальным курсом BTC/ETH
Запускается через GitHub Actions 3 раза в день
"""

import os
import random
import sys
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@tokenruru"
REF_LINK = "https://bingx.com/ru/partner/A888"
POST_TYPE = sys.argv[1] if len(sys.argv) > 1 else "morning"

IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=900&q=80",
    "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=900&q=80",
    "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=900&q=80",
    "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=900&q=80",
