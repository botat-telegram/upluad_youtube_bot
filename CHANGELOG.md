# سجل التغييرات

جميع التغييرات المهمة في هذا المشروع سيتم توثيقها في هذا الملف.

## [1.0.0] - 2025-05-23

### الميزات الجديدة
- تجربة مستخدم محسنة مع تنزيل وتحميل تلقائي للفيديوهات
- إضافة دعم لتنزيل الفيديوهات من المجموعات الخاصة في تيليجرام
- تحسين واجهة المستخدم في البوت مع رسائل واضحة عن حالة العملية
- إضافة أمر `/cancel` لإلغاء العمليات الجارية مثل التنزيل أو الرفع
- إعادة هيكلة العملية بحيث يتم سؤال المستخدم عن قائمة التشغيل أولاً ثم عنوان الفيديو

### إصلاحات
- إصلاح مشكلة انتهاء صلاحية توكن يوتيوب مع إضافة تجديد تلقائي
- إصلاح مشكلة `AttributeError: 'NoneType' object has no attribute 'reply_text'`
- معالجة خطأ "'coroutine' object is not iterable" في ملف telegram_bot.py
- تحسين معالجة أنواع الوسائط المختلفة وإضافة رسائل خطأ واضحة
- إصلاح مشاكل في الوسائط غير المدعومة (MessageMediaUnsupported)

### تحسينات تقنية
- إعادة هيكلة الكود مع فصل المسؤوليات بشكل أفضل
- تحسين نظام التسجيل ليوفر معلومات أكثر تفصيلاً عن الأخطاء
- إضافة معالجة أفضل للاستثناءات وتحسين الاستقرار
- تحسين نظام المصادقة مع Google/YouTube
- إضافة نظام مراقبة الملفات لإعادة تشغيل البوت تلقائياً عند تغيير الملفات

## [0.9.0] - 2025-05-10

### الميزات الجديدة
- إطلاق النسخة التجريبية الأولى من البوت
- دعم التحميل من روابط تيليجرام العامة
- تنزيل الفيديوهات المرسلة مباشرة إلى البوت
- إمكانية رفع الفيديوهات إلى يوتيوب مع اختيار قائمة التشغيل
- نظام مصادقة أساسي مع YouTube API
- أوامر `/start` و `/help` و `/setadmin` و `/auth` 