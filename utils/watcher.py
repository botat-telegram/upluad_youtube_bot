import os
import sys
import time
import logging
import subprocess
import codecs
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# تكوين التسجيل لدعم Unicode
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(codecs.getwriter('utf-8')(sys.stdout.buffer))
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class BotRestartHandler(FileSystemEventHandler):
    def __init__(self, bot_process):
        self.bot_process = bot_process
        self.last_restart = 0
        self.restart_cooldown = 1  # ثانية واحدة كحد أدنى بين عمليات إعادة التشغيل
        self.watched_extensions = ('.py', '.json', '.env')  # امتدادات الملفات التي سيتم مراقبتها

    def on_modified(self, event):
        if event.is_directory:
            return
            
        file_ext = os.path.splitext(event.src_path)[1].lower()
        if file_ext not in self.watched_extensions:
            return

        current_time = time.time()
        if current_time - self.last_restart < self.restart_cooldown:
            logger.debug(f"تجاهل التغيير (فترة التهدئة): {event.src_path}")
            return

        logger.info(f"تم اكتشاف تغيير في الملف: {event.src_path}")
        self.restart_bot()
        self.last_restart = current_time

    def restart_bot(self):
        try:
            # إيقاف العملية الحالية إذا كانت قيد التشغيل
            if self.bot_process and self.bot_process.poll() is None:
                logger.info("إيقاف عملية البوت الحالية...")
                # محاولة إيقاف العملية بشكل طبيعي أولاً
                self.bot_process.terminate()
                try:
                    # زيادة وقت الانتظار للإيقاف الطبيعي
                    self.bot_process.wait(timeout=20)  # زيادة وقت الانتظار إلى 20 ثانية
                except subprocess.TimeoutExpired:
                    logger.warning("تعذر إيقاف العملية بشكل طبيعي، محاولة إيقاف قوي...")
                    # محاولة إيقاف قوي
                    self.bot_process.kill()
                    try:
                        self.bot_process.wait(timeout=15)  # زيادة وقت الانتظار للإيقاف القوي
                    except subprocess.TimeoutExpired:
                        logger.error("فشل في إيقاف العملية حتى بعد الإيقاف القوي")
                        # محاولة إيقاف العملية باستخدام taskkill في Windows
                        if os.name == 'nt':
                            try:
                                # إيقاف جميع العمليات المرتبطة
                                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.bot_process.pid)], timeout=15)
                                time.sleep(5)  # زيادة وقت الانتظار للتأكد من إغلاق جميع العمليات
                                logger.info("تم إيقاف العملية باستخدام taskkill")
                            except Exception as e:
                                logger.error(f"فشل في إيقاف العملية باستخدام taskkill: {e}")
                                return  # الخروج إذا لم نتمكن من إيقاف العملية

            # التأكد من إزالة ملف القفل
            lock_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.lock')
            max_attempts = 5  # زيادة عدد المحاولات
            attempt = 0
            while os.path.exists(lock_file) and attempt < max_attempts:
                try:
                    # محاولة إغلاق أي مقابض ملفات مفتوحة (Windows فقط)
                    if os.name == 'nt':
                        try:
                            subprocess.run(['handle', '-c', lock_file], timeout=5)
                        except Exception:
                            pass
                    
                    os.remove(lock_file)
                    logger.info("تم إزالة ملف القفل القديم")
                    break
                except Exception as e:
                    attempt += 1
                    logger.warning(f"محاولة {attempt} لإزالة ملف القفل فشلت: {e}")
                    time.sleep(3)  # زيادة وقت الانتظار بين المحاولات
            
            if os.path.exists(lock_file):
                logger.error("فشلت جميع محاولات إزالة ملف القفل")
                return  # الخروج إذا لم نتمكن من إزالة ملف القفل

            # إضافة تأخير قبل إعادة التشغيل
            time.sleep(3)  # انتظار 3 ثواني للتأكد من تحرير جميع الموارد
            
            # إعادة تشغيل البوت
            logger.info("جاري إعادة تشغيل البوت...")
            try:
                self.bot_process = subprocess.Popen([sys.executable, 'run_bot.py'])
                logger.info("✅ تم إعادة تشغيل البوت بنجاح")
                logger.info("تم تفعيل نظام مراقبة الملفات")
            except Exception as e:
                logger.error(f"فشل في إعادة تشغيل البوت: {e}")
                return  # الخروج في حالة فشل إعادة التشغيل
        except Exception as e:
            logger.error(f"فشل في إعادة تشغيل البوت: {str(e)}")
            # محاولة إعادة تشغيل البوت مرة أخرى بعد 5 ثواني
            time.sleep(5)
            try:
                self.bot_process = subprocess.Popen([sys.executable, 'run_bot.py'])
                logger.info("✅ تم إعادة تشغيل البوت بنجاح بعد المحاولة الثانية")
                logger.info("تم تفعيل نظام مراقبة الملفات بعد المحاولة الثانية")
            except Exception as e:
                logger.critical(f"فشل في إعادة تشغيل البوت بعد المحاولة الثانية: {str(e)}")


def start_watcher(bot_process):
    event_handler = BotRestartHandler(bot_process)
    observer = Observer()

    # إضافة المجلدات للمراقبة
    paths_to_watch = ['core', 'utils', 'config']
    for path in paths_to_watch:
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=True)
            logger.info(f"تمت إضافة المجلد {path} للمراقبة")

    observer.start()
    logger.info("بدأ نظام مراقبة الملفات")
    return observer