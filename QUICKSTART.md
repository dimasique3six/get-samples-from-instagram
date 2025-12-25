# 🎵 Быстрая установка - Шпаргалка

## 📦 1. Установка (5 минут)

```bash
# Подключитесь к серверу
ssh user@server.com

# Создайте директорию
mkdir -p ~/instagram-samples-bot
cd ~/instagram-samples-bot

# Загрузите файлы (через scp с вашего компьютера)
# scp instagram-samples-bot.tar.gz username@server:~/

# Распакуйте архив
tar -xzf instagram-samples-bot.tar.gz
cd instagram-samples-bot

# Установите зависимости
chmod +x install.sh
./install.sh
```

## ⚙️ 2. Настройка (2 минуты)

```bash
# Отредактируйте конфигурацию
nano instagram_samples_bot.py
```

**Заполните:**
- `INSTAGRAM_USERNAME` → ваш логин Instagram
- `INSTAGRAM_PASSWORD` → ваш пароль Instagram  
- `INSTAGRAM_THREAD_ID` → ID чата с сэмплами (число из URL `/t/XXXXX`)
- `TELEGRAM_BOT_TOKEN` → токен от @BotFather
- `TELEGRAM_CHANNEL_ID` → ID канала для публикации (начинается с -100)

## ✅ 3. Тестовый запуск

```bash
source venv/bin/activate
python3 instagram_samples_bot.py
# Ctrl+C для остановки
```

## 🔧 4. Настройка службы

```bash
# Отредактируйте service файл
nano instagram-samples.service
# Замените YOUR_USERNAME на ваше имя пользователя

# Установите службу
sudo cp instagram-samples.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable instagram-samples
sudo systemctl start instagram-samples
```

## 📊 5. Управление

```bash
# Статус
sudo systemctl status instagram-samples

# Перезапуск
sudo systemctl restart instagram-samples

# Логи в реальном времени
sudo journalctl -u instagram-samples -f

# ИЛИ
tail -f samples_bot.log
```

## 🔑 Получение ID канала

```bash
# Способ 1: переслать сообщение из канала боту @userinfobot
# Способ 2: переслать сообщение из канала боту @raw_data_bot
# Способ 3: открыть web.telegram.org, взять ID из URL, добавить -100
```

## 🆘 Быстрое решение проблем

```bash
# Не запускается?
sudo journalctl -u instagram-samples -n 50

# Ошибка Instagram?
rm instagram_session.json
sudo systemctl restart instagram-samples

# Не отправляет в канал?
# Проверьте: бот админ канала? Права на публикацию? ID правильный?

# Высокая нагрузка?
# В instagram_samples_bot.py увеличьте CHECK_INTERVAL = 120
```

## 📁 Быстрый доступ к файлам

```bash
cd ~/instagram-samples-bot
ls -la

# Основные файлы:
# - instagram_samples_bot.py     → код бота
# - samples_bot.log              → логи приложения
# - instagram_session.json       → сессия Instagram
# - state.json                   → обработанные сообщения
```

---

**Всё готово!** Теперь бот автоматически публикует музыкальные сэмплы из Instagram чата в ваш Telegram канал. 🎉
