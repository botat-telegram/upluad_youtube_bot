import os
import pickle
import logging
import time
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config.config import (
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_TOKEN_PICKLE,
    SCOPES,
    TELEGRAM_SESSION_PATH,
    TELEGRAM_BOT_TOKEN,
    DATA_DIR
)
import asyncio
from telegram import Bot

logger = logging.getLogger(__name__)

# ملف حفظ إعدادات المسؤول
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, 'admin_config.json')

class SessionManager:
    _last_token_check = 0
    _token_check_interval = 1800  # 30 دقيقة
    _token_refresh_threshold = 300  # 5 دقائق قبل انتهاء الصلاحية
    _waiting_for_code = False
    _auth_code = None
    _admin_chat_id = None
    _admin_password = "upluad-youtube-1234"  # كلمة المرور الافتراضية
    
    # تحميل الإعدادات عند استيراد الكلاس
    @staticmethod
    def initialize():
        """تهيئة إعدادات المسؤول"""
        SessionManager._load_admin_config()

    @staticmethod
    def _load_admin_config():
        """تحميل إعدادات المسؤول من الملف"""
        if os.path.exists(ADMIN_CONFIG_FILE):
            try:
                with open(ADMIN_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    SessionManager._admin_chat_id = config.get('admin_chat_id')
                    if 'admin_password' in config:
                        SessionManager._admin_password = config['admin_password']
                    logger.info(f"تم تحميل إعدادات المسؤول: معرف المحادثة = {SessionManager._admin_chat_id}")
                    return True
            except Exception as e:
                logger.error(f"خطأ في تحميل إعدادات المسؤول: {str(e)}")
        return False

    @staticmethod
    def _save_admin_config():
        """حفظ إعدادات المسؤول في الملف"""
        try:
            os.makedirs(os.path.dirname(ADMIN_CONFIG_FILE), exist_ok=True)
            config = {
                'admin_chat_id': SessionManager._admin_chat_id,
                'admin_password': SessionManager._admin_password
            }
            with open(ADMIN_CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            logger.info(f"تم حفظ إعدادات المسؤول: معرف المحادثة = {SessionManager._admin_chat_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ إعدادات المسؤول: {str(e)}")
            return False

    @staticmethod
    def set_admin_chat_id(chat_id):
        """تعيين معرف المحادثة الإدارية"""
        SessionManager._admin_chat_id = chat_id
        SessionManager._save_admin_config()
        logger.info(f"تم تعيين معرف المحادثة الإدارية: {chat_id}")

    @staticmethod
    def get_admin_chat_id():
        """الحصول على معرف المحادثة الإدارية"""
        if SessionManager._admin_chat_id is None:
            SessionManager._load_admin_config()
        return SessionManager._admin_chat_id

    @staticmethod
    def check_admin_password(password):
        """التحقق من كلمة مرور المسؤول"""
        if SessionManager._admin_password is None:
            SessionManager._load_admin_config()
        return password == SessionManager._admin_password

    @staticmethod
    async def receive_auth_code(message_text, chat_id):
        """استلام رمز المصادقة من رسالة"""
        admin_chat_id = SessionManager.get_admin_chat_id()
        if SessionManager._waiting_for_code and admin_chat_id == chat_id:
            # تنظيف الرمز
            code = message_text.strip()
            
            # محاولة استخراج الرمز من النص بتنسيقات مختلفة
            # الكثير من رموز جوجل تبدأ بـ 4/ أو 4%2F
            if "4/" in code or "4%2F" in code:
                # استخراج الجزء الذي يحتوي على الرمز
                import re
                match = re.search(r'(4/[a-zA-Z0-9_\-]+)', code)
                if match:
                    code = match.group(1)
                else:
                    match = re.search(r'(4%2F[a-zA-Z0-9_\-]+)', code)
                    if match:
                        # تحويل 4%2F إلى 4/
                        code = match.group(1).replace("%2F", "/")
            
            # إزالة أي اقتباسات إذا وجدت
            if code.startswith('"') and code.endswith('"'):
                code = code[1:-1]
            
            # إذا كان الرمز يحتوي على كلمات إضافية، نحاول استخراج الرمز فقط
            if len(code.split()) > 1 and not code.startswith("4/"):
                parts = code.split()
                for part in parts:
                    if part.startswith("4/"):
                        code = part
                        break
            
            # إزالة المساحات غير المرئية والأحرف الخاصة
            code = ''.join(c for c in code if c.isprintable() and not c.isspace())
            
            # التعامل مع الرموز التي قد تكون تمت قراءتها بشكل خاطئ
            # مثل الحرف 'l' بدلاً من الرقم '1' أو حرف 'O' بدلاً من الرقم '0'
            # لا نقوم بذلك إلا إذا كان الرمز لا يبدأ بـ "4/"
            if not code.startswith("4/") and "4" in code:
                # محاولة إعادة بناء الرمز
                parts = code.split("4")
                if len(parts) > 1:
                    # إذا وجدنا جزء يبدأ بـ '4' ويحتوي على '/'
                    for i in range(1, len(parts)):
                        if "/" in parts[i]:
                            reconstructed = "4" + parts[i]
                            logger.info(f"محاولة إعادة بناء الرمز: {reconstructed[:10]}...")
                            code = reconstructed
                            break
            
            # تسجيل معلومات الرمز للتشخيص
            logger.info(f"تم استلام رمز المصادقة: {code[:10]}... (الطول: {len(code)})")
            
            # حفظ الرمز
            SessionManager._auth_code = code
            SessionManager._waiting_for_code = False
            
            # إعلام المستخدم
            try:
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                await bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"✅ تم استلام رمز المصادقة وجاري التحقق...\nطول الرمز: {len(code)} حرف"
                )
            except Exception as e:
                logger.error(f"خطأ في إرسال رسالة تأكيد استلام الرمز: {str(e)}")
            
            return True
        return False

    @staticmethod
    async def check_youtube_auth():
        """
        التحقق من صلاحية جلسة يوتيوب وتجديدها إذا لزم الأمر
        """
        current_time = time.time()
        
        # التحقق من صلاحية التوكن بشكل دوري
        if current_time - SessionManager._last_token_check < SessionManager._token_check_interval:
            try:
                creds = SessionManager._load_credentials()
                if creds and creds.valid:
                    return creds
            except:
                pass

        SessionManager._last_token_check = current_time
        creds = None
        
        try:
            # محاولة تحميل التوكن الموجود
            creds = SessionManager._load_credentials()
            
            if creds:
                # التحقق من صلاحية التوكن
                if creds.valid:
                    # التحقق من وقت انتهاء الصلاحية
                    if creds.expiry and (creds.expiry.timestamp() - current_time) < SessionManager._token_refresh_threshold:
                        logger.info("تجديد التوكن قبل انتهاء الصلاحية")
                        try:
                            creds.refresh(Request())
                            SessionManager._save_credentials(creds)
                            logger.info("تم تجديد التوكن بنجاح")
                        except Exception as e:
                            logger.error(f"فشل تجديد التوكن: {str(e)}")
                            creds = None
                    return creds
                elif creds.expired and creds.refresh_token:
                    logger.info("تجديد التوكن منتهي الصلاحية")
                    try:
                        creds.refresh(Request())
                        SessionManager._save_credentials(creds)
                        logger.info("تم تجديد التوكن بنجاح")
                        return creds
                    except Exception as e:
                        logger.error(f"فشل تجديد التوكن: {str(e)}")
                        creds = None

            # إذا لم يكن هناك توكن صالح ومعرف المحادثة الإدارية غير محدد
            if not creds:
                admin_chat_id = SessionManager.get_admin_chat_id()
                
                # عرض رابط المصادقة في التيرمنال كخيار احتياطي
                if admin_chat_id is None:
                    logger.info("معرف المحادثة الإدارية غير محدد، سيتم استخدام طريقة المصادقة عبر التيرمنال")
                    return await SessionManager._terminal_auth()
                    
                # إنشاء توكن جديد عبر البوت
                logger.info("إنشاء توكن جديد عبر البوت")
                flow = InstalledAppFlow.from_client_secrets_file(
                    YOUTUBE_CLIENT_SECRETS_FILE, 
                    SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # استخدام OOB (Out-of-Band) للمصادقة
                )
                
                # إرسال رابط المصادقة عبر البوت
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                auth_url = flow.authorization_url()[0]
                await bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"🔐 يرجى النقر على الرابط التالي للمصادقة مع يوتيوب:\n{auth_url}\n\nبعد المصادقة، سيتم عرض رمز تحقق على الشاشة. يرجى نسخ هذا الرمز وإرساله هنا."
                )
                
                # انتظار الرد من المستخدم عبر البوت
                SessionManager._waiting_for_code = True
                SessionManager._auth_code = None
                
                # انتظار استلام الرمز
                timeout_seconds = 300  # 5 دقائق
                start_time = time.time()
                while SessionManager._waiting_for_code:
                    if time.time() - start_time > timeout_seconds:
                        logger.error("انتهت مهلة انتظار رمز المصادقة")
                        await bot.send_message(
                            chat_id=admin_chat_id,
                            text="⚠️ انتهت مهلة انتظار رمز المصادقة. يرجى إعادة المحاولة."
                        )
                        raise Exception("انتهت مهلة انتظار رمز المصادقة")
                    
                    # انتظار قصير
                    await asyncio.sleep(1)
                
                # إذا استلمنا الرمز
                if SessionManager._auth_code:
                    try:
                        # تنظيف الرمز مرة أخرى للتأكد
                        clean_code = SessionManager._auth_code.strip()
                        logger.info(f"محاولة استخدام رمز المصادقة للحصول على التوكن (طول الرمز: {len(clean_code)})")
                        
                        # الحصول على التوكن باستخدام الرمز
                        try:
                            flow.fetch_token(code=clean_code)
                        except Exception as e:
                            # محاولة مع إضافة معلمة redirect_uri بشكل صريح
                            if "redirect_uri" in str(e):
                                logger.info("محاولة مع إضافة redirect_uri بشكل صريح")
                                flow.fetch_token(
                                    code=clean_code,
                                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                                )
                        
                        creds = flow.credentials
                        
                        # حفظ التوكن الجديد
                        SessionManager._save_credentials(creds)
                        
                        # إرسال رسالة نجاح
                        await bot.send_message(
                            chat_id=admin_chat_id,
                            text="✅ تم المصادقة مع يوتيوب بنجاح!"
                        )
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"خطأ في المصادقة: {error_msg}")
                        
                        # إرسال رسالة خطأ مفصلة للمستخدم
                        detailed_error = f"❌ خطأ في المصادقة: {error_msg}"
                        if "invalid_grant" in error_msg:
                            detailed_error += "\n\nيبدو أن رمز المصادقة غير صالح أو منتهي الصلاحية. يرجى المحاولة مرة أخرى باستخدام /auth"
                            # إعادة تعيين حالة انتظار الرمز للسماح بمحاولة جديدة
                            SessionManager._waiting_for_code = False
                            SessionManager._auth_code = None
                        
                        await bot.send_message(
                            chat_id=admin_chat_id,
                            text=detailed_error
                        )
                        raise
            
            return creds
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من جلسة يوتيوب: {str(e)}")
            admin_chat_id = SessionManager.get_admin_chat_id()
            if admin_chat_id:
                try:
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    await bot.send_message(
                        chat_id=admin_chat_id,
                        text=f"❌ خطأ في المصادقة مع يوتيوب: {str(e)}"
                    )
                except:
                    pass
            raise

    @staticmethod
    async def _terminal_auth():
        """المصادقة عبر التيرمنال كخيار احتياطي"""
        logger.info("إنشاء توكن جديد عبر التيرمنال")
        flow = InstalledAppFlow.from_client_secrets_file(
            YOUTUBE_CLIENT_SECRETS_FILE, 
            SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # استخدام OOB (Out-of-Band) للمصادقة
        )
        
        # عرض رابط المصادقة للمستخدم
        auth_url = flow.authorization_url()[0]
        print("\n" + "=" * 60)
        print("🔐 يرجى النقر على الرابط التالي للمصادقة مع يوتيوب:")
        print(auth_url)
        print("بعد المصادقة، سيتم عرض رمز تحقق على الشاشة. يرجى نسخ هذا الرمز وإدخاله هنا.")
        print("=" * 60 + "\n")
        
        # انتظار الرد من المستخدم
        code = None
        while not code:
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: input("أدخل رمز المصادقة: ")
                )
                code = response.strip()
            except Exception as e:
                logger.error(f"خطأ في انتظار الرمز: {str(e)}")
                continue
        
        # الحصول على التوكن باستخدام الرمز
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # حفظ التوكن الجديد
        SessionManager._save_credentials(creds)
        
        # طباعة رسالة نجاح
        print("✅ تم المصادقة مع يوتيوب بنجاح!")
        
        return creds

    @staticmethod
    def _load_credentials():
        """تحميل بيانات الاعتماد من الملف"""
        if os.path.exists(YOUTUBE_TOKEN_PICKLE):
            with open(YOUTUBE_TOKEN_PICKLE, 'rb') as token:
                return pickle.load(token)
        return None

    @staticmethod
    def _save_credentials(creds):
        """حفظ بيانات الاعتماد في الملف"""
        os.makedirs(os.path.dirname(YOUTUBE_TOKEN_PICKLE), exist_ok=True)
        with open(YOUTUBE_TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)
            logger.info(f"تم حفظ بيانات الاعتماد في {YOUTUBE_TOKEN_PICKLE}")

    @staticmethod
    def check_telegram_session():
        """
        التحقق من وجود ملف جلسة تيليجرام
        """
        exists = os.path.exists(TELEGRAM_SESSION_PATH)
        if exists:
            logger.info(f"تم العثور على ملف جلسة تيليجرام: {TELEGRAM_SESSION_PATH}")
        else:
            logger.warning(f"لم يتم العثور على ملف جلسة تيليجرام: {TELEGRAM_SESSION_PATH}")
        return exists

# استدعاء دالة التهيئة عند استيراد الملف
SessionManager.initialize()