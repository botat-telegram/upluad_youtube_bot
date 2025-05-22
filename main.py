import os
import logging
import asyncio
import traceback
from config.config import TEMP_DOWNLOAD_PATH, LOGS_DIR, DATA_DIR, SESSIONS_DIR, CREDENTIALS_DIR
from core.telegram_bot import UploadBot
from utils.session_manager import SessionManager

# إنشاء المجلدات المطلوبة
os.makedirs(TEMP_DOWNLOAD_PATH, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# تهيئة مدير الجلسات
SessionManager.initialize()

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "bot_log.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def print_startup_instructions():
    """طباعة تعليمات بدء التشغيل"""
    print("\n" + "=" * 70)
    print("🚀 تم تشغيل البوت بنجاح!")
    print("📱 يرجى اتباع الخطوات التالية في تطبيق تيليجرام:")
    print("  1. افتح البوت وأرسل الأمر /start")
    print("  2. استخدم الأمر /setadmin لتعيين نفسك كمسؤول (كلمة المرور: upluad-youtube-1234)")
    print("  3. استخدم الأمر /auth لبدء عملية المصادقة مع يوتيوب")
    print("  4. اتبع التعليمات التي ستظهر في البوت")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        logger.info("بدء تشغيل البوت...")
        bot = UploadBot()  # إنشاء البوت بدون تهيئة اتصال يوتيوب
        print_startup_instructions()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم.")
    except Exception as e:
        logger.critical(f"حدث خطأ غير متوقع: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"خطأ: {str(e)}")
