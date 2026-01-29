"""
إعدادات بوت روابط أمازون فقط
"""

# 🔑 المفاتيح الأساسية
BOT_TOKEN = ""  # توكن البوت من @BotFather
GEMINI_API_KEY = ""  # مفتاح Gemini API

# 🏷️ إعدادات Amazon Affiliate
AMAZON_TAG = ""  # ضع Amazon Affiliate tag هنا

# 🌍 روابط أمازون حسب المنطقة
AMAZON_URLS = {
    "global": f"https://www.amazon.com/s?k={{query}}&tag={AMAZON_TAG}",
    "uae": f"https://www.amazon.ae/s?k={{query}}&tag={AMAZON_TAG}",
    "ksa": f"https://www.amazon.sa/s?k={{query}}&tag={AMAZON_TAG}",
    "egypt": f"https://www.amazon.eg/s?k={{query}}&tag={AMAZON_TAG}"
}

# 🔄 إعدادات البوت
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
LOG_LEVEL = "INFO"
