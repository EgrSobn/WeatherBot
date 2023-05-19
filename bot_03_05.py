import telebot
from telebot.types import Chat
import requests
from translate import Translator
import datetime as dt
import sqlite3
# import json
import time
# токен телеграм-бота
token = '5873420107:AAEl2BK1ojlcwPw9ipOGhfqVBj6IrIyLCiY'
# токен OpenWeatherApi
weather_token = '4b2f11bf582a82a29f0772230f12c83a'
bot = telebot.TeleBot(token)
# Подключаемся к базе данных
try:
    conn = sqlite3.connect("users.sqlite3")
    print('первое подключение к БД для всякого')
except: print('db is not connected')
cursor = conn.cursor()

# Создаем таблицу для хранения состояний пользователей
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, state TEXT)''')
conn.commit
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

conn.close()
# функция получения данных с OpenWeatherMap
def get_weather_data(place_en, place_ru, api_key=weather_token):
  print('Получение погоды начало')
  # ссылка на API
  url = f'https://api.openweathermap.org/data/2.5/weather?q={place_en}&appid={api_key}'
  res = requests.get(url)
  data = res.json()

  # подключение переводчика
  translator = Translator(from_lang="en", to_lang="ru")

  #преобразование данных
  weather = data['weather'][0]['main'] + ": " + data['weather'][0]['description']
  weather = translator.translate(weather)
  temp = round(data['main']['temp'] - 273.15)
  wind_speed = data['wind']['speed']
  fells = round(data['main']['feels_like'] - 273.15)
  pres = data['main']['pressure']
  hum = data['main']['humidity']
  output=f'Погода в городе <b>{place_ru}</b>: <b>{weather}</b>\nТемпература: <b>{temp} °C</b>, ощущается как <b>{fells} °C</b>\nСкорость ветра: <b>{wind_speed} м/с</b>\nДавление: <b>{pres * 0.75}  мм рт.ст.</b>\nВлажность <b>{hum} %</b>'
  print('Получение погоды начало')
  return output

def send_weather(message, place_en, place_ru):
  flag = False
  while not flag:
    time.sleep(5)
    try:
      conn = sqlite3.connect("users.sqlite3")
      print('подключение к БД для обработки запроса пользователя')
      cursor = conn.cursor()
      cursor.execute("SELECT state FROM users WHERE id=?", (message.chat.id,))
      user_state = cursor.fetchone()
    except:
      print('db is not connected')
    if user_state[0] == "nonactive":
      conn.close()
      return 0
    if user_state[0] == 'freeze':
      bot.send_message(message.chat.id,text=get_weather_data(place_en, place_ru, api_key=weather_token),parse_mode='html')
    conn.close()
  return None

# обработка команды /start
@bot.message_handler(commands=["start"])
def start(message):
  try:
    conn = sqlite3.connect("users.sqlite3")
    print('подключение к БД для старта')
  except: print('db is not connected')
  cursor = conn.cursor()
  cursor.execute("UPDATE users SET state=? WHERE id=?", ("active", message.chat.id))
  conn.commit()
  conn.close()
  bot.send_message(message.chat.id, text=f'Привет, <b>{message.from_user.first_name} {message.from_user.last_name}</b>! Я буду отправлять тебе погоду.', parse_mode='html')
  bot.send_message(message.chat.id, text=f'Напиши название своего горда')

# обработка команды /test
@bot.message_handler(commands=["test"])
def start(message):
  bot.send_message(message.chat.id, text=f'Тестовая команда, которая показывает формат вывода данных', parse_mode='html')
  bot.send_message(message.chat.id, text=get_weather_data(place_en="Moscow", place_ru = 'Москва'), parse_mode='html')

# обработка команды /stop
@bot.message_handler(commands=['stop'])
def stop(message):
  try:
    conn = sqlite3.connect("users.sqlite3")
    print('подключение к БД для остановки')
  except: print('db is not connected')
  cursor = conn.cursor()
  cursor.execute("UPDATE users SET state=? WHERE id=?", ("nonactive", message.chat.id))
  conn.commit()
  bot.send_message(message.chat.id, "Бот остановлен для вас.")
  conn.close()


@bot.message_handler(content_types=['text'])
def handle_message(message):
  # Получаем состояние пользователя из БД
  try:
    conn = sqlite3.connect("users.sqlite3")
    print('подключение к БД для обработки запроса пользователя')
    cursor = conn.cursor()
    cursor.execute("SELECT state FROM users WHERE id=?", (message.chat.id,))
    user_state = cursor.fetchone()
  except: print('db is not connected')
  if user_state is None:
    # Если пользователь не найден в БД, создаем запись с состоянием "активен"
    cursor.execute("INSERT INTO users (id, state) VALUES (?, ?)", (message.chat.id, "active"))
    conn.commit()
  elif user_state[0] == "nonactive":
    bot.send_message(message.chat.id, "Бот остановлен для вас.")
    return
  elif user_state[0] == 'active':
  # получаем текст сообщения от пользователя
    place_ru = message.text
    if place_ru == 'Санкт-Петербург' or place_ru == 'Санкт Петербург':
      place_en = 'Saint Petersburg'
    else:
      translator = Translator(from_lang="ru", to_lang="en")
      place_en = translator.translate(place_ru)
      print(place_en, ' ' ,place_ru)
    # есть проблема с городом Санкт-Петербург, так как существуют 2 города с таким названием
    # исправим эту проблему небольшим костылем
    try:
      cursor.execute("UPDATE users SET state=? WHERE id=?", ("freeze", message.chat.id))
      conn.commit()
      conn.close()
      send_weather(message, place_en, place_ru)
    except:
      bot.send_message(message.chat.id, text=f'Города с таким названием не найдено, проверьте правильность написания')

bot.polling()