import os
import telebot
from telebot import types
from flask import Flask, request
import json

# Инициализация Flask приложения
app = Flask(__name__)

# Получаем токен бота из переменных окружения
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Папка для хранения данных пользователей
DATA_FOLDER = "Json"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Функция загрузки данных пользователя
def load_user_data(user_id):
    user_file = os.path.join(DATA_FOLDER, f'{user_id}.json')
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            return json.load(f)
    else:
        return None

# Функция сохранения данных пользователя
def save_user_data(user_data):
    user_file = os.path.join(DATA_FOLDER, f'{user_data["user_id"]}.json')
    with open(user_file, 'w') as f:
        json.dump(user_data, f)

# Проверка на уникальность ника
def is_nickname_taken(nickname):
    for user_file in os.listdir(DATA_FOLDER):
        with open(os.path.join(DATA_FOLDER, user_file), 'r') as f:
            data = json.load(f)
            if data.get('nickname') == nickname:
                return True
    return False

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    
    if user_data is None:
        msg = bot.send_message(user_id, "Привет! Введи свой уникальный ник:")
        bot.register_next_step_handler(msg, process_nickname)
    else:
        bot.send_message(user_id, f"С возвращением, {user_data['nickname']}!")
        show_menu(message)

def process_nickname(message):
    user_id = message.from_user.id
    nickname = message.text.strip()
    
    if is_nickname_taken(nickname):
        msg = bot.send_message(user_id, "Этот ник уже занят. Попробуй другой:")
        bot.register_next_step_handler(msg, process_nickname)
    else:
        user_data = {
            "user_id": user_id,
            "nickname": nickname,
            "chebureks": 0,
            "multiplier": 1,
            "multiplier_cost": 10
        }
        save_user_data(user_data)
        bot.send_message(user_id, f"Отлично, {nickname}! Теперь ты в игре.")
        show_menu(message)

# Функция показа основного меню
def show_menu(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    click_button = types.KeyboardButton("Клик")
    shop_button = types.KeyboardButton("Магазин")
    profile_button = types.KeyboardButton("Профиль")
    top5_button = types.KeyboardButton("Топ 5")
    keyboard.add(click_button, shop_button)
    keyboard.add(profile_button, top5_button)
    bot.send_message(message.chat.id, "Выбери действие:", reply_markup=keyboard)

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)

    if "multiplier" not in user_data:
        user_data["multiplier"] = 1
    if "multiplier_cost" not in user_data:
        user_data["multiplier_cost"] = 10

    if message.text == "Клик":
        user_data['chebureks'] += user_data['multiplier']
        save_user_data(user_data)
        bot.send_message(user_id, f"Ты съел чебурек! Всего чебуреков: {user_data['chebureks']}")
    
    elif message.text == "Магазин":
        show_shop(message)
    
    elif message.text == "Профиль":
        bot.send_message(user_id, f"Твой профиль:\nНик: {user_data['nickname']}\nЧебуреки: {user_data['chebureks']}\nМножитель клика: x{user_data['multiplier']}\nЦена множителя: {user_data['multiplier_cost']} чебуреков")
    
    elif message.text == "Топ 5":
        top_users = []
        for user_file in os.listdir(DATA_FOLDER):
            with open(os.path.join(DATA_FOLDER, user_file), 'r') as f:
                data = json.load(f)
                top_users.append((data['nickname'], data['chebureks']))
        top_users = sorted(top_users, key=lambda x: x[1], reverse=True)[:5]
        top_message = "Топ 5 поедателей чебуреков:\n"
        for i, user in enumerate(top_users, 1):
            top_message += f"{i}. {user[0]}: {user[1]} чебуреков\n"
        bot.send_message(user_id, top_message)

# Функция показа магазина
def show_shop(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)

    keyboard = types.InlineKeyboardMarkup()
    if user_data['multiplier'] < 32:
        multiplier_button = types.InlineKeyboardButton(
            text=f"Купить x2 Множитель ({user_data['multiplier_cost']} чебуреков)", 
            callback_data="buy_multiplier"
        )
        keyboard.add(multiplier_button)
    else:
        bot.send_message(user_id, "Ты уже достиг максимального множителя x32.")
    
    bot.send_message(message.chat.id, "Добро пожаловать в магазин улучшений!", reply_markup=keyboard)

# Обработчик нажатий на кнопки магазина
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    user_data = load_user_data(user_id)

    if call.data == "buy_multiplier":
        if user_data['multiplier'] < 32:
            if user_data['chebureks'] >= user_data['multiplier_cost']:
                user_data['chebureks'] -= user_data['multiplier_cost']
                user_data['multiplier'] *= 2
                user_data['multiplier_cost'] *= 2
                save_user_data(user_data)
                bot.answer_callback_query(call.id, f"Ты купил x2 к множителю! Новая сила клика: x{user_data['multiplier']}. Новая цена: {user_data['multiplier_cost']} чебуреков.")
            else:
                bot.answer_callback_query(call.id, "Недостаточно чебуреков!")
        else:
            bot.answer_callback_query(call.id, "Ты уже достиг максимального множителя x32.")

# Обработка вебхуков через Flask
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '!', 200

# Установка вебхука
@app.route("/set_webhook", methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL')}/{TOKEN}"
    if bot.set_webhook(url=webhook_url):
        return "Webhook установлен!", 200
    else:
        return "Ошибка при установке вебхука", 400

# Запуск сервера Flask
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_URL')}/{TOKEN}")
    app.run(host="0.0.0.0", port=port)