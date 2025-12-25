#!/bin/bash

# Скрипт установки Instagram Samples to Telegram Bot

echo "🎵 Установка Instagram Samples to Telegram Bot"
echo "=============================================="

# Проверка прав суперпользователя
if [ "$EUID" -eq 0 ]; then 
   echo "❌ Не запускайте этот скрипт от root!"
   echo "   Используйте обычного пользователя"
   exit 1
fi

# Обновление системы
echo ""
echo "📦 Обновление системных пакетов..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv yt-dlp

# Проверка установки yt-dlp
if ! command -v yt-dlp &> /dev/null; then
    echo "⚠️  yt-dlp не установлен через apt, устанавливаем через pip..."
    sudo pip3 install yt-dlp
fi

# Создание виртуального окружения
echo ""
echo "🐍 Создание виртуального окружения Python..."
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
echo ""
echo "📚 Установка Python библиотек..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "1. Отредактируйте файл instagram_samples_bot.py"
echo "2. Укажите ваши данные Instagram и Telegram"
echo "3. Запустите: python3 instagram_samples_bot.py"
echo "4. Для автозапуска настройте systemd службу"
