from telethon import TelegramClient
from telethon.sessions import StringSession, MemorySession
import os
import logging
import asyncio
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, USE_MEMORY_SESSION

logger = logging.getLogger(__name__)

class TelegramDownloader:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            # استخدام جلسة مؤقتة في الذاكرة لتجنب مشاكل قاعدة البيانات
            if USE_MEMORY_SESSION:
                self.client = TelegramClient(MemorySession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)
            else:
                # استخدام StringSession لتخزين أكثر كفاءة
                self.client = TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)
            logger.info("تم إنشاء عميل Telethon بنجاح")
        except Exception as e:
            logger.error(f"فشل في إنشاء عميل Telethon: {str(e)}")
            raise

    async def start(self, max_retries=3, retry_delay=5):
        if not self.client:
            self._initialize_client()
        
        for attempt in range(max_retries):
            try:
                if not self.client.is_connected():
                    await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
                    logger.info("تم تشغيل عميل Telethon بنجاح")
                    return True
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"محاولة الاتصال {attempt + 1} فشلت: {str(e)}. إعادة المحاولة بعد {retry_delay} ثوان...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"فشل في بدء عميل Telethon بعد {max_retries} محاولات: {str(e)}")
                    return False

    async def stop(self):
        if self.client and self.client.is_connected():
            try:
                await self.client.disconnect()
                logger.info("تم إيقاف عميل Telethon بنجاح")
            except Exception as e:
                logger.error(f"خطأ عند إيقاف عميل Telethon: {str(e)}")

    async def download_media_from_link(self, channel_username, message_id, download_path, progress_callback=None):
        """تحميل وسائط من رسالة تيليجرام باستخدام اسم المستخدم ورقم الرسالة"""
        try:
            if not await self.start(max_retries=3):
                raise Exception("فشل في الاتصال بـ Telegram بعد عدة محاولات")

            # التحقق من إمكانية الوصول إلى القناة
            try:
                channel = await self.client.get_entity(channel_username)
            except Exception as e:
                raise Exception(f"لا يمكن الوصول إلى القناة {channel_username}. تأكد من أن البوت لديه صلاحيات الوصول للقناة: {str(e)}")

            # محاولة الحصول على الرسالة
            try:
                message = await self.client.get_messages(channel, ids=message_id)
            except Exception as e:
                raise Exception(f"فشل في الحصول على الرسالة: {str(e)}. تأكد من صحة رابط الرسالة وصلاحيات البوت")
            
            if not message:
                raise Exception(f"لم يتم العثور على الرسالة في {channel_username}")
                
            if not message.media:
                raise Exception(f"لا توجد وسائط في الرسالة")

            # تحديد اسم الملف
            file_name = f"{channel_username}_{message_id}.mp4"
            file_path = os.path.join(download_path, file_name)
            
            # تحميل الملف مع callback للتقدم
            downloaded_path = await self.client.download_media(
                message.media,
                file_path,
                progress_callback=progress_callback
            )
            
            return downloaded_path
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الوسائط: {str(e)}")
            raise
