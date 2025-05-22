from telethon import TelegramClient
from telethon.sessions import StringSession, MemorySession
import os
import logging
import asyncio
import re
from config.config import (
    TELEGRAM_API_ID, 
    TELEGRAM_API_HASH, 
    TELEGRAM_BOT_TOKEN, 
    USE_MEMORY_SESSION, 
    TEMP_DOWNLOAD_PATH
)

logger = logging.getLogger(__name__)

class TelegramDownloader:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            # استخدام جلسة مؤقتة في الذاكرة لتجنب مشاكل قاعدة البيانات
            if USE_MEMORY_SESSION:
                logger.info("استخدام جلسة في الذاكرة لـ Telethon")
                self.client = TelegramClient(MemorySession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)
            else:
                # استخدام StringSession لتخزين أكثر كفاءة
                logger.info("استخدام جلسة StringSession لـ Telethon")
                self.client = TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)
            logger.info("تم إنشاء عميل Telethon بنجاح")
        except Exception as e:
            logger.error(f"فشل في إنشاء عميل Telethon: {str(e)}")
            raise

    async def start(self):
        if not self.client:
            self._initialize_client()
        
        if not self.client.is_connected():
            try:
                logger.info("جاري بدء اتصال عميل Telethon")
                await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
                logger.info("تم تشغيل عميل Telethon بنجاح")
                return True
            except Exception as e:
                logger.error(f"فشل في بدء عميل Telethon: {str(e)}")
                return False
        return True

    async def stop(self):
        if self.client and self.client.is_connected():
            try:
                logger.info("جاري إيقاف عميل Telethon")
                await self.client.disconnect()
                logger.info("تم إيقاف عميل Telethon بنجاح")
            except Exception as e:
                logger.error(f"خطأ عند إيقاف عميل Telethon: {str(e)}")

    async def download_media_from_link(self, channel_username, message_id, progress_callback=None):
        """تحميل وسائط من رسالة تيليجرام باستخدام اسم المستخدم ورقم الرسالة"""
        try:
            if not await self.start():
                raise Exception("فشل في الاتصال بـ Telegram")

            # محاولة الحصول على الرسالة
            logger.info(f"جاري الحصول على رسالة من {channel_username} برقم {message_id}")
            message = await self.client.get_messages(channel_username, ids=message_id)
            
            if not message:
                logger.error(f"لم يتم العثور على الرسالة في {channel_username}")
                raise Exception(f"لم يتم العثور على الرسالة في {channel_username}")
                
            if not message.media:
                logger.error(f"لا توجد وسائط في الرسالة من {channel_username}")
                raise Exception(f"لا توجد وسائط في الرسالة")

            # تحديد اسم الملف
            file_name = f"{channel_username}_{message_id}.mp4"
            file_path = os.path.join(TEMP_DOWNLOAD_PATH, file_name)
            
            # تحميل الملف مع callback للتقدم
            logger.info(f"بدء تحميل الوسائط إلى {file_path}")
            downloaded_path = await self.client.download_media(
                message.media,
                file_path,
                progress_callback=progress_callback
            )
            
            if downloaded_path:
                logger.info(f"تم تحميل الوسائط بنجاح إلى {downloaded_path}")
                return downloaded_path
            else:
                logger.error("فشل تحميل الوسائط")
                return None
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الوسائط: {str(e)}")
            raise
            
    async def parse_telegram_link(self, link):
        """تحليل رابط تيليجرام وتحديد ما إذا كان يشير إلى مجموعة خاصة أو قناة عامة"""
        try:
            # تحقق من نوع الرابط (مجموعة خاصة أم قناة عامة)
            private_match = re.match(r'https?://(?:t|telegram)\.(?:me|dog)/c/(\d+)/(\d+)(?:/(\d+))?', link)
            public_match = re.match(r'https?://(?:t|telegram)\.(?:me|dog)/([^/]+)/(\d+)', link)
            
            if private_match:
                # رابط مجموعة خاصة
                chat_id = int(private_match.group(1))
                message_id = int(private_match.group(2))
                sub_message_id = int(private_match.group(3)) if private_match.group(3) else None
                
                return {
                    'type': 'private',
                    'chat_id': chat_id,
                    'message_id': message_id,
                    'sub_message_id': sub_message_id
                }
            elif public_match:
                # رابط قناة عامة
                channel_username = public_match.group(1)
                message_id = int(public_match.group(2))
                
                return {
                    'type': 'public',
                    'channel_username': channel_username,
                    'message_id': message_id
                }
            else:
                logger.error("صيغة الرابط غير معروفة")
                return None
        except Exception as e:
            logger.error(f"خطأ في تحليل الرابط: {str(e)}")
            return None
            
    async def download_media_from_private_chat(self, chat_id, message_id, sub_message_id=None, progress_callback=None):
        """تحميل وسائط من مجموعة خاصة في تيليجرام"""
        try:
            if not await self.start():
                raise Exception("فشل في الاتصال بـ Telegram")

            # محاولة مختلف صيغ معرفات المجموعات الخاصة
            target_message_id = sub_message_id if sub_message_id else message_id
            message = None
            entity_obtained = False
            
            # قائمة بصيغ معرفات المجموعات الخاصة المختلفة للتجربة
            chat_id_formats = [
                -100 + int(chat_id),             # الصيغة القياسية 1
                -(100 + int(chat_id)),           # الصيغة القياسية 2
                -1000000000000 - int(chat_id),   # صيغة بديلة 1
                -100000000 - int(chat_id)        # صيغة بديلة 2
            ]
            
            # تجربة كل صيغة حتى نجد واحدة تعمل
            for full_chat_id in chat_id_formats:
                try:
                    logger.info(f"محاولة الوصول للمجموعة الخاصة باستخدام المعرف: {full_chat_id}")
                    entity = await self.client.get_entity(full_chat_id)
                    logger.info(f"تم الوصول إلى المجموعة/القناة: {getattr(entity, 'title', 'مجموعة خاصة')}")
                    
                    # محاولة الحصول على الرسالة
                    message = await self.client.get_messages(full_chat_id, ids=target_message_id)
                    if message:
                        entity_obtained = True
                        break
                except Exception as e:
                    logger.warning(f"فشلت المحاولة باستخدام {full_chat_id}: {str(e)}")
                    continue
            
            if not entity_obtained or not message:
                logger.error(f"لم يتم العثور على المجموعة الخاصة أو الرسالة")
                raise Exception("فشل في الوصول للمجموعة الخاصة أو الرسالة. تأكد من أن البوت عضو في المجموعة.")
                
            if not message.media:
                logger.error(f"لا توجد وسائط في الرسالة من المجموعة الخاصة")
                raise Exception(f"لا توجد وسائط في الرسالة")

            # تحديد اسم الملف
            file_name = f"private_{chat_id}_{target_message_id}.mp4"
            file_path = os.path.join(TEMP_DOWNLOAD_PATH, file_name)
            
            # تحميل الملف مع callback للتقدم
            logger.info(f"بدء تحميل الوسائط إلى {file_path}")
            downloaded_path = await self.client.download_media(
                message.media,
                file_path,
                progress_callback=progress_callback
            )
            
            if downloaded_path:
                logger.info(f"تم تحميل الوسائط بنجاح إلى {downloaded_path}")
                return downloaded_path
            else:
                logger.error("فشل تحميل الوسائط")
                return None
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الوسائط من المجموعة الخاصة: {str(e)}")
            raise
            
    async def download_from_any_link(self, link, progress_callback=None):
        """تحميل وسائط من أي رابط تيليجرام (عام أو خاص)"""
        try:
            # تحليل الرابط
            link_info = await self.parse_telegram_link(link)
            
            if not link_info:
                raise Exception("صيغة الرابط غير صالحة")
                
            if link_info['type'] == 'public':
                # رابط عام
                return await self.download_media_from_link(
                    link_info['channel_username'], 
                    link_info['message_id'],
                    progress_callback
                )
            else:
                # رابط مجموعة خاصة
                return await self.download_media_from_private_chat(
                    link_info['chat_id'],
                    link_info['message_id'],
                    link_info['sub_message_id'],
                    progress_callback
                )
                
        except Exception as e:
            logger.error(f"خطأ في تحميل الوسائط من الرابط: {str(e)}")
            raise
