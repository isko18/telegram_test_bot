Как правильно запускать

Клонируйте репозиторий:

git clone <repository-url>
cd <repository-folder>

Создайте виртуальное окружение:

python -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate

Установите зависимости:

pip install -r requirements.txt

Настройте бота:

Замените API_TOKEN на ваш токен Telegram-бота в файле bot.py.

Замените your_wallet_address_here на ваш реальный адрес кошелька.

Запустите бота:

python bot.py

Используйте команды бота в Telegram:

/start — для инициализации бота.

/check — для ручной проверки фармов.
