from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle
import os
import logging
import asyncio
from config.config import (
    YOUTUBE_CLIENT_SECRETS_FILE, 
    YOUTUBE_TOKEN_PICKLE,
    SCOPES, 
    UPLOAD_CHUNK_SIZE, 
    MAX_UPLOAD_RETRIES
)
from utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

class YouTubeUploader:
    def __init__(self, init_auth=False):
        self.youtube = None
        if init_auth:
            # هذا لن يستخدم بعد الآن، سنستخدم الدالة المتزامنة initialize بدلاً منه
            self._initialize()
        # لا نقوم بتهيئة الاتصال تلقائياً هنا - سيتم ذلك عند الطلب بواسطة أمر /auth
        
    async def initialize(self):
        """تهيئة الاتصال مع يوتيوب باستخدام SessionManager (متزامنة)"""
        if not self.youtube:
            self.youtube = await self._authenticate_async()
        return self.youtube
        
    def _initialize(self):
        """تهيئة الاتصال مع يوتيوب باستخدام SessionManager (غير متزامنة)"""
        if not self.youtube:
            self.youtube = self._authenticate()
        return self.youtube

    def _authenticate(self):
        """مصادقة غير متزامنة - تستخدم فقط عند الحاجة للاستدعاء من دالة غير متزامنة"""
        try:
            # استخدام SessionManager للتحقق من صلاحية جلسة يوتيوب
            logger.info("جاري التحقق من صلاحية جلسة يوتيوب (غير متزامن)")
            loop = asyncio.get_event_loop()
            credentials = loop.run_until_complete(SessionManager.check_youtube_auth())
            
            if not credentials:
                logger.error("فشل الحصول على بيانات اعتماد صالحة")
                raise Exception("فشل الحصول على بيانات اعتماد صالحة")
                
            logger.info("تم الحصول على بيانات اعتماد صالحة")
            return build('youtube', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"خطأ في المصادقة مع يوتيوب: {str(e)}")
            raise
            
    async def _authenticate_async(self):
        """مصادقة متزامنة - تستخدم من الدوال المتزامنة"""
        try:
            # استخدام SessionManager للتحقق من صلاحية جلسة يوتيوب
            logger.info("جاري التحقق من صلاحية جلسة يوتيوب (متزامن)")
            credentials = await SessionManager.check_youtube_auth()
            
            if not credentials:
                logger.error("فشل الحصول على بيانات اعتماد صالحة")
                raise Exception("فشل الحصول على بيانات اعتماد صالحة")
                
            logger.info("تم الحصول على بيانات اعتماد صالحة")
            return build('youtube', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"خطأ في المصادقة مع يوتيوب: {str(e)}")
            raise

    async def get_playlists(self):
        try:
            if not self.youtube:
                logger.error("لم يتم تهيئة اتصال يوتيوب")
                raise Exception("يجب تهيئة اتصال يوتيوب أولاً")

            logger.info("جاري التحقق من صلاحية الاتصال مع يوتيوب")
            try:
                # اختبار الاتصال
                self.youtube.playlists().list(part="snippet", maxResults=1).execute()
            except Exception as conn_error:
                logger.error(f"خطأ في الاتصال مع يوتيوب: {str(conn_error)}")
                # إعادة تهيئة الاتصال
                self.youtube = None
                self.youtube = await self._authenticate_async()

            logger.info("جاري جلب قوائم التشغيل من يوتيوب")
            request = self.youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            response = request.execute()

            if 'items' not in response:
                logger.error("لم يتم العثور على قوائم تشغيل في الاستجابة")
                return []

            playlists = [(item['id'], item['snippet']['title']) for item in response['items']]
            logger.info(f"تم جلب {len(playlists)} قائمة تشغيل")
            return playlists

        except Exception as e:
            logger.error(f"خطأ في جلب قوائم التشغيل: {str(e)}")
            raise Exception(f"فشل في جلب قوائم التشغيل: {str(e)}")


    async def upload_video(self, file_path, title, playlist_id):
        try:
            logger.info(f"بدء رفع فيديو: {title}")
            
            if not os.path.exists(file_path):
                logger.error(f"ملف الفيديو غير موجود: {file_path}")
                raise FileNotFoundError(f"ملف الفيديو غير موجود: {file_path}")
                
            body = {
                'snippet': {
                    'title': title,
                    'description': 'Uploaded via Telegram Bot',
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'unlisted',
                    'selfDeclaredMadeForKids': False
                }
            }

            # Configure chunked upload
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"حجم الفيديو: {file_size_mb:.2f} ميجابايت")
            
            media = MediaFileUpload(
                file_path,
                mimetype='video/*',
                chunksize=UPLOAD_CHUNK_SIZE,
                resumable=True
            )
            
            # Insert the video
            insert_request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            retry = 0
            
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"تقدم الرفع: {progress}%")
                    if response:
                        logger.info(f"اكتمل الرفع بنجاح! معرف الفيديو: {response['id']}")
                except Exception as e:
                    retry += 1
                    if retry >= MAX_UPLOAD_RETRIES:
                        logger.error(f"فشل الرفع بعد {MAX_UPLOAD_RETRIES} محاولة: {str(e)}")
                        raise Exception(f"فشل الرفع بعد {MAX_UPLOAD_RETRIES} محاولة: {str(e)}")
                    logger.warning(f"إعادة محاولة الرفع... المحاولة {retry}")
                    
            video_id = response['id']

            # Add to playlist
            if playlist_id:
                logger.info(f"إضافة الفيديو إلى قائمة التشغيل: {playlist_id}")
                self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                ).execute()

            video_url = f'https://youtu.be/{video_id}'
            logger.info(f"تم رفع الفيديو بنجاح إلى: {video_url}")
            return video_url
            
        except Exception as e:
            logger.error(f"خطأ أثناء رفع الفيديو: {str(e)}")
            raise
