#!/usr/bin/env python3
"""
Instagram Samples to Telegram Bot
Автоматически пересылает музыкальные сэмплы (reels) из Instagram чата в Telegram канал
"""

import os
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, PleaseWaitFewMinutes
import telegram
import asyncio

# ===== КОНФИГУРАЦИЯ =====
INSTAGRAM_USERNAME = "ваш_логин_инстаграм"
INSTAGRAM_PASSWORD = "ваш_пароль_инстаграм"
INSTAGRAM_THREAD_ID = "340282366841710301281176539621804876514"

TELEGRAM_BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"
TELEGRAM_CHANNEL_ID = "-100XXXXXXXXXX"  # ID канала (должен начинаться с -100)

CHECK_INTERVAL = 60  # Проверка каждые 60 секунд
DOWNLOAD_DIR = "./downloads"
STATE_FILE = "./state.json"
SESSION_FILE = "./instagram_session.json"

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('samples_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InstagramSamplesBot:
    def __init__(self):
        self.ig_client = Client()
        self.ig_client.delay_range = [1, 3]
        self.tg_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.processed_messages = self.load_state()
        self.first_run = len(self.processed_messages) == 0
        
        # Создаём директорию для загрузок
        Path(DOWNLOAD_DIR).mkdir(exist_ok=True)
        
    def load_state(self):
        """Загружает состояние обработанных сообщений"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()
    
    def save_state(self):
        """Сохраняет состояние обработанных сообщений"""
        with open(STATE_FILE, 'w') as f:
            json.dump(list(self.processed_messages), f)
    
    def login_instagram(self):
        """Авторизация в Instagram с сохранением сессии"""
        try:
            if os.path.exists(SESSION_FILE):
                logger.info("Загружаем сохранённую сессию Instagram...")
                self.ig_client.load_settings(SESSION_FILE)
                self.ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                logger.info("✓ Вход через сохранённую сессию выполнен")
            else:
                logger.info("Выполняем первый вход в Instagram...")
                self.ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                self.ig_client.dump_settings(SESSION_FILE)
                logger.info("✓ Первый вход выполнен, сессия сохранена")
            
            return True
            
        except LoginRequired:
            logger.error("Требуется повторная авторизация")
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            return False
            
        except PleaseWaitFewMinutes:
            logger.warning("Instagram просит подождать несколько минут")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка входа в Instagram: {e}")
            return False
    
    def get_new_messages(self):
        """Получает новые сообщения из Instagram чата"""
        try:
            result = self.ig_client.private_request(
                f"direct_v2/threads/{INSTAGRAM_THREAD_ID}/",
                params={
                    "visual_message_return_type": "unseen",
                    "direction": "older",
                    "seq_id": "40065",
                    "limit": "20"
                }
            )
            
            if 'thread' not in result or 'items' not in result['thread']:
                return []
            
            messages_data = result['thread']['items']
            new_messages = []
            
            for msg_data in messages_data:
                msg_id = msg_data.get('item_id')
                
                if msg_id and msg_id not in self.processed_messages:
                    class SimpleMessage:
                        def __init__(self, data):
                            self.id = data.get('item_id')
                            self.user_id = data.get('user_id')
                            self.text = data.get('text', '')
                            self.item_type = data.get('item_type')
                            
                            # Проверяем clip
                            self.clip = None
                            if 'clip' in data and data['clip']:
                                clip_data = data['clip']['clip']
                                self.clip = type('obj', (object,), {
                                    'id': clip_data.get('id', '').split('_')[0] if clip_data.get('id') else None
                                })()
                            
                            # Проверяем media_share
                            self.media_share = None
                            if 'media_share' in data and data['media_share']:
                                media = data['media_share']
                                self.media_share = type('obj', (object,), {
                                    'id': media.get('id', '').split('_')[0] if media.get('id') else None,
                                    'media_type': media.get('media_type'),
                                    'product_type': media.get('product_type'),
                                    'caption_text': media.get('caption', {}).get('text', '') if media.get('caption') else ''
                                })()
                    
                    new_messages.append(SimpleMessage(msg_data))
            
            return new_messages
            
        except Exception as e:
            logger.error(f"Ошибка получения сообщений: {e}")
            return []
    
    def download_sample_direct(self, media_id, output_path):
        """Скачивает сэмпл напрямую через API Instagram"""
        try:
            logger.info(f"Скачиваем сэмпл через API...")
            
            if '_' in str(media_id):
                media_pk = str(media_id).split('_')[0]
            else:
                media_pk = str(media_id)
            
            result = self.ig_client.private_request(f"media/{media_pk}/info/")
            
            if 'items' not in result or len(result['items']) == 0:
                logger.warning(f"Медиа не найдено: {media_pk}")
                return None
            
            media_data = result['items'][0]
            video_url = None
            
            if 'video_versions' in media_data and len(media_data['video_versions']) > 0:
                video_url = media_data['video_versions'][0]['url']
            
            if not video_url:
                logger.warning(f"URL видео не найден для {media_pk}")
                return None
            
            logger.info(f"Найден video URL, скачиваем...")
            
            import requests
            cookies = {cookie.name: cookie.value for cookie in self.ig_client.private.cookies}
            headers = {
                'User-Agent': self.ig_client.private.headers.get('User-Agent', 'Instagram 269.0.0.18.75 Android'),
            }
            
            response = requests.get(video_url, headers=headers, cookies=cookies, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if os.path.exists(output_path):
                logger.info(f"✓ Сэмпл скачан: {output_path}")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка прямого скачивания: {e}")
            return None
    
    def download_sample_ytdlp(self, media_id, output_path):
        """Скачивает сэмпл через yt-dlp"""
        try:
            if '_' in str(media_id):
                media_pk = str(media_id).split('_')[0]
            else:
                media_pk = str(media_id)
            
            code = self.ig_client.media_code_from_pk(int(media_pk))
            reel_url = f"https://www.instagram.com/reel/{code}/"
            
            logger.info(f"Скачиваем через yt-dlp: {reel_url}")
            
            cookies_file = f"{DOWNLOAD_DIR}/cookies.txt"
            with open(cookies_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n\n")
                for cookie in self.ig_client.private.cookies:
                    domain = cookie.domain if cookie.domain else '.instagram.com'
                    flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path = cookie.path if cookie.path else '/'
                    secure = 'TRUE' if cookie.secure else 'FALSE'
                    expiration = str(int(cookie.expires)) if cookie.expires else '0'
                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{cookie.name}\t{cookie.value}\n")
            
            cmd = [
                'yt-dlp',
                '--quiet',
                '--no-warnings',
                '--cookies', cookies_file,
                '-f', 'best',
                '-o', output_path,
                reel_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            try:
                os.remove(cookies_file)
            except:
                pass
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✓ Сэмпл скачан через yt-dlp: {output_path}")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка yt-dlp: {e}")
            return None
    
    def download_sample(self, media_id):
        """Скачивает сэмпл (пробует оба метода)"""
        output_path = f"{DOWNLOAD_DIR}/{media_id}.mp4"
        
        # Метод 1: Прямое скачивание через API
        result = self.download_sample_direct(media_id, output_path)
        if result:
            return result
        
        # Метод 2: Через yt-dlp
        logger.info("Прямое скачивание не удалось, пробуем yt-dlp...")
        result = self.download_sample_ytdlp(media_id, output_path)
        if result:
            return result
        
        logger.error(f"Не удалось скачать сэмпл {media_id}")
        return None
    
    async def send_to_channel_async(self, video_path, caption=""):
        """Отправляет сэмпл в канал Telegram (асинхронная версия)"""
        try:
            with open(video_path, 'rb') as video:
                await self.tg_bot.send_video(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    video=video,
                    caption=caption,
                    supports_streaming=True,
                    read_timeout=60,
                    write_timeout=60
                )
            logger.info(f"✓ Сэмпл опубликован в канале")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")
            return False
    
    def send_to_channel(self, video_path, caption=""):
        """Отправляет сэмпл в канал Telegram (синхронная обёртка)"""
        try:
            # Проверяем размер файла (Telegram лимит 50MB)
            file_size = os.path.getsize(video_path)
            if file_size > 50 * 1024 * 1024:
                logger.warning(f"Файл слишком большой ({file_size / 1024 / 1024:.2f} MB)")
                return False
            
            # Получаем или создаём event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Запускаем асинхронную отправку
            return loop.run_until_complete(self.send_to_channel_async(video_path, caption))
            
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False
    
    def get_sender_name(self, sender_id):
        """Получает имя отправителя"""
        try:
            user_info = self.ig_client.user_info(sender_id)
            return user_info.username
        except:
            return "Unknown"
    
    def process_message(self, message):
        """Обрабатывает одно сообщение"""
        try:
            msg_id = message.id
            sender = message.user_id
            sender_name = self.get_sender_name(sender)
            
            logger.info(f"🎵 Обрабатываем сообщение от @{sender_name}")
            
            media_id = None
            caption_text = ""
            
            if message.clip:
                media_id = message.clip.id
                caption_text = message.text or ""
                logger.info(f"Найден сэмпл (clip): {media_id}")
                
            elif message.media_share:
                media = message.media_share
                if media.media_type == 2 and media.product_type == "clips":
                    media_id = media.id
                    caption_text = media.caption_text or ""
                    logger.info(f"Найден сэмпл (media_share): {media_id}")
            
            if media_id:
                video_path = self.download_sample(media_id)
                
                if video_path and os.path.exists(video_path):
                    # Формируем подпись для канала
                    caption = f"🎵 от @{sender_name}"
                    if caption_text:
                        caption += f"\n\n{caption_text[:300]}"
                    
                    # Публикуем в канале
                    if self.send_to_channel(video_path, caption):
                        try:
                            os.remove(video_path)
                        except:
                            pass
                        
                        self.processed_messages.add(msg_id)
                        self.save_state()
                        return True
            else:
                logger.info(f"Сообщение не содержит сэмпл, пропускаем")
            
            self.processed_messages.add(msg_id)
            self.save_state()
            return False
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            self.processed_messages.add(message.id)
            self.save_state()
            return False
    
    def run(self):
        """Основной цикл работы бота"""
        logger.info("=" * 60)
        logger.info("🎵 Instagram Samples to Telegram Bot запущен!")
        logger.info(f"📱 Instagram чат: {INSTAGRAM_THREAD_ID}")
        logger.info(f"📢 Telegram канал: {TELEGRAM_CHANNEL_ID}")
        logger.info(f"⏱️  Интервал проверки: {CHECK_INTERVAL} сек")
        logger.info("=" * 60)
        
        # Авторизация в Instagram
        if not self.login_instagram():
            logger.error("❌ Не удалось войти в Instagram")
            return
        
        # При первом запуске помечаем все существующие сообщения
        if self.first_run:
            logger.info("🔄 Первый запуск: помечаем существующие сообщения...")
            try:
                result = self.ig_client.private_request(
                    f"direct_v2/threads/{INSTAGRAM_THREAD_ID}/",
                    params={"limit": "100"}
                )
                
                if 'thread' in result and 'items' in result['thread']:
                    for msg in result['thread']['items']:
                        if 'item_id' in msg:
                            self.processed_messages.add(msg['item_id'])
                    
                    self.save_state()
                    logger.info(f"✓ Помечено {len(self.processed_messages)} сообщений")
            except Exception as e:
                logger.error(f"Ошибка инициализации: {e}")
            
            self.first_run = False
        
        consecutive_errors = 0
        max_errors = 5
        
        logger.info("👀 Начинаем мониторинг новых сэмплов...\n")
        
        while True:
            try:
                new_messages = self.get_new_messages()
                
                if new_messages:
                    logger.info(f"📬 Найдено новых сообщений: {len(new_messages)}")
                    
                    for message in reversed(new_messages):
                        self.process_message(message)
                        time.sleep(3)
                
                consecutive_errors = 0
                
            except LoginRequired:
                logger.warning("⚠️  Требуется повторная авторизация")
                if not self.login_instagram():
                    consecutive_errors += 1
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в основном цикле: {e}")
                consecutive_errors += 1
            
            if consecutive_errors >= max_errors:
                logger.error(f"💀 Слишком много ошибок ({max_errors}). Остановка.")
                break
            
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        bot = InstagramSamplesBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\n\n⛔ Остановка бота (Ctrl+C)")
    except Exception as e:
        logger.error(f"💀 Критическая ошибка: {e}")
