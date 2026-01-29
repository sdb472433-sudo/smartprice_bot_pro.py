"""
بوت بسيط: ياخذ صورة → يرسل رابط أمازون
"""
import logging
import urllib.parse
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image
import tempfile
import os

# استيراد الإعدادات
from config import BOT_TOKEN, GEMINI_API_KEY, AMAZON_URLS, AMAZON_TAG

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# تخزين بيانات المستخدمين
user_states = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت"""
    
    # أزرار اختيار اللغة
    keyboard = [
        [
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 *Welcome to Amazon Link Bot!*\n\n"
        "📸 *How to use:*\n"
        "1. Choose your language\n"
        "2. Send me a product photo\n"
        "3. I'll send you an Amazon link\n\n"
        "🛒 *Only Amazon links*\n"
        "👇 *Choose your language:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار اللغة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    
    # حفظ اللغة
    user_states[user_id] = {"lang": lang}
    
    # رسائل حسب اللغة
    messages = {
        "en": "✅ *English selected!*\n\n📸 Now send me a photo of any product.\n\nI'll analyze it and send you an Amazon link.",
        "ar": "✅ *تم اختيار العربية!*\n\n📸 الآن أرسل لي صورة أي منتج.\n\nسأحللها وأرسل لك رابط أمازون.",
        "fr": "✅ *Français sélectionné!*\n\n📸 Maintenant envoyez-moi une photo de n'importe quel produit.\n\nJe vais l'analyser et vous envoyer un lien Amazon."
    }
    
    await query.edit_message_text(
        messages.get(lang, messages["en"]),
        parse_mode="Markdown"
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور"""
    user_id = update.effective_user.id
    
    # التحقق من اللغة
    if user_id not in user_states:
        await update.message.reply_text(
            "Please choose language first / اختر اللغة أولاً / Veuillez d'abord choisir la langue"
        )
        return
    
    lang = user_states[user_id]["lang"]
    
    # رسالة الانتظار
    wait_messages = {
        "en": "🔍 *Analyzing photo...*",
        "ar": "🔍 *جاري تحليل الصورة...*",
        "fr": "🔍 *Analyse de la photo...*"
    }
    
    wait_msg = await update.message.reply_text(
        wait_messages.get(lang, wait_messages["en"]),
        parse_mode="Markdown"
    )
    
    try:
        # تحميل الصورة
        photo = await update.message.photo[-1].get_file()
        
        # حفظ مؤقت
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            await photo.download_to_drive(tmp.name)
            
            # تحليل مع Gemini
            product_info = await analyze_photo(tmp.name, lang)
            
            # إنشاء رابط أمازون
            amazon_link = create_amazon_link(product_info)
            
            # إرسال النتيجة
            await send_result(update, product_info, amazon_link, lang)
            
            # تنظيف
            os.unlink(tmp.name)
        
        await wait_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
        error_msgs = {
            "en": "❌ Error processing photo. Please try again.",
            "ar": "❌ خطأ في معالجة الصورة. حاول مرة أخرى.",
            "fr": "❌ Erreur de traitement de la photo. Veuillez réessayer."
        }
        
        await wait_msg.delete()
        await update.message.reply_text(error_msgs.get(lang, error_msgs["en"]))

async def analyze_photo(image_path, lang):
    """تحليل الصورة باستخدام Gemini"""
    try:
        img = Image.open(image_path)
        
        # نصوص التحليل حسب اللغة
        prompts = {
            "en": "What product is in this image? Give me only the product name.",
            "ar": "ما هو المنتج في هذه الصورة؟ أعطني اسم المنتج فقط.",
            "fr": "Quel produit est dans cette image ? Donnez-moi seulement le nom du produit."
        }
        
        prompt = prompts.get(lang, prompts["en"])
        response = model.generate_content([prompt, img])
        
        # تنظيف الاسم
        product_name = response.text.strip()
        
        # إزالة أي جمل زائدة
        if ":" in product_name:
            product_name = product_name.split(":")[-1].strip()
        
        return product_name[:200]  # تحديد الطول
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return "product"

def create_amazon_link(product_name):
    """إنشاء رابط أمازون"""
    # ترميث اسم المنتج
    encoded_name = urllib.parse.quote(product_name)
    
    # استخدام الرابط العام
    return AMAZON_URLS["global"].format(query=encoded_name)

async def send_result(update, product_name, amazon_link, lang):
    """إرسال النتيجة للمستخدم"""
    
    # تحضير النصوص حسب اللغة
    if lang == "ar":
        text = f"""
✅ *تم تحليل الصورة*

🔍 *المنتج:* {product_name}

🛒 *رابط أمازون:*
{amazon_link}

📎 *ملاحظة:* هذا رابط أمازون مباشر
        """
        
        buttons = [
            [InlineKeyboardButton("🛒 افتح أمازون", url=amazon_link)],
            [InlineKeyboardButton("📸 صورة أخرى", callback_data="another")]
        ]
        
    elif lang == "fr":
        text = f"""
✅ *Photo analysée*

🔍 *Produit:* {product_name}

🛒 *Lien Amazon:*
{amazon_link}

📎 *Note:* Ceci est un lien Amazon direct
        """
        
        buttons = [
            [InlineKeyboardButton("🛒 Ouvrir Amazon", url=amazon_link)],
            [InlineKeyboardButton("📸 Autre photo", callback_data="another")]
        ]
        
    else:  # English
        text = f"""
✅ *Photo analyzed*

🔍 *Product:* {product_name}

🛒 *Amazon link:*
{amazon_link}

📎 *Note:* This is a direct Amazon link
        """
        
        buttons = [
            [InlineKeyboardButton("🛒 Open Amazon", url=amazon_link)],
            [InlineKeyboardButton("📸 Another photo", callback_data="another")]
        ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
        disable_web_page_preview=False
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "another":
        user_id = query.from_user.id
        lang = user_states.get(user_id, {}).get("lang", "en")
        
        messages = {
            "en": "📸 Send another product photo",
            "ar": "📸 أرسل صورة منتج أخرى",
            "fr": "📸 Envoyer une autre photo de produit"
        }
        
        await query.edit_message_text(messages.get(lang, messages["en"]))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    help_text = """
*🤖 Amazon Link Bot - Help*

*English:*
/start - Start bot and choose language
/help - Show this message

*العربية:*
/start - بدء البوت واختيار اللغة
/help - عرض رسالة المساعدة

*Français:*
/start - Démarrer le bot et choisir la langue
/help - Afficher ce message

*📸 How to use:*
1. Send /start
2. Choose language
3. Send product photo
4. Get Amazon link

*🛒 Only Amazon:*
This bot only sends Amazon affiliate links.
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def direct_link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر للحصول على رابط مباشر"""
    if not context.args:
        await update.message.reply_text(
            "Usage: /link product name\n"
            "مثال: /link iphone 15"
        )
        return
    
    product_name = " ".join(context.args)
    amazon_link = create_amazon_link(product_name)
    
    await update.message.reply_text(
        f"🛒 *Amazon link for:* {product_name}\n\n{amazon_link}",
        parse_mode="Markdown",
        disable_web_page_preview=False
    )

def main():
    """الدالة الرئيسية"""
    # التحقق من المفاتيح
    if not BOT_TOKEN or BOT_TOKEN == "":
        print("❌ Error: BOT_TOKEN is empty in config.py")
        return
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "":
        print("❌ Error: GEMINI_API_KEY is empty in config.py")
        return
    
    if not AMAZON_TAG or AMAZON_TAG == "":
        print("⚠️ Warning: AMAZON_TAG is empty. Using default.")
    
    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("link", direct_link_command))
    
    app.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    # بدء البوت
    print("=" * 50)
    print("🤖 Amazon Link Bot Started")
    print("📸 Photo → 🔗 Amazon Link")
    print("🌍 Languages: EN, AR, FR")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
