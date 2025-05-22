import os
import sys
import shutil
from pathlib import Path
import logging

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# المسار الحالي للمشروع
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# قيم افتراضية (لاستخدامها إذا لم يكن ملف config.py موجوداً)
DATA_DIR = os.path.join(BASE_DIR, 'data')
YOUTUBE_TOKEN_PICKLE = os.path.join(DATA_DIR, 'credentials', 'youtube_token.pickle')
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
CREDENTIALS_DIR = os.path.join(DATA_DIR, 'credentials')

# محاولة استيراد القيم من config.py إن وجد
try:
    sys.path.insert(0, BASE_DIR)
    from config import YOUTUBE_TOKEN_PICKLE, SESSIONS_DIR, CREDENTIALS_DIR
    print("✓ تم استيراد الإعدادات من config.py بنجاح")
except ImportError:
    print("! لم يتم العثور على ملف config.py، سيتم استخدام القيم الافتراضية")
    # إنشاء المجلدات اللازمة
    for directory in [DATA_DIR, os.path.join(DATA_DIR, 'downloads'), SESSIONS_DIR, CREDENTIALS_DIR]:
        os.makedirs(directory, exist_ok=True)

def print_colored(message, color="white"):
    """طباعة رسالة ملونة"""
    colors = {
        "white": "\033[0m",
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m"
    }
    print(f"{colors.get(color, colors['white'])}{message}{colors['white']}")

def reset_youtube_token():
    """إعادة تعيين توكن يوتيوب"""
    try:
        # استيراد SessionManager هنا لتجنب الاستيراد الدائري
        from utils.session_manager import SessionManager
        logger.info("جاري إعادة تعيين توكن يوتيوب...")
        
        if os.path.exists(YOUTUBE_TOKEN_PICKLE):
            try:
                os.remove(YOUTUBE_TOKEN_PICKLE)
                print_colored(f"✓ تم حذف توكن يوتيوب: {YOUTUBE_TOKEN_PICKLE}", "green")
                logger.info(f"تم حذف توكن يوتيوب: {YOUTUBE_TOKEN_PICKLE}")
                return True
            except Exception as e:
                print_colored(f"✗ فشل حذف توكن يوتيوب: {str(e)}", "red")
                logger.error(f"فشل حذف توكن يوتيوب: {str(e)}")
                # محاولة النسخ الاحتياطي إذا فشل الحذف
                try:
                    backup_path = f"{YOUTUBE_TOKEN_PICKLE}.bak"
                    shutil.move(YOUTUBE_TOKEN_PICKLE, backup_path)
                    print_colored(f"✓ تم نقل التوكن القديم إلى: {backup_path}", "green")
                    logger.info(f"تم نقل التوكن القديم إلى: {backup_path}")
                    return True
                except Exception as e2:
                    print_colored(f"✗ فشل نقل التوكن القديم: {str(e2)}", "red")
                    logger.error(f"فشل نقل التوكن القديم: {str(e2)}")
                    return False
        else:
            print_colored(f"! توكن يوتيوب غير موجود بالفعل: {YOUTUBE_TOKEN_PICKLE}", "yellow")
            logger.info(f"توكن يوتيوب غير موجود بالفعل: {YOUTUBE_TOKEN_PICKLE}")
            return True
    except Exception as e:
        print_colored(f"✗ خطأ غير متوقع: {str(e)}", "red")
        logger.error(f"خطأ غير متوقع: {str(e)}")
        return False

def reset_telegram_sessions():
    """إعادة تعيين جلسات تيليجرام"""
    try:
        # استيراد SessionManager هنا لتجنب الاستيراد الدائري
        from utils.session_manager import SessionManager
        logger.info("جاري إعادة تعيين جلسات تيليجرام...")
        
        # التحقق من وجود جلسة تيليجرام باستخدام SessionManager
        telegram_session_exists = SessionManager.check_telegram_session()
        
        if os.path.exists(SESSIONS_DIR):
            deleted_count = 0
            failed_count = 0
            
            # البحث عن ملفات الجلسة
            for item in os.listdir(SESSIONS_DIR):
                file_path = os.path.join(SESSIONS_DIR, item)
                if os.path.isfile(file_path) and (item.endswith('.session') or item.endswith('.session-journal')):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        print_colored(f"✓ تم حذف جلسة تيليجرام: {item}", "green")
                        logger.info(f"تم حذف جلسة تيليجرام: {item}")
                    except Exception as e:
                        failed_count += 1
                        print_colored(f"✗ فشل حذف الجلسة {item}: {str(e)}", "red")
                        logger.error(f"فشل حذف الجلسة {item}: {str(e)}")
            
            if deleted_count == 0 and failed_count == 0:
                print_colored("! لم يتم العثور على جلسات تيليجرام", "yellow")
                logger.info("لم يتم العثور على جلسات تيليجرام")
            
            return failed_count == 0
        else:
            print_colored(f"! مجلد جلسات تيليجرام غير موجود: {SESSIONS_DIR}", "yellow")
            logger.info(f"مجلد جلسات تيليجرام غير موجود: {SESSIONS_DIR}")
            os.makedirs(SESSIONS_DIR, exist_ok=True)
            print_colored(f"✓ تم إنشاء مجلد جلسات تيليجرام", "green")
            logger.info(f"تم إنشاء مجلد جلسات تيليجرام")
            return True
    except Exception as e:
        print_colored(f"✗ خطأ غير متوقع: {str(e)}", "red")
        logger.error(f"خطأ غير متوقع: {str(e)}")
        return False

def main():
    print_colored("=" * 60, "blue")
    print_colored("     إعادة تعيين توكنات المصادقة     ", "blue")
    print_colored("=" * 60, "blue")
    
    youtube_reset = reset_youtube_token()
    telegram_reset = reset_telegram_sessions()
    
    print_colored("\n" + "=" * 20 + " ملخص النتائج " + "=" * 20, "blue")
    print_colored(f"إعادة تعيين توكن يوتيوب: {'✓' if youtube_reset else '✗'}", "green" if youtube_reset else "red")
    print_colored(f"إعادة تعيين جلسات تيليجرام: {'✓' if telegram_reset else '✗'}", "green" if telegram_reset else "red")
    
    if youtube_reset and telegram_reset:
        print_colored("\n✓ تم إعادة تعيين جميع التوكنات بنجاح", "green")
        print_colored("🔄 عند تشغيل البوت في المرة القادمة سيطلب إعادة المصادقة", "cyan")
    else:
        print_colored("\n! حدثت بعض المشاكل أثناء إعادة تعيين التوكنات", "yellow")
        print_colored("قد تحتاج لحذف الملفات يدوياً:", "yellow")
        print_colored(f"- توكن يوتيوب: {YOUTUBE_TOKEN_PICKLE}", "yellow")
        print_colored(f"- جلسات تيليجرام: {SESSIONS_DIR}/*.session", "yellow")
        
    print_colored("\nلإنشاء ملف config.py، قم بتنفيذ:", "cyan")
    print_colored("  python create_config.py", "cyan")

if __name__ == "__main__":
    main()
    print_colored("\nاضغط Enter للخروج...", "blue")
    input()
