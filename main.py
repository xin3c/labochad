import telebot
from telebot import types
import sqlite3

ADMIN_ID = 310343612  # Замените на ваш Telegram ID
TOKEN = '1720799328:AAHLuq-6tfk_1GLpf9CXTjv7t_A-uvoH3pU'

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

bot = telebot.TeleBot(TOKEN)

# cursor.execute('''
#    CREATE TABLE IF NOT EXISTS users (
#        user_id INTEGER PRIMARY KEY,
#        lab_number INTEGER
#    )
# ''')
# conn.commit()
# cursor.execute('''
#    ALTER TABLE users
#    ADD COLUMN payment_screenshot_id TEXT
# ''')
# conn.commit()
# cursor.execute('''
#   ALTER TABLE users
#   ADD COLUMN payment_status BOOLEAN DEFAULT FALSE
# ''')
# conn.commit()
# cursor.execute('''
#    ALTER TABLE users
#    ADD COLUMN variant_number INTEGER
# ''')
# conn.commit()
# cursor.execute('''
#     ALTER TABLE users
#     ADD COLUMN subject TEXT
# ''')
# conn.commit()


@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID, commands=['paid_users'])
# @bot.message_handler(commands=[''])
def paid_users(message):
    cursor.execute('SELECT user_id, lab_number FROM users WHERE payment_status = TRUE')
    paid_users_list = cursor.fetchall()
    response = "/get_payment_screenshot /send_file \nПользователи с оплаченными лабораторными:\n"
    for user in paid_users_list:
        response += f"ID: {user[0]}, Лабораторная №: {user[1]}\n"
    bot.send_message(message.chat.id, response)


def lab_choice_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for i in range(9, 11):
        markup.add(types.KeyboardButton(str(i)))
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add('Информатика', 'Языки программирования')
    msg = bot.send_message(message.chat.id, "Выберите предмет:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_subject)

def process_subject(message):
    subject = message.text
    msg = bot.send_message(message.chat.id, "Выберите номер лабораторной работы:", reply_markup=lab_choice_markup())
    bot.register_next_step_handler(msg, process_lab_choice, subject)

def process_lab_choice(message, subject):
    user_id = message.from_user.id
    lab_number = int(message.text)

    msg = bot.send_message(message.chat.id, "Введите номер вашего варианта:")
    bot.register_next_step_handler(msg, process_variant, user_id, lab_number, subject)


def process_variant(message, user_id, lab_number, subject):
    variant_number = int(message.text)

    cursor.execute('INSERT OR REPLACE INTO users (user_id, lab_number, variant_number, subject) VALUES (?, ?, ?, ?)', (user_id, lab_number, variant_number, subject))
    conn.commit()

    bot.send_message(message.chat.id, f"{subject}, Лабораторная {lab_number}, Вариант {variant_number} выбраны.")
    send_qr(message)
    bot.send_message(ADMIN_ID, f"Пользователь {user_id} выбрал {subject}, Лабораторную работу № {lab_number}, Вариант № {variant_number}.")

@bot.message_handler(commands=['send_qr'])
def send_qr(message):
    qr_image = 'qr.jpg'  # Укажите путь к изображению QR-кода
    bot.send_photo(message.chat.id, photo=open(qr_image, 'rb'))
    msg = bot.send_message(message.chat.id,
                           "Это QR-код СБП. Пришлите скриншот подтверждения оплаты. Наебать не выйдет, я проверяю каждый скрин и историю.")
    bot.register_next_step_handler(msg, process_payment_confirmation)


def process_payment_confirmation(message):
    if message.photo:
        user_id = message.from_user.id
        screenshot_file_id = message.photo[-1].file_id

        cursor.execute('UPDATE users SET payment_status = TRUE, payment_screenshot_id = ? WHERE user_id = ?',
                       (screenshot_file_id, user_id))
        conn.commit()

        bot.send_message(message.chat.id, "Подтверждение оплаты получено. Ожидайте, в течение суток бот пришлет вам архив с решением.")
    else:
        bot.send_message(message.chat.id,
                         "Пожалуйста, отправьте изображение. Пока нет скриншота, ваша запись не занесена в БД и не будет принята к исполнению.")


@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID, commands=['send_file'])
def request_user_id(message):
    msg = bot.send_message(message.chat.id, "Введите ID пользователя для отправки файла:")
    bot.register_next_step_handler(msg, receive_user_id)


def receive_user_id(message):
    global current_user_id
    current_user_id = message.text
    bot.send_message(message.chat.id, "зипку кинь")


@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID, content_types=['document'])
def receive_and_send_file(message):
    if message.document.mime_type == 'application/zip':
        file_id = message.document.file_id
        bot.send_document(current_user_id, file_id)
        bot.send_message(message.chat.id, "Файл отправлен.")
    else:
        bot.send_message(message.chat.id, "Ты чета попутал.")


@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID, commands=['get_payment_screenshot'])
def request_user_id_for_screenshot(message):
    msg = bot.send_message(message.chat.id, "Введите ID пользователя для просмотра скриншота оплаты:")
    bot.register_next_step_handler(msg, send_payment_screenshot)


def send_payment_screenshot(message):
    user_id = message.text
    cursor.execute('SELECT payment_screenshot_id FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result and result[0]:
        bot.send_photo(message.chat.id, result[0])
    else:
        bot.send_message(message.chat.id, "Скриншот оплаты не найден или не был отправлен.")


bot.polling()
