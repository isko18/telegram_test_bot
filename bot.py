from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import aiohttp
import time, os

from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv('RPC_URL')

PURCHASE_AMOUNT = 100
PRICE_MULTIPLIER = 2
SELL_TIME_THRESHOLD = 600
SELL_LOSS_TIME_THRESHOLD = 1800
CHECK_INTERVAL = 60

farm_cache = {}

bot = Bot(token=os.getenv('API_TOKEN'))
dp = Dispatcher()

async def rpc_call(method, params=None):
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'https://app.ston.fi',
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
    }
    data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(RPC_URL, json=data, headers=headers) as response:
            response_data = await response.json()
            if response.status != 200 or "error" in response_data:
                print(f"Ошибка RPC вызова: {response_data}")
            return response_data

async def get_farm_list():
    return await rpc_call("farm.list")

async def buy_token(pool_address, amount):
    async with aiohttp.ClientSession() as session:
        data = {
            "userWalletAddress": "your_wallet_address_here",
            "offerAmount": str(amount),
            "askJettonAddress": pool_address,
            "minAskAmount": "1",
            "queryId": 12345
        }
        async with session.post(f"{RPC_URL}/swap/ton-to-jetton", json=data) as response:
            if response.status == 200:
                tx_params = await response.json()
                print(f"Параметры транзакции для покупки: {tx_params}")
            else:
                print(f"Ошибка при покупке токенов: {response.status}")

async def sell_token(pool_address):
    async with aiohttp.ClientSession() as session:
        data = {
            "userWalletAddress": "your_wallet_address_here",
            "offerJettonAddress": pool_address,
            "offerAmount": "1",
            "minAskAmount": "1",
            "queryId": 12345
        }
        async with session.post(f"{RPC_URL}/swap/jetton-to-ton", json=data) as response:
            if response.status == 200:
                tx_params = await response.json()
                print(f"Параметры транзакции для продажи: {tx_params}")
            else:
                print(f"Ошибка при продаже токенов: {response.status}")

async def get_current_price(pool_address):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{RPC_URL}/price/{pool_address}") as response:
            if response.status == 200:
                price_data = await response.json()
                return float(price_data.get("price", 0))
            else:
                # print(f"Ошибка при получении цены токена: {response.status}")
                return 0.0

async def monitor_price_and_sell(pool_address, purchase_price, purchase_time):
    while True:
        current_price = await get_current_price(pool_address)
        current_time = time.time()

        if current_price >= purchase_price * PRICE_MULTIPLIER and (current_time - purchase_time) >= SELL_TIME_THRESHOLD:
            # print(f"Цена удвоилась, продаю токены из пула: {pool_address}")
            await sell_token(pool_address)
            break

        if current_price < purchase_price and (current_time - purchase_time) >= SELL_LOSS_TIME_THRESHOLD:
            # print(f"Цена упала, продаю токены из пула: {pool_address}")
            await sell_token(pool_address)
            break

        print(f"Текущая цена: {current_price}. Условия для продажи не выполнены.")
        await asyncio.sleep(60)

async def handle_farm(farm):
    pool_address = farm['pool_address']
    pool_name = farm['pool_name']

    if pool_name in farm_cache and time.time() - farm_cache[pool_name] < 86400:
        # print(f"Фарм {pool_name} уже обработан недавно. Пропускаю.")
        return

    await buy_token(pool_address, PURCHASE_AMOUNT)

    purchase_price = await get_current_price(pool_address)
    purchase_time = time.time()

    farm_cache[pool_name] = purchase_time

    await monitor_price_and_sell(pool_address, purchase_price, purchase_time)

async def check_farms():
    farms_data = await get_farm_list()

    for farm in farms_data.get('result', {}).get('farms', []):
        pool_address = farm.get('pool_address')
        status = farm.get('status')
        version = farm.get('version')
        pool_name = farm.get('pool_name', '')

        if status == "pause_all" and "TON" in pool_name and "USDT" not in pool_name:
            print(f"Фарм подходит | Пул: {pool_name}, Адрес: {pool_address}")
            await handle_farm(farm)
        else:
            print(f"Фарм не подходит. Пул: {pool_name}, Статус: {status}, Версия: {version}")

@dp.message(Command('start'))
async def start_handler(message: types.Message):
    await message.reply("Привет! Я бот для фарминга. Я буду проверять фармы и торговать токенами.")

@dp.message(Command('check'))
async def check_handler(message: types.Message):
    await message.reply("Начинаю проверку фармов...")
    try:
        await check_farms()
        await message.reply("Проверка фармов завершена.")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

async def periodic_check():
    while True:
        print("Запуск автоматической проверки фармов...")
        await check_farms()
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    print("Запуск бота...")
    asyncio.create_task(periodic_check())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
