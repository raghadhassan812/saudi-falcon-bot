#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦅 بوت الصقر السعودي - النسخة الاحترافية المتكاملة
✅ نظام حماية متقدم 24/7
✅ إدارة كاملة من داخل البوت
✅ حظر أبدي ذكي للمخالفين
✅ عمل صامت بدون إشعارات
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set, List
from telegram import Update, ChatPermissions, ChatMember
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackContext,
    CallbackQueryHandler
)
from telegram.constants import ChatMemberStatus, ParseMode

# ==================== إعدادات المالك ====================
OWNER_ID = 6063934552  # معرّف المالك
BOT_TOKEN = "8080869266:AAFt3yFrtM2c5TUj0j_BOf3ttSIzNVq6i70"  # توكن البوت

# ==================== إعدادات النظام ====================
CONFIG_FILE = "bot_config.json"
LOG_FILE = "bot_operations.log"

# ==================== إعداد التسجيل ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== هياكل البيانات ====================
class BotConfig:
    def __init__(self):
        self.blocked_words: Set[str] = set()
        self.global_banned_users: Dict[int, Dict] = {}  # {user_id: {info}}
        self.group_settings: Dict[int, Dict] = {}  # {group_id: settings}
        self.user_warnings: Dict[int, List] = {}  # {user_id: [{reason, date}]}
        self.admin_users: Set[int] = {OWNER_ID}  # قائمة المسؤولين
        self.silent_mode: bool = True  # العمل الصامت
        
    def load(self):
        """تحميل الإعدادات من الملف"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blocked_words = set(data.get('blocked_words', []))
                    self.global_banned_users = data.get('global_banned_users', {})
                    self.group_settings = data.get('group_settings', {})
                    self.user_warnings = data.get('user_warnings', {})
                    self.admin_users = set(data.get('admin_users', [OWNER_ID]))
                    self.silent_mode = data.get('silent_mode', True)
                logger.info(f"✅ تم تحميل {len(self.blocked_words)} كلمة محظورة")
                logger.info(f"📊 {len(self.global_banned_users)} مستخدم محظور أبدياً")
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل الإعدادات: {e}")
    
    def save(self):
        """حفظ الإعدادات إلى الملف"""
        try:
            data = {
                'blocked_words': list(self.blocked_words),
                'global_banned_users': self.global_banned_users,
                'group_settings': self.group_settings,
                'user_warnings': self.user_warnings,
                'admin_users': list(self.admin_users),
                'silent_mode': self.silent_mode,
                'last_updated': datetime.now().isoformat()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("💾 تم حفظ الإعدادات")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الإعدادات: {e}")

# إنشاء كائن الإعدادات
config = BotConfig()

# ==================== دوال المساعدة ====================
def is_owner(user_id: int) -> bool:
    """التحقق إذا كان المستخدم هو المالك"""
    return user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    """التحقق إذا كان المستخدم مسؤولاً"""
    return user_id in config.admin_users

async def is_group_admin(bot, chat_id: int, user_id: int) -> bool:
    """التحقق إذا كان المستخدم مشرفاً في المجموعة"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

def normalize_text(text: str) -> str:
    """تطبيع النص للمقارنة"""
    import re
    text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)  # إزالة الرموز
    text = re.sub(r'\s+', ' ', text)  # إزالة المسافات الزائدة
    return text.strip().lower()

def contains_blocked_words(text: str) -> (bool, str):
    """التحقق من وجود كلمات محظورة"""
    normalized = normalize_text(text)
    for word in config.blocked_words:
        if normalize_text(word) in normalized:
            return True, word
    return False, None

def log_operation(operation: str, user_id: int, details: str = ""):
    """تسجيل العمليات"""
    log_entry = f"[{datetime.now().isoformat()}] {operation} | User: {user_id} | {details}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + "\n")
    logger.info(log_entry)

# ==================== أوامر المالك والمسؤولين ====================
async def owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المالك"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    keyboard = [
        ["📋 قائمة الأوامر", "⚙️ الإعدادات"],
        ["🚫 الكلمات المحظورة", "👥 المستخدمون المحظورون"],
        ["📊 الإحصائيات", "🔄 تحديث البوت"]
    ]
    
    message = f"""
🦅 **لوحة تحكم بوت الصقر السعودي**

**👑 المالك:** {update.effective_user.mention_html()}
**📅 آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**📊 الإحصائيات:**
• الكلمات المحظورة: {len(config.blocked_words)}
• المستخدمون المحظورون: {len(config.global_banned_users)}
• المجموعات النشطة: {len(config.group_settings)}
• التحذيرات المسجلة: {sum(len(w) for w in config.user_warnings.values())}

**⚙️ الإعدادات الحالية:**
• الوضع الصامت: {'✅ مفعل' if config.silent_mode else '❌ معطل'}
• المسؤولين: {len(config.admin_users)}

**🔧 استخدم الأوامر التالية:**
/panel - هذه اللوحة
/addword - إضافة كلمة محظورة
/delword - حذف كلمة محظورة
/words - عرض الكلمات المحظورة
/banlist - عرض المحظورين
/silent - تبديل الوضع الصامت
/stats - إحصائيات مفصلة
"""
    
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

async def add_banned_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة كلمة/كلمات محظورة"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 **طريقة الاستخدام:**\n"
            "`/addword كلمة1 كلمة2 كلمة3`\n\n"
            "**أو:**\n"
            "`/addword`\n"
            "ثم اكتب الكلمات في رسالة (كل كلمة في سطر)"
        )
        return
    
    # استقبال الكلمات من الأمر
    words_to_add = []
    
    if update.message.reply_to_message:
        # إذا كان رداً على رسالة تحتوي كلمات
        reply_text = update.message.reply_to_message.text or ""
        words_to_add = [line.strip() for line in reply_text.split('\n') if line.strip()]
    else:
        # كلمات من الأمر نفسه
        words_to_add = context.args
    
    added_count = 0
    duplicate_count = 0
    
    for word in words_to_add:
        word = word.strip()
        if not word:
            continue
            
        normalized = normalize_text(word)
        if any(normalize_text(w) == normalized for w in config.blocked_words):
            duplicate_count += 1
        else:
            config.blocked_words.add(word)
            added_count += 1
    
    config.save()
    
    response = f"""
✅ **تمت إضافة الكلمات المحظورة**

➕ **تم الإضافة:** {added_count} كلمة جديدة
➖ **مكررة:** {duplicate_count} كلمة
📊 **الإجمالي الآن:** {len(config.blocked_words)} كلمة

**📝 ملاحظة:** الكلمات المحظورة ستطبق على:
• جميع المجموعات الجديدة تلقائياً
• جميع الرسائل مباشرة
• العمل صامت بدون إشعارات
"""
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    log_operation("ADD_WORDS", update.effective_user.id, f"Added {added_count} words")

async def delete_banned_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف كلمة محظورة"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "🗑️ **طريقة الاستخدام:**\n"
            "`/delword الكلمة`\n\n"
            "**لعرض الكلمات:** `/words`"
        )
        return
    
    word_to_remove = ' '.join(context.args)
    normalized_to_remove = normalize_text(word_to_remove)
    
    removed = False
    exact_word = ""
    
    for word in list(config.blocked_words):
        if normalize_text(word) == normalized_to_remove:
            config.blocked_words.remove(word)
            exact_word = word
            removed = True
            break
    
    if removed:
        config.save()
        await update.message.reply_text(
            f"✅ **تم حذف الكلمة:** `{exact_word}`\n"
            f"📊 **الكلمات المتبقية:** {len(config.blocked_words)}",
            parse_mode=ParseMode.MARKDOWN
        )
        log_operation("DELETE_WORD", update.effective_user.id, f"Removed: {exact_word}")
    else:
        await update.message.reply_text(
            f"⚠️ **الكلمة غير موجودة:** `{word_to_remove}`\n"
            f"استخدم `/words` لعرض الكلمات المحظورة",
            parse_mode=ParseMode.MARKDOWN
        )

async def list_banned_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الكلمات المحظورة"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    if not config.blocked_words:
        await update.message.reply_text("📭 **لا توجد كلمات محظورة حالياً**")
        return
    
    words_list = sorted(list(config.blocked_words))
    
    # تقسيم القائمة إذا كانت طويلة
    chunk_size = 50
    chunks = [words_list[i:i + chunk_size] for i in range(0, len(words_list), chunk_size)]
    
    for i, chunk in enumerate(chunks):
        message = f"📋 **الكلمات المحظورة ({len(config.blocked_words)})**\n\n"
        for idx, word in enumerate(chunk, 1):
            message += f"{idx + (i * chunk_size)}. `{word}`\n"
        
        if len(chunks) > 1:
            message += f"\n📄 الصفحة {i + 1} من {len(chunks)}"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def list_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المستخدمين المحظورين أبدياً"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    if not config.global_banned_users:
        await update.message.reply_text("📭 **لا يوجد مستخدمون محظورون أبدياً**")
        return
    
    message = f"🚫 **المستخدمون المحظورون أبدياً ({len(config.global_banned_users)})**\n\n"
    
    for idx, (user_id, info) in enumerate(list(config.global_banned_users.items())[:50], 1):
        username = info.get('username', 'بدون معرف')
        date = info.get('date', 'غير معروف')
        reason = info.get('reason', 'كلمات محظورة')
        
        message += f"{idx}. **ID:** `{user_id}`\n"
        message += f"   **المعرف:** @{username}\n"
        message += f"   **التاريخ:** {date}\n"
        message += f"   **السبب:** {reason}\n\n"
    
    if len(config.global_banned_users) > 50:
        message += f"\n📄 **ملاحظة:** عرض 50 من {len(config.global_banned_users)}"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def toggle_silent_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل الوضع الصامت"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    config.silent_mode = not config.silent_mode
    config.save()
    
    status = "✅ مفعل" if config.silent_mode else "❌ معطل"
    await update.message.reply_text(
        f"🔇 **الوضع الصامت:** {status}\n\n"
        f"في الوضع الصامت:\n"
        f"• لا إشعارات في المجموعات\n"
        f"• الحذف الصامت للرسائل\n"
        f"• الحظر الصامت للأعضاء\n"
        f"• بدون رسائل تحذيرية",
        parse_mode=ParseMode.MARKDOWN
    )
    log_operation("TOGGLE_SILENT", update.effective_user.id, f"New status: {config.silent_mode}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات مفصلة"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط!")
        return
    
    total_warnings = sum(len(warns) for warns in config.user_warnings.values())
    
    stats_message = f"""
📊 **إحصائيات بوت الصقر السعودي**

**🔢 الكلمات المحظورة:** {len(config.blocked_words)}
**👥 المستخدمون المحظورون:** {len(config.global_banned_users)}
**👤 المستخدمون المحذرون:** {len(config.user_warnings)}
**⚠️ التحذيرات الكلية:** {total_warnings}
**👥 المجموعات النشطة:** {len(config.group_settings)}

**⚙️ الإعدادات:**
• الوضع الصامت: {'✅' if config.silent_mode else '❌'}
• المسؤولين: {len(config.admin_users)}

**📈 النشاط:**
• آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• الملفات المسجلة: 2
• السجلات: {sum(1 for _ in open(LOG_FILE, encoding='utf-8')) if os.path.exists(LOG_FILE) else 0} سطر

**🔧 الأوامر المتاحة للمالك:**
/panel - لوحة التحكم
/addword - إضافة كلمات محظورة
/delword - حذف كلمة محظورة
/words - عرض الكلمات المحظورة
/banlist - عرض المحظورين
/silent - تبديل الوضع الصامت
/stats - هذه الإحصائيات
"""
    
    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

# ==================== نظام الحماية المتقدم ====================
async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأعضاء الجدد (للتحقق من الحظر الأبدي)"""
    for member in update.message.new_chat_members:
        user_id = str(member.id)
        
        # التحقق من الحظر الأبدي
        if user_id in config.global_banned_users:
            try:
                # حظر المستخدم صامتاً
                await context.bot.ban_chat_member(
                    update.effective_chat.id,
                    member.id
                )
                
                # حذف رسالة الترحيب بالمستخدم (إذا كانت موجودة)
                try:
                    await update.message.delete()
                except:
                    pass
                
                # تسجيل العملية (بدون إشعار في المجموعة)
                log_operation("AUTO_BAN", member.id, 
                            f"Global banned user joined {update.effective_chat.title}")
                
                # إرسال رسالة خاصة للمالك فقط
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"🚫 **تم حظر مستخدم محظور أبدياً**\n\n"
                         f"• **المستخدم:** {member.mention_html()}\n"
                         f"• **المجموعة:** {update.effective_chat.title}\n"
                         f"• **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode=ParseMode.HTML
                )
                
            except Exception as e:
                logger.error(f"❌ فشل حظر مستخدم محظور: {e}")

async def check_message_for_violations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الرسائل للكلمات المحظورة"""
    # تجاهل الرسائل في الدردشات الخاصة
    if update.effective_chat.type == "private":
        return
    
    # تجاهل رسائل المشرفين
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except:
        pass
    
    # الحصول على نص الرسالة
    message_text = update.message.text or update.message.caption or ""
    if not message_text:
        return
    
    # التحقق من الكلمات المحظورة
    contains_banned, banned_word = contains_blocked_words(message_text)
    
    if contains_banned:
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        try:
            # 1. حذف الرسالة المخالفة فوراً
            await update.message.delete()
            
            # 2. إضافة تحذير للمستخدم
            if user_id not in config.user_warnings:
                config.user_warnings[user_id] = []
            
            config.user_warnings[user_id].append({
                'date': datetime.now().isoformat(),
                'reason': f'كلمة محظورة: {banned_word}',
                'group': update.effective_chat.title,
                'message': message_text[:100]
            })
            
            warning_count = len(config.user_warnings[user_id])
            
            # 3. الحظر الأبدي بعد 3 تحذيرات
            if warning_count >= 3:
                # حظر من المجموعة
                await context.bot.ban_chat_member(chat_id, int(user_id))
                
                # إضافة للحظر الأبدي
                config.global_banned_users[user_id] = {
                    'username': update.effective_user.username or 'بدون معرف',
                    'date': datetime.now().isoformat(),
                    'reason': 'تجاوز 3 تحذيرات',
                    'warnings': warning_count
                }
                
                # إرسال إشعار للمالك فقط
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"🚫 **تم حظر مستخدم أبدياً**\n\n"
                         f"• **المستخدم:** {update.effective_user.mention_html()}\n"
                         f"• **المعرف:** @{update.effective_user.username or 'بدون'}\n"
                         f"• **ID:** `{user_id}`\n"
                         f"• **السبب:** تجاوز 3 تحذيرات\n"
                         f"• **الكلمة:** {banned_word}\n"
                         f"• **المجموعة:** {update.effective_chat.title}",
                    parse_mode=ParseMode.HTML
                )
                
                log_operation("PERMANENT_BAN", user_id, 
                            f"3 warnings | Word: {banned_word}")
            
            # 4. تسجيل العملية
            log_operation("DELETE_MESSAGE", user_id, 
                         f"Banned word: {banned_word} | Warnings: {warning_count}")
            
            # 5. حفظ الإعدادات
            config.save()
            
            # 6. إرسال إشعار في المجموعة (فقط إذا كان الوضع الصامت معطل)
            if not config.silent_mode and warning_count < 3:
                try:
                    warning_msg = await update.message.reply_text(
                        f"⚠️ {update.effective_user.mention_html()}\n"
                        f"تم حذف رسالتك لاحتوائها على كلمة محظورة!\n"
                        f"التحذير #{warning_count}/3",
                        parse_mode=ParseMode.HTML
                    )
                    # حذف رسالة التحذير بعد 5 ثواني
                    await asyncio.sleep(5)
                    await warning_msg.delete()
                except:
                    pass
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة المخالفة: {e}")

async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عند إضافة البوت إلى مجموعة"""
    bot_user = await context.bot.get_me()
    
    for member in update.message.new_chat_members:
        if member.id == bot_user.id:
            group_id = update.effective_chat.id
            
            # تسجيل المجموعة الجديدة
            config.group_settings[str(group_id)] = {
                'title': update.effective_chat.title,
                'added_date': datetime.now().isoformat(),
                'member_count': await update.effective_chat.get_member_count()
            }
            config.save()
            
            # إرسال رسالة ترحيب
            welcome_msg = """
🦅 **تم تفعيل بوت الصقر السعودي بنجاح!**

✅ **الميزات المفعلة تلقائياً:**
• نظام الكلمات المحظورة
• الحذف التلقائي للرسائل المخالفة
• الحظر الأبدي للمخالفين المتكررين
• العمل الصامت بدون إشعارات

⚙️ **المتطلبات:**
1. رفع البوت مشرفاً
2. منح صلاحية **حذف الرسائل**
3. منح صلاحية **حظر الأعضاء**

🔧 **ملاحظة:** الإعدادات تتم من قبل المالك فقط
ولا تحتاج لأي إعدادات إضافية.

📞 **للمساعدة:** @Arjoan46789o
"""
            
            await context.bot.send_message(
                chat_id=group_id,
                text=welcome_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # إرسال إشعار للمالك
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"✅ **تم إضافة البوت إلى مجموعة جديدة**\n\n"
                     f"• **المجموعة:** {update.effective_chat.title}\n"
                     f"• **الرابط:** {update.effective_chat.link or 'غير متوفر'}\n"
                     f"• **الأعضاء:** {await update.effective_chat.get_member_count()}\n"
                     f"• **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                     f"📊 **المجموعات النشطة:** {len(config.group_settings)}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            log_operation("BOT_ADDED", group_id, f"Group: {update.effective_chat.title}")

# ==================== التشغيل الرئيسي ====================
def setup_handlers(application: Application):
    """إعداد جميع الـ handlers"""
    
    # أوامر المالك
    application.add_handler(CommandHandler("panel", owner_panel))
    application.add_handler(CommandHandler("addword", add_banned_word))
    application.add_handler(CommandHandler("delword", delete_banned_word))
    application.add_handler(CommandHandler("words", list_banned_words))
    application.add_handler(CommandHandler("banlist", list_banned_users))
    application.add_handler(CommandHandler("silent", toggle_silent_mode))
    application.add_handler(CommandHandler("stats", show_stats))
    
    # أوامر عامة
    application.add_handler(CommandHandler("start", owner_panel))
    application.add_handler(CommandHandler("help", owner_panel))
    
    # معالجات الأحداث
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_chat_member
    ))
    
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        bot_added_to_group
    ))
    
    # معالج الرسائل للكلمات المحظورة
    application.add_handler(MessageHandler(
        filters.TEXT | filters.CAPTION,
        check_message_for_violations
    ))

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    # تحميل الإعدادات
    config.load()
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إعداد الـ handlers
    setup_handlers(application)
    
    # رسالة بدء التشغيل
    logger.info("=" * 60)
    logger.info("🦅 SAUDI FALCON BOT - PROFESSIONAL EDITION")
    logger.info("=" * 60)
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info(f"📊 Blocked Words: {len(config.blocked_words)}")
    logger.info(f"🚫 Global Bans: {len(config.global_banned_users)}")
    logger.info(f"🤖 Silent Mode: {config.silent_mode}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 60)
    print("🦅 BOT STARTED SUCCESSFULLY - PROFESSIONAL MODE")
    print("=" * 60)
    print(f"✅ Blocked Words: {len(config.blocked_words)}")
    print(f"✅ Global Banned Users: {len(config.global_banned_users)}")
    print(f"✅ Silent Mode: {config.silent_mode}")
    print(f"✅ Config File: {CONFIG_FILE}")
    print(f"✅ Log File: {LOG_FILE}")
    print("=" * 60)
    print("\n🔧 **Available Owner Commands:**")
    print("  /panel - Control Panel")
    print("  /addword - Add banned words")
    print("  /delword - Delete banned word")
    print("  /words - List banned words")
    print("  /banlist - List banned users")
    print("  /silent - Toggle silent mode")
    print("  /stats - Detailed statistics")
    print("=" * 60 + "\n")
    
    # تشغيل البوت
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    # تشغيل مع استعادة من الأخطاء
    while True:
        try:
            main()
        except KeyboardInterrupt:
            logger.info("⏹️ تم إيقاف البوت يدوياً")
            break
        except Exception as e:
            logger.error(f"💥 خطأ: {e}")
            logger.info("🔄 إعادة التشغيل خلال 10 ثواني...")
            import time
            time.sleep(10)
