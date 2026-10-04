import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8876442435:AAFu7AnFXELjK4vroVNRcg0AYQK72tup928")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "-1004489070783"))

WORK_START = "07:30"
WORK_END = "22:00"

MENU = {
    "espresso": {"name": "Эспрессо", "price": 150, "emoji": "☕"},
    "americano": {"name": "Американо", "price": 180, "emoji": "☕"},
    "cappuccino": {"name": "Капучино", "price": 250, "emoji": "☕"},
    "latte": {"name": "Латте", "price": 270, "emoji": "🥛"},
    "raf": {"name": "Раф", "price": 300, "emoji": "🥛"},
    "flat_white": {"name": "Флэт Уайт", "price": 280, "emoji": "☕"},
    "mocha": {"name": "Мокко", "price": 320, "emoji": "🍫"},
    "cocoa": {"name": "Какао", "price": 220, "emoji": "🍫"},
    "black_tea": {"name": "Чёрный чай", "price": 150, "emoji": "🍵"},
    "green_tea": {"name": "Зелёный чай", "price": 150, "emoji": "🍵"},
    "lemonade": {"name": "Лимонад", "price": 200, "emoji": "🍋"},
    "berry_smoothie": {"name": "Ягодный смузи", "price": 280, "emoji": "🫐"},
    "croissant": {"name": "Круассан", "price": 180, "emoji": "🥐"},
    "cheesecake": {"name": "Чизкейк", "price": 250, "emoji": "🍰"},
    "cookie": {"name": "Печенье", "price": 100, "emoji": "🍪"},
}
