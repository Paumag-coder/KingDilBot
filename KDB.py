import telebot
import json
import os

# === НАСТРОЙКИ ===
TOKEN = '8363133718:AAGcdIhpeulIvbixgB3OQmYRpEvTYgXLYyg'  # ← Замени на токен от @BotFather
bot = telebot.TeleBot(TOKEN)

# Файлы данных
USERS_FILE = 'users.json'
POLL_FILE = 'poll_data.json'

# Участники
PARTICIPANTS = ["Гамам", "Коден", "Аллвед", "Олвин"]

# --- Загрузка привязок пользователей ---
def load_user_bindings():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    except Exception as e:
        print(f"Ошибка загрузки {USERS_FILE}:", e)
        return {}

def save_user_bindings(bindings):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in bindings.items()}, f, ensure_ascii=False, indent=2)

# --- Загрузка данных опроса ---
def load_poll_data():
    if not os.path.exists(POLL_FILE):
        return {
            "answers": {name: None for name in PARTICIPANTS},
            "leader": None,
            "judge": None,
            "poll_message_id": None,
            "poll_chat_id": None,
            "editable": []
        }
    try:
        with open(POLL_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Гарантируем структуру
        if "answers" not in data:
            data["answers"] = {}
        for name in PARTICIPANTS:
            if name not in data["answers"]:
                data["answers"][name] = None
        if "editable" not in data:
            data["editable"] = []
        return data
    except Exception as e:
        print(f"Ошибка загрузки {POLL_FILE}:", e)
        return {
            "answers": {name: None for name in PARTICIPANTS},
            "leader": None,
            "judge": None,
            "poll_message_id": None,
            "poll_chat_id": None,
            "editable": []
        }

def save_poll_data():
    with open(POLL_FILE, 'w', encoding='utf-8') as f:
        json.dump(poll_data, f, ensure_ascii=False, indent=2)

# --- Глобальные переменные ---
user_to_name = load_user_bindings()
poll_data = load_poll_data()  # Это переменная, не функция!

# === КОМАНДЫ ===

@bot.message_handler(commands=['Голосуем'])
def start_poll(message):
    global poll_data

    # Открепляем старое
    if poll_data["poll_chat_id"] and poll_data["poll_message_id"]:
        try:
            bot.unpin_chat_message(poll_data["poll_chat_id"], poll_data["poll_message_id"])
        except Exception as e:
            print("Не удалось открепить:", e)

    # Сбрасываем
    poll_data = {
        "answers": {name: None for name in PARTICIPANTS},
        "leader": None,
        "judge": None,
        "poll_message_id": None,
        "poll_chat_id": None,
        "editable": []
    }
    save_poll_data()

    # Создаём и закрепляем
    update_poll_form(message.chat.id)
    try:
        bot.pin_chat_message(message.chat.id, poll_data["poll_message_id"], disable_notification=True)
    except Exception as e:
        print("Ошибка закрепления:", e)

@bot.message_handler(commands=['meis'])
def bind_me_to_name(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Используй: `/meis Имя`", parse_mode="Markdown")
        return

    name = args[1].strip()
    user_id = message.from_user.id

    if name not in PARTICIPANTS:
        bot.reply_to(message, f"❌ Нет такого участника. Доступные: {', '.join(PARTICIPANTS)}")
        return

    if user_id in user_to_name:
        old_name = user_to_name[user_id]
        bot.reply_to(message, f"🔹 Вы уже привязаны к: {old_name}")
        return

    if name in user_to_name.values():
        bot.reply_to(message, f"❌ Имя '{name}' уже занято.")
        return

    user_to_name[user_id] = name
    save_user_bindings(user_to_name)
    bot.reply_to(message, f"✅ Вы успешно привязаны к: *{name}*", parse_mode="Markdown")

@bot.message_handler(commands=['lead'])
def set_leader(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Используй: `/lead Имя` или `/lead снять`", parse_mode="Markdown")
        return

    name = args[1].strip()
    if name == "снять":
        poll_data["leader"] = None
        bot.reply_to(message, "✅ Лидер снят.")
    elif name in PARTICIPANTS:
        poll_data["leader"] = name
        bot.reply_to(message, f"✊ {name} назначен лидером.")
    else:
        bot.reply_to(message, f"❌ Нет такого участника.")
        return

    save_poll_data()
    update_poll_form()

@bot.message_handler(commands=['jud'])
def set_judge(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Используй: `/jud Имя` или `/jud снять`", parse_mode="Markdown")
        return

    name = args[1].strip()
    if name == "снять":
        poll_data["judge"] = None
        bot.reply_to(message, "✅ Судья снят.")
    elif name in PARTICIPANTS:
        poll_data["judge"] = name
        bot.reply_to(message, f"⚖️ {name} назначен судьёй.")
    else:
        bot.reply_to(message, f"❌ Нет такого участника.")
        return

    save_poll_data()
    update_poll_form()

@bot.message_handler(commands=['dis'])
def reset_answer(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return
    name = args[1].strip()
    if name not in PARTICIPANTS:
        return
    if name not in poll_data["editable"]:
        poll_data["editable"].append(name)
        save_poll_data()
        update_poll_form()

# === ОБНОВЛЕНИЕ ФОРМЫ ===
def update_poll_form(chat_id=None):
    global poll_data

    text = "📋 **Голосование**\n\n"
    for name in PARTICIPANTS:
        answer = poll_data["answers"][name]
        leader_emoji = "✊ " if poll_data["leader"] == name else ""
        judge_emoji = "⚖️ " if poll_data["judge"] == name else ""
        status = "✅" if answer is not None and name not in poll_data["editable"] else "🟡"
        answer_text = f"`{answer}`" if answer is not None else "ожидает ответа"
        text += f"{leader_emoji}{judge_emoji}{status} {name}: {answer_text}\n"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Проголосовать", callback_data="submit_answer"))

    if chat_id:
        try:
            sent = bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
            poll_data["poll_message_id"] = sent.message_id
            poll_data["poll_chat_id"] = chat_id
            save_poll_data()
        except Exception as e:
            print("Ошибка отправки формы:", e)
    else:
        try:
            if poll_data["poll_message_id"] and poll_data["poll_chat_id"]:
                bot.edit_message_text(
                    chat_id=poll_data["poll_chat_id"],
                    message_id=poll_data["poll_message_id"],
                    text=text,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
        except Exception as e:
            print("Ошибка обновления формы:", e)

# === КНОПКИ ОТВЕТА ===
@bot.callback_query_handler(func=lambda call: call.data == "submit_answer")
def submit_answer(call):
    user_id = call.from_user.id

    if user_id not in user_to_name:
        bot.answer_callback_query(call.id, "Вы не привязаны. Используйте /meis Имя")
        return

    name = user_to_name[user_id]

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("Пас - власть", callback_data="ans:pass_vlast"),
        telebot.types.InlineKeyboardButton("Пас - судья", callback_data="ans:pass_sud")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("Да - X", callback_data="ans:da_x"),
        telebot.types.InlineKeyboardButton("Нет - X", callback_data="ans:no_x")
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✊ {name}, выберите ответ:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans:"))
def handle_answer_choice(call):
    user_id = call.from_user.id
    action = call.data.split(":")[1]

    if user_id not in user_to_name:
        bot.answer_callback_query(call.id, "Вы не привязаны.")
        return

    name = user_to_name[user_id]

    if action == "pass_vlast":
        final_answer = "Пас - власть"
        save_and_update(call.message.chat.id, call.message.message_id, name, final_answer)
        bot.answer_callback_query(call.id, f"✅ {name}: Пас - власть")

    elif action == "pass_sud":
        final_answer = "Пас - судья"
        save_and_update(call.message.chat.id, call.message.message_id, name, final_answer)
        bot.answer_callback_query(call.id, f"✅ {name}: Пас - судья")

    elif action == "da_x":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔢 Сколько власьт хочешь вложить в Да?:",
            reply_markup=None
        )
        bot.register_next_step_handler(call.message, process_number, name, "Да - {}")

    elif action == "no_x":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔢 Сколько власти хочешь вложить в Нет?",
            reply_markup=None
        )
        bot.register_next_step_handler(call.message, process_number, name, "Нет - {}")

def process_number(message, name, template):
    try:
        num = int(message.text.strip())
        if num < 1 or num > 100:
            bot.send_message(message.chat.id, "❌ Число должно быть от 1 до 100.")
            bot.register_next_step_handler(message, process_number, name, template)
            return
        final_answer = template.format(num)
        save_and_update(message.chat.id, None, name, final_answer)
        bot.send_message(message.chat.id, f"✅ {name}, ваш ответ: *{final_answer}*", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число.")
        bot.register_next_step_handler(message, process_number, name, template)

def save_and_update(chat_id, message_id, name, answer):
    poll_data["answers"][name] = answer
    if name in poll_data["editable"]:
        poll_data["editable"].remove(name)
    save_poll_data()
    update_poll_form()

# === ЗАПУСК ===
print("✅ Бот запущен и готов к работе...")
bot.polling(none_stop=True)
