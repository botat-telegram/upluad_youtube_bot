"""
أداة لتنظيف الملفات المؤقتة والجلسات القديمة
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta

# إضافة المجلد الأساسي إلى مسار Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DOWNLOAD_DIR, LOGS_DIR, APP_LOGS_DIR, SESSIONS_DIR

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cleaner')

def clean_temp_files(days_old=1):
    """تنظيف الملفات المؤقتة الأقدم من عدد محدد من الأيام"""
    if not os.path.exists(DOWNLOAD_DIR):
        logger.warning(f"مجلد التنزيلات غير موجود: {DOWNLOAD_DIR}")
        return
        
    now = time.time()
    count = 0
    size = 0
    
    logger.info(f"بدء تنظيف الملفات المؤقتة القديمة في {DOWNLOAD_DIR}")
    for file in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, file)
        if os.path.isfile(file_path):
            # التحقق من عمر الملف
            file_age = now - os.path.getmtime(file_path)
            if file_age / (24 * 3600) >= days_old:
                file_size = os.path.getsize(file_path)
                try:
                    os.remove(file_path)
                    count += 1
                    size += file_size
                    logger.info(f"تم حذف: {file}")
                except Exception as e:
                    logger.error(f"خطأ في حذف {file}: {str(e)}")
    
    logger.info(f"تم حذف {count} ملف بحجم إجمالي {size/1024/1024:.2f} ميجابايت")
    return count, size

def clean_old_logs(days_old=7):
    """تنظيف ملفات السجل القديمة"""
    if not os.path.exists(APP_LOGS_DIR):
        logger.warning(f"مجلد السجلات غير موجود: {APP_LOGS_DIR}")
        return
        
    now = time.time()
    count = 0
    size = 0
    
    logger.info(f"بدء تنظيف ملفات السجل القديمة في {APP_LOGS_DIR}")
    for file in os.listdir(APP_LOGS_DIR):
        if not file.endswith('.log'):
            continue
            
        file_path = os.path.join(APP_LOGS_DIR, file)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age / (24 * 3600) >= days_old:
                file_size = os.path.getsize(file_path)
                try:
                    os.remove(file_path)
                    count += 1
                    size += file_size
                    logger.info(f"تم حذف: {file}")
                except Exception as e:
                    logger.error(f"خطأ في حذف {file}: {str(e)}")
    
    logger.info(f"تم حذف {count} ملف سجل بحجم إجمالي {size/1024/1024:.2f} ميجابايت")
    return count, size

def main():
    print("أداة تنظيف ملفات البوت")
    print("====================")
    
    # تنظيف الملفات المؤقتة
    print("\n1. تنظيف الملفات المؤقتة...")
    temp_count, temp_size = clean_temp_files(days_old=1)
    
    # تنظيف السجلات القديمة
    print("\n2. تنظيف ملفات السجل القديمة...")
    log_count, log_size = clean_old_logs(days_old=7)
    
    total_count = temp_count + log_count
    total_size = temp_size + log_size
    
    print("\nملخص النتائج:")
    print(f"- تم حذف {temp_count} ملف مؤقت ({temp_size/1024/1024:.2f} ميجابايت)")
    print(f"- تم حذف {log_count} ملف سجل ({log_size/1024/1024:.2f} ميجابايت)")
    print(f"- المجموع: {total_count} ملف ({total_size/1024/1024:.2f} ميجابايت)")
    
    input("\nاضغط Enter للخروج...")

if __name__ == "__main__":
    main()
