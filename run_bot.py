"""
برنامج تشغيل البوت مع إدارة الأخطاء والتسجيل
"""
import os
import sys
import time
import logging
import asyncio
import subprocess
import traceback
from datetime import datetime
from utils.watcher import start_watcher

# استيراد مكون Instance واحدة
from core.single_instance import SingleInstance

# استيراد الإعدادات والبوت
from config import (
    TEMP_DOWNLOAD_PATH, 
    LOGS_DIR, 
    APP_LOGS_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    ENABLE_SINGLE_INSTANCE,
    LOCK_FILE_PATH,
    LOCK_TIMEOUT_MINUTES,
    BOT_VERSION,
    BOT_NAME
)

# إنشاء المجلدات المطلوبة إن لم تكن موجودة
os.makedirs(TEMP_DOWNLOAD_PATH, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(APP_LOGS_DIR, exist_ok=True)

# إعداد التسجيل
log_filename = os.path.join(APP_LOGS_DIR, f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def cleanup_temp_files():
    """تنظيف الملفات المؤقتة"""
    try:
        file_count = 0
        for file in os.listdir(TEMP_DOWNLOAD_PATH):
            file_path = os.path.join(TEMP_DOWNLOAD_PATH, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
                file_count += 1
        if file_count > 0:
            logger.info(f"تم تنظيف {file_count} ملف مؤقت")
    except Exception as e:
        logger.error(f"خطأ أثناء تنظيف الملفات المؤقتة: {str(e)}")

def print_banner():
    """عرض رسالة بدء التشغيل"""
    banner = f"""
    ****************************************************
    *                                                  *
    *  {BOT_NAME}                   *
    *  الإصدار: {BOT_VERSION}                                   *
    *                                                  *
    *  تطوير: {os.environ.get('USER') or os.environ.get('USERNAME') or 'Unknown'}          *
    *  التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}             *
    *                                                  *
    ****************************************************
    """
    print(banner)
    logger.info(f"بدء تشغيل {BOT_NAME} - الإصدار {BOT_VERSION}")

def main():
    """دالة التشغيل الرئيسية"""
    # التأكد من أن نسخة واحدة فقط تعمل (إذا كان ذلك مفعلاً)
    single_instance = None
    if ENABLE_SINGLE_INSTANCE:
        try:
            single_instance = SingleInstance(
                lock_file_path=LOCK_FILE_PATH, 
                timeout=LOCK_TIMEOUT_MINUTES
            )
        except SystemExit:
            logger.error("هناك نسخة أخرى من البوت قيد التشغيل بالفعل")
            print("⛔ خطأ: هناك نسخة أخرى من البوت قيد التشغيل بالفعل")
            return 1

    try:
        print_banner()
        
        # تنظيف الملفات المؤقتة من التشغيل السابق
        cleanup_temp_files()
        
        # بدء عملية البوت
        bot_process = subprocess.Popen([sys.executable, 'main.py'])
        logger.info("تم بدء تشغيل البوت عبر main.py")
        
        # بدء نظام مراقبة الملفات
        observer = start_watcher(bot_process)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("تم اكتشاف طلب إيقاف البوت")
            observer.stop()
            if bot_process.poll() is None:
                bot_process.terminate()
                bot_process.wait()

        observer.join()
        logger.info("تم إيقاف البوت بنجاح")
        return 0
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
        print("\n⚠️ تم إيقاف البوت بواسطة المستخدم")
        return 0
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.critical(f"خطأ غير متوقع: {str(e)}\n{error_details}")
        print(f"\n❌ حدث خطأ غير متوقع: {str(e)}")
        print(f"راجع ملف السجل للمزيد من التفاصيل: {log_filename}")
        return 1
        
    finally:
        # تنظيف الملفات المؤقتة قبل الخروج
        cleanup_temp_files()

if __name__ == "__main__":
    sys.exit(main())
