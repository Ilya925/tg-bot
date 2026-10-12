import os
import datetime
import math
import requests
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'ТОКЕН ВАШЕГО БОТА')

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

code_to_smile = {
    "Clear": "Ясно \U00002600",
    "Clouds": "Облачно \U00002601",
    "Rain": "Дождь \U00002614",
    "Drizzle": "Дождь \U00002614",
    "Thunderstorm": "Гроза \U000026A1",
    "Snow": "Снег \U0001F328",
    "Mist": "Туман \U0001F32B"
}

# Open-Meteo использует WMO-коды погоды, а не текстовые описания
# Поэтому сделаем свой словарь
WMO_CODES = {
    0: ("Ясно", "Ясно \U00002600"),
    1: ("Преимущественно ясно", "Ясно \U00002600"),
    2: ("Переменная облачность", "Облачно \U00002601"),
    3: ("Пасмурно", "Облачно \U00002601"),
    45: ("Туман", "Туман \U0001F32B"),
    48: ("Изморозь", "Туман \U0001F32B"),
    51: ("Слабая морось", "Дождь \U00002614"),
    53: ("Морось", "Дождь \U00002614"),
    55: ("Сильная морось", "Дождь \U00002614"),
    61: ("Небольшой дождь", "Дождь \U00002614"),
    63: ("Дождь", "Дождь \U00002614"),
    65: ("Сильный дождь", "Дождь \U00002614"),
    71: ("Небольшой снег", "Снег \U0001F328"),
    73: ("Снег", "Снег \U0001F328"),
    75: ("Сильный снег", "Снег \U0001F328"),
    80: ("Ливень", "Дождь \U00002614"),
    81: ("Сильный ливень", "Дождь \U00002614"),
    82: ("Очень сильный ливень", "Дождь \U00002614"),
    95: ("Гроза", "Гроза \U000026A1"),
    96: ("Гроза с градом", "Гроза \U000026A1"),
    99: ("Сильная гроза с градом", "Гроза \U000026A1"),
}


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply('Привет! Напиши мне название города и я пришлю сводку погоды.')


@dp.message_handler()
async def get_weather(message: types.Message):
    try:
        # Шаг 1: получаем координаты города через Geocoding API Open-Meteo
        geo_response = requests.get(
            'https://geocoding-api.open-meteo.com/v1/search',
            params={
                'name': message.text,
                'count': 1,
                'language': 'ru',
                'format': 'json'
            },
            timeout=10
        )
        geo_data = geo_response.json()

        if not geo_data.get('results'):
            await message.reply('Проверьте название города!')
            return

        place = geo_data['results'][0]
        lat = place['latitude']
        lon = place['longitude']
        city = place['name']
        country = place.get('country', '')

        # Шаг 2: получаем погоду по координатам
        weather_response = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m,relative_humidity_2m,surface_pressure,'
                           'wind_speed_10m,weather_code',
                'daily': 'sunrise,sunset',
                'timezone': 'auto'
            },
            timeout=10
        )
        data = weather_response.json()

        current = data['current']
        daily = data['daily']

        cur_temp = current['temperature_2m']
        humidity = current['relative_humidity_2m']
        pressure = current['surface_pressure']  # в гПа
        wind = current['wind_speed_10m']        # в км/ч
        weather_code = current['weather_code']

        # Давление переводим в мм.рт.ст. (1 гПа ≈ 0.750062 мм.рт.ст.)
        pressure_mmhg = math.ceil(pressure * 0.750062)

        # Время восхода/заката (уже в нужном часовом поясе)
        sunrise = datetime.datetime.fromisoformat(daily['sunrise'][0])
        sunset = datetime.datetime.fromisoformat(daily['sunset'][0])
        length_of_the_day = sunset - sunrise

        # Описание погоды
        description, wd = WMO_CODES.get(
            weather_code,
            ('Неизвестно', 'Посмотри в окно, я не понимаю, что там за погода...')
        )

        await message.reply(
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Погода в городе: {city}{', ' + country if country else ''}\n"
            f"Температура: {cur_temp:.1f}°C {wd}\n"
            f"Влажность: {humidity}%\n"
            f"Давление: {pressure_mmhg} мм.рт.ст\n"
            f"Ветер: {wind:.1f} км/ч\n"
            f"Восход солнца: {sunrise.strftime('%H:%M')}\n"
            f"Закат солнца: {sunset.strftime('%H:%M')}\n"
            f"Продолжительность дня: {length_of_the_day}\n"
            f"Хорошего дня!"
        )

    except requests.RequestException as e:
        await message.reply(f'Ошибка при запросе к API: {e}')
    except (KeyError, IndexError) as e:
        await message.reply('Не удалось обработать ответ сервера. Попробуйте ещё раз.')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)