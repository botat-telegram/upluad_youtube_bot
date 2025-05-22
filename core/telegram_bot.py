import os, re, traceback, logging, aiohttp, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from config.config import TELEGRAM_BOT_TOKEN, TEMP_DOWNLOAD_PATH, YOUTUBE_TOKEN_PICKLE
from core.youtube_utils import YouTubeUploader
from core.telegram_utils import TelegramDownloader
from utils.session_manager import SessionManager
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class UploadBot:
    def __init__(self):
        self.youtube = YouTubeUploader(init_auth=False)
        self.telegram_downloader = TelegramDownloader()
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
        os.makedirs(TEMP_DOWNLOAD_PATH, exist_ok=True)
        self.youtube_initialized = False
        
    def setup_handlers(self):
        self.app.add_handler(CommandHandler('start', self.start_command))
        self.app.add_handler(CommandHandler('help', self.help_command))
        self.app.add_handler(CommandHandler('setadmin', self.set_admin_command))
        self.app.add_handler(CommandHandler('auth', self.auth_command))
        self.app.add_handler(CommandHandler('checkauth', self.check_auth_command))
        self.app.add_handler(CommandHandler('sendcode', self.send_code_command))
        self.app.add_handler(CommandHandler('authhelp', self.auth_help_command))
        self.app.add_handler(CommandHandler('cancel', self.cancel_command))
        self.app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, self.handle_video))
        
        # تحسين فلتر روابط تيليجرام
        tg_link_pattern = r'https?://(?:t|telegram)\.(?:me|dog)/([^/]+)/(\d+)'
        self.app.add_handler(MessageHandler(filters.Regex(tg_link_pattern), self.handle_telegram_link))
        
        self.app.add_handler(CallbackQueryHandler(self.handle_playlist_selection))
        
        # معالج خاص للرسائل النصية
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        self.app.add_error_handler(self.error_handler)

    async def initialize_youtube(self):
        """تهيئة اتصال يوتيوب"""
        if not self.youtube_initialized:
            try:
                await self.youtube.initialize()
                self.youtube_initialized = True
                logger.info("تم تهيئة اتصال يوتيوب بنجاح")
                return True
            except Exception as e:
                logger.error(f"فشل في تهيئة اتصال يوتيوب: {str(e)}")
                return False
        return True

    async def auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية المصادقة مع يوتيوب"""
        chat_id = update.effective_chat.id
        admin_chat_id = SessionManager.get_admin_chat_id()
        
        if admin_chat_id is None:
            await update.message.reply_text(
                "⚠️ يجب تعيين مسؤول أولاً. استخدم الأمر /setadmin [كلمة_المرور]\n"
                "كلمة المرور الافتراضية هي: upluad-youtube-1234"
            )
            return
            
        if chat_id != admin_chat_id:
            await update.message.reply_text(
                "❌ عذراً، فقط المسؤول يمكنه استخدام هذا الأمر."
            )
            return
            
        await update.message.reply_text(
            "🔄 جاري بدء عملية المصادقة مع يوتيوب...\n\n"
            "سيتم إرسال رابط لك للمصادقة. اتبع الخطوات التالية:\n\n"
            "1️⃣ اضغط على الرابط الذي سيظهر\n"
            "2️⃣ سجل دخولك بحساب Google المرتبط بقناة يوتيوب\n"
            "3️⃣ اسمح بالصلاحيات المطلوبة\n"
            "4️⃣ انسخ رمز المصادقة الذي سيظهر\n"
            "5️⃣ أرسل الرمز مباشرة للبوت هنا\n\n"
            "⏳ في انتظار الاتصال..."
        )
        
        try:
            success = await self.initialize_youtube()
            if success:
                await update.message.reply_text(
                    "✅ تم تهيئة اتصال يوتيوب بنجاح!"
                )
            else:
                await update.message.reply_text(
                    "❌ فشل في تهيئة اتصال يوتيوب. يرجى المحاولة مرة أخرى.\n"
                    "يمكنك استخدام /authhelp للحصول على مساعدة مفصلة."
                )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"خطأ في المصادقة: {error_msg}")
            
            message = f"❌ حدث خطأ: {error_msg}"
            if "invalid_grant" in error_msg:
                message += "\n\nيبدو أن هناك مشكلة في رمز المصادقة. يرجى استخدام /authhelp للحصول على مساعدة."
            
            await update.message.reply_text(message)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أخطاء محسّن"""
        error_details = traceback.format_exc()
        logger.error(f"خطأ: {context.error}\n{error_details}")
        
        if update and update.effective_message:
            error_type = type(context.error).__name__
            simple_error = str(context.error).split('\n')[0]  # الحصول على السطر الأول فقط
            
            if "File too large" in simple_error:
                await update.effective_message.reply_text(
                    "❌ خطأ: حجم الملف كبير جدًا. استخدم رابط تيليجرام بدلاً من ذلك."
                )
            else:
                await update.effective_message.reply_text(
                    f"❌ حدث خطأ: {simple_error}\nنوع الخطأ: {error_type}"
                )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🌟 أهلاً وسهلاً بك في بوت رفع الفيديوهات إلى يوتيوب! 🎥\n\n"
            "يمكنك استخدام البوت بكل سهولة عن طريق:\n"
            "📤 إرسال فيديو مباشرة\n"
            "🔗 إرسال رابط فيديو من تيليجرام\n\n"
            "✨ مميزات البوت:\n"
            "• رفع الفيديوهات تلقائياً إلى قناتك\n"
            "• دعم الفيديوهات 40الكبيرة عبر روابط تيليجرام\n"
            "• إمكانية اختيار قائمة التشغيل\n\n"
            "🔐 خطوات الإعداد:\n"
            "1. استخدم الأمر `/setadmin upluad-youtube-1234` لتعيين نفسك كمسؤول للبوت\n"
            "2. استخدم الأمر /auth لبدء عملية المصادقة مع يوتيوب\n"
            "3. اتبع التعليمات التي ستظهر في البوت\n\n"
            "📚 للمزيد من المعلومات، استخدم /help"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 *بوت رفع فيديوهات من تيليجرام إلى يوتيوب*\n\n"
            "الأوامر المتاحة:\n"
            "• `/start` - بدء البوت\n"
            "• `/help` - عرض المساعدة\n"
            "• `/setadmin` - تعيين مستخدم كمدير\n"
            "• `/auth` - المصادقة مع يوتيوب\n"
            "• `/checkauth` - التحقق من حالة المصادقة\n"
            "• `/cancel` - إلغاء العملية الحالية\n\n"
            
            "كيفية الاستخدام:\n"
            "1. قم بإرسال فيديو من هاتفك\n"
            "2. أو شارك رابط رسالة من تيليجرام تحتوي على فيديو\n"
            "3. اختر قائمة التشغيل التي تريد رفع الفيديو إليها\n"
            "4. أدخل عنوان الفيديو\n"
            "5. انتظر حتى يتم الرفع\n\n"
            
            "إذا أردت إلغاء العملية في أي وقت، استخدم أمر `/cancel`"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # تأكد من تهيئة اتصال يوتيوب
        if not self.youtube_initialized:
            await update.message.reply_text(
                "⚠️ لم يتم تهيئة اتصال يوتيوب بعد. يرجى استخدام الأمر /setadmin ثم /auth أولاً."
            )
            return
            
        msg = await update.message.reply_text("⬇️ جاري تحميل الفيديو...")
        
        try:
            # تحديد نوع الملف
            if update.message.video:
                file = update.message.video
                file_name = file.file_name if file.file_name else f"video_{file.file_id[-10:]}.mp4"
            else:  # Document
                file = update.message.document
                file_name = file.file_name if file.file_name else f"video_{file.file_id[-10:]}.mp4"
            
            # تحميل الملف
            file_path = os.path.join(TEMP_DOWNLOAD_PATH, file_name)
            video_file = await file.get_file()
            
            # التحميل مع إظهار التقدم
            total_size = file.file_size
            downloaded = 0
            last_percentage = 0
            
            async with aiohttp.ClientSession() as session:
                async with session.get(video_file.file_path) as response:
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024 * 1024)  # 1MB chunks
                            if not chunk:
                                break
                                
                            f.write(chunk)
                            downloaded += len(chunk)
                            percentage = int((downloaded / total_size) * 100)
                            
                            if percentage - last_percentage >= 5:
                                await msg.edit_text(
                                    f"⬇️ جاري التحميل: {percentage}%\n"
                                    f"تم تحميل: {downloaded / (1024 * 1024):.1f} ميجابايت / {total_size / (1024 * 1024):.1f} ميجابايت"
                                )
                                last_percentage = percentage
            
            await msg.edit_text("✅ اكتمل التحميل! جاري التحضير ليوتيوب...")
            
            # حفظ معلومات الملف
            context.user_data.update({
                'file_path': file_path,
                'original_name': file_name
            })
            
            # الحصول على قوائم التشغيل
            playlists = self.youtube.get_playlists()
            keyboard = [[InlineKeyboardButton(title, callback_data=f"playlist_{id}")] 
                       for id, title in playlists]
            
            await msg.edit_text("اختر قائمة تشغيل:", reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            error_msg = str(e)
            await msg.edit_text(f"❌ خطأ: {error_msg}\nيرجى المحاولة مرة أخرى.")
            if 'file_path' in context.user_data and os.path.exists(context.user_data['file_path']):
                os.remove(context.user_data['file_path'])
            context.user_data.clear()
    
    async def handle_telegram_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # تأكد من تهيئة اتصال يوتيوب
        if not self.youtube_initialized:
            await update.message.reply_text(
                "⚠️ لم يتم تهيئة اتصال يوتيوب بعد. يرجى استخدام الأمر /setadmin ثم /auth أولاً."
            )
            return
            
        msg = await update.message.reply_text("⬇️ جاري معالجة رابط تيليجرام...")
        
        try:
            link = update.message.text
            logger.info(f"معالجة رابط: {link}")
            
            # تحليل الرابط باستخدام الوظيفة الجديدة
            link_info = await self.telegram_downloader.parse_telegram_link(link)
            
            if not link_info:
                await msg.edit_text("❌ صيغة الرابط غير صحيحة. تأكد من نسخ الرابط بشكل كامل.")
                return
                
            # تحقق من نوع الرابط (مجموعة عامة أو خاصة)
            context.user_data['telegram_link_info'] = link_info
            
            # الحصول على قوائم التشغيل من يوتيوب أولاً (لجميع أنواع الروابط)
            playlists = await self.youtube.get_playlists()
            keyboard = [[InlineKeyboardButton(title, callback_data=f"playlist_{id}")] 
                      for id, title in playlists]
            
            await msg.edit_text("اختر قائمة تشغيل للفيديو:", 
                              reply_markup=InlineKeyboardMarkup(keyboard))
                
        except Exception as e:
            error_msg = str(e)
            await msg.edit_text(f"❌ خطأ: {error_msg}\nيرجى المحاولة مرة أخرى.")
            context.user_data.clear()

    async def handle_playlist_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        # استخراج معرف قائمة التشغيل
        playlist_id = query.data.replace("playlist_", "")
        
        # حفظ في البيانات
        context.user_data['playlist_id'] = playlist_id
        playlist_title = next((title for id, title in await self.youtube.get_playlists() if id == playlist_id), "غير معروف")
        
        # الاستجابة للمستخدم
        await query.edit_message_text(f"✓ تم اختيار قائمة التشغيل: {playlist_title}")
        
        # طلب عنوان الفيديو مباشرة بعد اختيار القائمة (لكل أنواع الفيديوهات)
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="أدخل عنوان الفيديو الذي تريد رفعه:"
        )
        
        # حفظ معرف الرسالة لاستخدامه لاحقاً للتحديثات أثناء التنزيل
        context.user_data['status_message_id'] = msg.message_id

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية للتعامل مع رموز المصادقة وعناوين الفيديو"""
        message_text = update.message.text
        chat_id = update.effective_chat.id
        
        # محاولة معالجة الرسالة كرمز مصادقة
        # نتحقق إذا كان النص يحتوي على ما يشبه رمز المصادقة من جوجل
        is_auth_code = False
        
        # فحص أكثر شمولاً لرموز جوجل المختلفة
        if SessionManager._waiting_for_code:
            if "4/" in message_text or "4%2F" in message_text:
                is_auth_code = True
            elif len(message_text) > 20:  # رموز جوجل عادة طويلة
                is_auth_code = True
            
            if is_auth_code:
                logger.info(f"محتمل رمز مصادقة: {message_text[:15]}...")
                result = await SessionManager.receive_auth_code(message_text, chat_id)
                if result:
                    await update.message.reply_text("✓ تم استلام رمز المصادقة وجاري المعالجة...")
                    return
        
        # إذا لم يتم التعرف على الرسالة كرمز مصادقة، عاملها كعنوان فيديو
        if 'playlist_id' in context.user_data:
            # تخزين عنوان الفيديو
            context.user_data['video_title'] = message_text
            
            # بدء عملية التنزيل والرفع معاً
            await self.process_download_and_upload(update, context)
        else:
            await update.message.reply_text("❌ يجب اختيار قائمة تشغيل أولاً.")

    async def process_download_and_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دالة موحدة لتنزيل ورفع الفيديو"""
        title = context.user_data.get('video_title')
        
        # التأكد من وجود عنوان للفيديو
        if not title:
            await update.message.reply_text("❌ يجب إدخال عنوان للفيديو.")
            return
            
        # إنشاء رسالة الحالة
        msg = await update.message.reply_text("⬇️ جاري تجهيز الفيديو...")
        
        try:
            # تحقق من نوع الفيديو (رابط تيليجرام أو ملف محمل)
            downloaded_path = None
            
            if 'telegram_link_info' in context.user_data:
                # تنزيل الفيديو من رابط تيليجرام
                link_info = context.user_data['telegram_link_info']
                
                await msg.edit_text("⬇️ جاري تنزيل الفيديو من تيليجرام...")
                
                # بدء تشغيل عميل تيليجرام
                await self.telegram_downloader.start()
                
                # تعريف دالة تتبع التقدم
                percent_complete = [0]
                
                async def progress_callback(current, total):
                    percent = int((current / total) * 100)
                    
                    # تحديث الرسالة فقط عندما يتغير النسبة بـ 10٪
                    if percent // 10 > percent_complete[0] // 10:
                        percent_complete[0] = percent
                        try:
                            await msg.edit_text(f"⬇️ جاري تنزيل الفيديو... {percent}%")
                        except Exception:
                            pass  # تجاهل أخطاء تحديث الرسالة
                
                # تحميل الفيديو حسب نوع الرابط
                if link_info['type'] == 'public':
                    # رابط عام
                    downloaded_path = await self.telegram_downloader.download_media_from_link(
                        link_info['channel_username'], 
                        link_info['message_id'],
                        progress_callback
                    )
                else:
                    # رابط مجموعة خاصة
                    downloaded_path = await self.telegram_downloader.download_media_from_private_chat(
                        link_info['chat_id'],
                        link_info['message_id'],
                        link_info['sub_message_id'],
                        progress_callback
                    )
                    
                if not downloaded_path:
                    await msg.edit_text("❌ فشل في تنزيل الفيديو من الرابط.")
                    return
                    
            elif 'file_path' in context.user_data:
                # استخدام ملف تم تحميله مسبقاً
                downloaded_path = context.user_data['file_path']
            else:
                await msg.edit_text("❌ لم يتم تحديد أي فيديو للرفع.")
                return
            
            # حفظ مسار الملف المنزل
            context.user_data['file_path'] = downloaded_path
            
            # بدء الرفع إلى يوتيوب مباشرة
            await msg.edit_text("⬆️ جاري الرفع إلى يوتيوب...")
            
            # رفع الفيديو
            video_url = await self.youtube.upload_video(
                downloaded_path,
                title,
                context.user_data['playlist_id']
            )
            
            # تنظيف الملفات المؤقتة
            if os.path.exists(downloaded_path):
                os.remove(downloaded_path)
                logger.info(f"تم حذف الملف المؤقت: {downloaded_path}")
                
            # إعلام المستخدم بالانتهاء
            await msg.edit_text(f"✅ تم الرفع بنجاح!\n🔗 الرابط: {video_url}")
            
            # تنظيف بيانات المستخدم
            context.user_data.clear()
            
        except Exception as e:
            logger.error(f"خطأ في العملية: {str(e)}")
            await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
            if 'file_path' in context.user_data and os.path.exists(context.user_data['file_path']):
                os.remove(context.user_data['file_path'])
            context.user_data.clear()

    async def set_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تعيين المستخدم الحالي كمسؤول"""
        chat_id = update.effective_chat.id
        
        # التحقق من وجود كلمة المرور
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "⚠️ يجب إدخال كلمة المرور. استخدم الأمر بهذه الطريقة:\n"
                "/setadmin [كلمة_المرور]"
            )
            return
            
        password = context.args[0]
        
        # التحقق من صحة كلمة المرور
        if SessionManager.check_admin_password(password):
            SessionManager.set_admin_chat_id(chat_id)
            await update.message.reply_text(
                "✅ تم تعيينك كمسؤول للبوت! يمكنك الآن استلام روابط المصادقة وإرسال رموز التحقق من خلال هذه المحادثة."
            )
        else:
            await update.message.reply_text(
                "❌ كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى."
            )

    async def check_auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """التحقق من حالة المصادقة مع يوتيوب"""
        chat_id = update.effective_chat.id
        admin_chat_id = SessionManager.get_admin_chat_id()
        
        # التحقق من صلاحيات المستخدم
        if admin_chat_id is None or chat_id != admin_chat_id:
            await update.message.reply_text(
                "❌ عذراً، فقط المسؤول يمكنه استخدام هذا الأمر."
            )
            return
            
        # التحقق من وجود ملف التوكن
        token_exists = os.path.exists(YOUTUBE_TOKEN_PICKLE)
        
        if token_exists:
            # محاولة التحقق من صلاحية التوكن
            try:
                creds = SessionManager._load_credentials()
                if creds and creds.valid:
                    await update.message.reply_text(
                        "✅ المصادقة مع يوتيوب صالحة وتعمل بشكل جيد!"
                    )
                elif creds and creds.expired and creds.refresh_token:
                    await update.message.reply_text(
                        "⚠️ توكن يوتيوب منتهي الصلاحية ولكن يمكن تجديده. جاري المحاولة..."
                    )
                    try:
                        creds.refresh(Request())
                        SessionManager._save_credentials(creds)
                        await update.message.reply_text(
                            "✅ تم تجديد التوكن بنجاح!"
                        )
                    except Exception as e:
                        await update.message.reply_text(
                            f"❌ فشل تجديد التوكن: {str(e)}\nيرجى استخدام /auth مرة أخرى."
                        )
                else:
                    await update.message.reply_text(
                        "❌ توكن يوتيوب غير صالح. يرجى استخدام /auth لإعادة المصادقة."
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ خطأ في التحقق من التوكن: {str(e)}\nيرجى استخدام /auth لإعادة المصادقة."
                )
        else:
            await update.message.reply_text(
                "❌ لم يتم العثور على ملف توكن يوتيوب. يرجى استخدام /auth للمصادقة."
            )

    async def send_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر لإرسال رمز المصادقة يدوياً"""
        chat_id = update.effective_chat.id
        admin_chat_id = SessionManager.get_admin_chat_id()
        
        # التحقق من صلاحيات المستخدم
        if admin_chat_id is None or chat_id != admin_chat_id:
            await update.message.reply_text(
                "❌ عذراً، فقط المسؤول يمكنه استخدام هذا الأمر."
            )
            return
            
        # استخراج الرمز من النص الكامل للرسالة
        full_text = update.message.text.strip()
        code = None
        
        # في حالة وجود مسافات، نحاول استخراج الرمز
        if len(full_text.split()) > 1:
            parts = full_text.split()
            # تجاهل الجزء الأول لأنه الأمر نفسه
            for part in parts[1:]:
                if part.startswith("4/") or "4/" in part:
                    code = part
                    break
            
            # إذا لم نجد رمزاً محدداً، نأخذ كل الأجزاء بعد الأمر
            if not code:
                code = " ".join(parts[1:])
        else:
            # إذا لا توجد وسيطات في الأمر
            await update.message.reply_text(
                "⚠️ يجب إدخال رمز المصادقة. استخدم الأمر بهذه الطريقة:\n"
                "/sendcode [رمز_المصادقة]"
            )
            return
            
        # محاولة معالجة الرمز
        await update.message.reply_text(f"🔄 جاري معالجة الرمز: {code[:10]}...")
        
        # تأكد من أن النظام ينتظر رمز مصادقة
        if not SessionManager._waiting_for_code:
            SessionManager._waiting_for_code = True
            logger.info("تعيين حالة انتظار الرمز لاستقبال الرمز المرسل")
            
        is_processed = await SessionManager.receive_auth_code(code, chat_id)
        if is_processed:
            await update.message.reply_text(
                "✓ تم استلام الرمز وجاري معالجته..."
            )
        else:
            await update.message.reply_text(
                "❌ لم يتم معالجة الرمز. تأكد من أنك بدأت عملية المصادقة أولاً باستخدام /auth"
            )
            
    async def auth_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مساعدة إضافية حول عملية المصادقة مع يوتيوب"""
        await update.message.reply_text(
            "🔐 مساعدة المصادقة مع يوتيوب 🔐\n\n"
            "إذا واجهت مشاكل في المصادقة، اتبع هذه الخطوات:\n\n"
            "1️⃣ تأكد من تعيين نفسك كمسؤول أولاً باستخدام:\n"
            "/setadmin upluad-youtube-1234\n\n"
            "2️⃣ ابدأ عملية المصادقة باستخدام:\n"
            "/auth\n\n"
            "3️⃣ اضغط على الرابط المرسل وقم بتسجيل الدخول إلى حساب Google الخاص بقناتك\n\n"
            "4️⃣ بعد المصادقة، ستحصل على رمز. انسخه وأرسله هنا مباشرة\n\n"
            "🔍 ملاحظات هامة حول رمز المصادقة:\n"
            "• يبدأ عادة بـ '4/' متبوعاً بحروف وأرقام\n"
            "• الرمز حساس لحالة الأحرف، فتأكد من نسخه بالضبط\n"
            "• يمكنك استخدام الأمر /sendcode لإرسال الرمز إذا لم يتم التعرف عليه تلقائياً\n\n"
            "⚠️ إذا ظهرت رسالة 'invalid_grant':\n"
            "• قد يكون الرمز منتهي الصلاحية، قم بتكرار عملية المصادقة\n"
            "• قد يكون هناك خطأ في نسخ الرمز، تأكد من نسخه بالكامل\n\n"
            "🔄 لإعادة المحاولة استخدم الأمر:\n"
            "/auth"
        )

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء العملية الجارية وتنظيف البيانات"""
        try:
            # تنظيف البيانات المخزنة
            if 'file_path' in context.user_data and os.path.exists(context.user_data['file_path']):
                try:
                    os.remove(context.user_data['file_path'])
                    logger.info(f"تم حذف الملف المؤقت: {context.user_data['file_path']}")
                except Exception as e:
                    logger.error(f"فشل في حذف الملف المؤقت: {str(e)}")
            
            # إعادة تعيين بيانات المستخدم
            context.user_data.clear()
            
            # إعلام المستخدم
            await update.message.reply_text("✓ تم إلغاء العملية الحالية. يمكنك البدء من جديد.")
            
        except Exception as e:
            logger.error(f"خطأ أثناء إلغاء العملية: {str(e)}")
            await update.message.reply_text(f"❌ حدث خطأ أثناء إلغاء العملية: {str(e)}")

    async def run(self):
        try:
            logger.info("بدء تشغيل البوت...")
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("البوت يعمل الآن. اضغط Ctrl+C للإيقاف.")
            # Use asyncio.Event() for clean shutdown
            stop_event = asyncio.Event()
            await stop_event.wait()
            
        except asyncio.CancelledError:
            logger.info("تم إلغاء تشغيل البوت")
            pass
        except Exception as e:
            logger.error(f"حدث خطأ أثناء تشغيل البوت: {str(e)}")
            traceback.print_exc()
        finally:
            logger.info("إيقاف البوت وتنظيف الموارد...")
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
                await self.telegram_downloader.stop()
                logger.info("تم إغلاق البوت بنجاح.")
            except Exception as e:
                logger.error(f"حدث خطأ أثناء إيقاف البوت: {str(e)}")
                traceback.print_exc()

if __name__ == '__main__':
    bot = UploadBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم.")
    except Exception as e:
        logger.critical(f"حدث خطأ غير متوقع: {str(e)}")
        print(f"خطأ: {str(e)}")
