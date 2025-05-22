import os

# إعدادات المسارات الأساسية
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOWNLOAD_DIR = os.path.join(DATA_DIR, 'downloads')
TEMP_DOWNLOAD_PATH = DOWNLOAD_DIR  # للتوافق مع الكود القديم
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
CREDENTIALS_DIR = os.path.join(DATA_DIR, 'credentials')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
APP_LOGS_DIR = os.path.join(LOGS_DIR, 'app_logs')

# إنشاء المجلدات اللازمة
for directory in [DATA_DIR, DOWNLOAD_DIR, SESSIONS_DIR, CREDENTIALS_DIR, LOGS_DIR, APP_LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# إعدادات تيليجرام
TELEGRAM_BOT_TOKEN = '7396649155:AAHDCRQkdoVgavOSJ3G4guxWXzRwG1E5Yvs'
TELEGRAM_API_ID = 9563612
TELEGRAM_API_HASH = 'bb723be5e3d8196761e04d640337ee60'
USE_MEMORY_SESSION = False
SESSION_NAME = os.path.join(SESSIONS_DIR, 'bot_session.session')
TELEGRAM_SESSION_PATH = os.path.join(SESSIONS_DIR, 'telethon.session')  # ملف جلسة Telethon
ADMIN_CHAT_ID = 123456789  # يجب تغيير هذا الرقم إلى معرف المحادثة الخاص بك

# إعدادات يوتيوب
YOUTUBE_CLIENT_SECRETS_FILE = os.path.join(CREDENTIALS_DIR, 'client_secrets.json')
YOUTUBE_TOKEN_PICKLE = os.path.join(CREDENTIALS_DIR, 'youtube_token.pickle')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube']

# إعدادات التحميل
TEMP_DOWNLOAD_PATH = os.path.join(DATA_DIR, 'downloads')  # المسار المؤقت للتحميل
CHUNK_SIZE = 50 * 1024 * 1024  # 50MB chunks for download
MAX_RETRIES = 5
MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB (Telegram Premium)
UPLOAD_CHUNK_SIZE = 256 * 1024 * 1024  # 256MB chunks for YouTube upload
MAX_UPLOAD_RETRIES = 10

# إعدادات السجلات
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(APP_LOGS_DIR, 'bot.log')
LOG_LEVEL = 'INFO'

# إعدادات النظام
ENABLE_SINGLE_INSTANCE = True  # منع تشغيل أكثر من نسخة من البوت
LOCK_FILE_PATH = os.path.join(BASE_DIR, 'bot.lock')
LOCK_TIMEOUT_MINUTES = 10  # مدة اعتبار Lock File قديم (بالدقائق)

# إعدادات الإصدار والمعلومات
BOT_VERSION = '1.0.0'
BOT_NAME = 'Telegram to YouTube Uploader'
BOT_AUTHOR = 'Your Name'
