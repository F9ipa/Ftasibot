import logging
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import concurrent.futures

# التوكن الخاص بك
TOKEN = "7408760983:AAGroYZzwSx6Ly8LwB3fYtZWcmLiN2gkK2U"

# قائمة رموز تاسي
TASI_SYMBOLS = [
    '1010.SR', '1020.SR', '1030.SR', '1050.SR', '1060.SR', '1080.SR', '1111.SR', '1120.SR', '1140.SR', '1150.SR',
    '1180.SR', '1182.SR', '1183.SR', '1201.SR', '1202.SR', '1210.SR', '1211.SR', '1212.SR', '1213.SR', '1214.SR',
    '1301.SR', '1304.SR', '1320.SR', '1321.SR', '1322.SR', '1810.SR', '1830.SR', '1831.SR', '1832.SR', '1833.SR',
    '2001.SR', '2002.SR', '2010.SR', '2020.SR', '2030.SR', '2040.SR', '2050.SR', '2060.SR', '2070.SR', '2080.SR',
    '2081.SR', '2082.SR', '2083.SR', '2090.SR', '2100.SR', '2110.SR', '2120.SR', '2130.SR', '2140.SR', '2150.SR',
    '2160.SR', '2170.SR', '2180.SR', '2190.SR', '2200.SR', '2210.SR', '2220.SR', '2222.SR', '2223.SR', '2230.SR',
    '2240.SR', '2250.SR', '2270.SR', '2280.SR', '2281.SR', '2282.SR', '2283.SR', '2290.SR', '2300.SR', '2310.SR',
    '2320.SR', '2330.SR', '2340.SR', '2350.SR', '2360.SR', '2370.SR', '2380.SR', '2381.SR', '2382.SR', '3001.SR',
    '3002.SR', '3003.SR', '3004.SR', '3005.SR', '3007.SR', '3008.SR', '3010.SR', '3020.SR', '3030.SR', '3040.SR',
    '3050.SR', '3060.SR', '3080.SR', '3090.SR', '3091.SR', '4001.SR', '4002.SR', '4003.SR', '4004.SR', '4005.SR',
    '4006.SR', '4007.SR', '4008.SR', '4009.SR', '4010.SR', '4011.SR', '4012.SR', '4013.SR', '4014.SR', '4015.SR',
    '4020.SR', '4030.SR', '4031.SR', '4040.SR', '4050.SR', '4061.SR', '4071.SR', '4072.SR', '4080.SR', '4081.SR',
    '4082.SR', '4090.SR', '4100.SR', '4110.SR', '4130.SR', '4140.SR', '4141.SR', '4142.SR', '4150.SR', '4160.SR',
    '4161.SR', '4162.SR', '4163.SR', '4164.SR', '4170.SR', '4180.SR', '4190.SR', '4191.SR', '4192.SR', '4200.SR',
    '4210.SR', '4220.SR', '4230.SR', '4240.SR', '4250.SR', '4260.SR', '4270.SR', '4280.SR', '4290.SR', '4291.SR',
    '4292.SR', '4300.SR', '4310.SR', '4320.SR', '4321.SR', '4322.SR', '4323.SR', '4330.SR', '4331.SR', '4332.SR',
    '4333.SR', '4335.SR', '4336.SR', '4340.SR', '4342.SR', '4344.SR', '4345.SR', '4346.SR', '4347.SR', '4348.SR',
    '6001.SR', '6002.SR', '6004.SR', '6010.SR', '6011.SR', '6012.SR', '6013.SR', '6014.SR', '6015.SR', '6020.SR',
    '6040.SR', '6050.SR', '6060.SR', '6070.SR', '6090.SR', '7010.SR', '7020.SR', '7030.SR', '7040.SR', '7201.SR',
    '7202.SR', '7203.SR', '7204.SR', '8010.SR', '8012.SR', '8020.SR', '8030.SR', '8040.SR', '8050.SR', '8060.SR',
    '8070.SR', '8100.SR', '8120.SR', '8150.SR', '8160.SR', '8170.SR', '8180.SR', '8190.SR', '8200.SR', '8210.SR',
    '8230.SR', '8240.SR', '8250.SR', '8260.SR', '8270.SR', '8280.SR', '8300.SR', '8310.SR', '8311.SR', '8312.SR'
]

# دالة تحويل البيانات إلى شموع Heikin-Ashi
def get_heikin_ashi(df):
    ha_df = df.copy()
    # Close = (Open + High + Low + Close) / 4
    ha_df['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Open = (Open_prev + Close_prev) / 2
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_df['Close'].iloc[i-1]) / 2
    ha_df['Open'] = ha_open
    
    # High = Max(High, Open, Close)
    ha_df['High'] = ha_df[['High', 'Open', 'Close']].max(axis=1)
    # Low = Min(Low, Open, Close)
    ha_df['Low'] = ha_df[['Low', 'Open', 'Close']].min(axis=1)
    
    return ha_df

# منطق مؤشر WaveTrend [LazyBear]
def calculate_wavetrend(df):
    if len(df) < 30: return None, None
    # استخدام بيانات Heikin-Ashi بدلاً من العادية
    ha_df = get_heikin_ashi(df)
    
    ap = (ha_df['High'] + ha_df['Low'] + ha_df['Close']) / 3
    esa = ap.ewm(span=10, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=10, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d)
    wt1 = ci.ewm(span=21, adjust=False).mean()
    wt2 = wt1.rolling(window=4).mean()
    return wt1, wt2

def get_signals():
    pos, neg = [], []
    def scan(sym):
        try:
            # الفاصل شهري interval="1mo"
            df = yf.download(sym, period="5y", interval="1mo", progress=False)
            if df.empty or len(df) < 10: return
            
            wt1, wt2 = calculate_wavetrend(df)
            if wt1 is None: return
            
            c1, p1 = wt1.iloc[-1], wt1.iloc[-2]
            c2, p2 = wt2.iloc[-1], wt2.iloc[-2]
            
            name = sym.replace(".SR", "")
            current_price = f"{df['Close'].iloc[-1]:.2f}"
            
            # تقاطع إيجابي (دخول)
            if p1 <= p2 and c1 > c2:
                pos.append(f"🟢 {name} - السعر: {current_price}")
            # تقاطع سلبي (خروج)
            elif p1 >= p2 and c1 < c2:
                neg.append(f"🔴 {name} - السعر: {current_price}")
        except Exception: pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        ex.map(scan, TASI_SYMBOLS)
    
    return sorted(pos), sorted(neg)

# واجهة البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📈 استخراج الإيجابية (دخول)", callback_data='pos')],
        [InlineKeyboardButton("📉 استخراج السلبية (خروج)", callback_data='neg')]
    ]
    await update.message.reply_text(
        "📊 **بوت فحص تاسي - WaveTrend Heikin-Ashi**\n\n"
        "• الفاصل: شهري 🗓\n"
        "• الشموع: هايكين آشي 🕯\n"
        "• المصدر: ياهو فاينانس 📡\n\n"
        "اختر العملية المطلوبة:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    if choice == 'main':
        kb = [[InlineKeyboardButton("📈 استخراج الإيجابية", callback_data='pos')],
              [InlineKeyboardButton("📉 استخراج السلبية", callback_data='neg')]]
        await query.edit_message_text("اختر الفلتر المطلوب (Heikin-Ashi):", reply_markup=InlineKeyboardMarkup(kb))
        return

    await query.edit_message_text("⏳ جاري تحليل السوق السعودي بالكامل... فضلاً انتظر.")
    
    pos, neg = get_signals()
    
    if choice == 'pos':
        title = "✅ **الأسهم الإيجابية (تقاطع دخول شهري):**"
        results = pos if pos else ["لا توجد تقاطعات إيجابية حالياً."]
    else:
        title = "❌ **الأسهم السلبية (تقاطع خروج شهري):**"
        results = neg if neg else ["لا توجد تقاطعات سلبية حالياً."]
    
    message = f"{title}\n\n" + "\n".join(results)
    
    # تقسيم الرسالة إذا كانت طويلة جداً
    if len(message) > 4000:
        message = message[:4000] + "\n...(القائمة طويلة)"
    
    kb = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data='main')]]
    await query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    
    print("البوت يعمل بنجاح...")
    application.run_polling()
