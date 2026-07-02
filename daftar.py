import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
BOT_TOKEN = "8708141323:AAFGEOO3E9-fLh36kmjfn6IQpS6bRKPWOzs"
ADMIN_ID = 8676940332  # <--- O'zingizning Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("qarzlar.db")
    cursor = conn.cursor()
    # Bazaga muddat (muddat) ustunini qo'shamiz
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qarzdorlar (
            user_id INTEGER PRIMARY KEY,
            ism TEXT,
            qarz_miqdori REAL DEFAULT 0,
            buyum TEXT,
            muddat TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- FSM (Holatlar) ---
class QarzState(StatesGroup):
    ism = State()
    user_id = State()
    buyum = State()
    miqdor = State()
    muddat = State()
    change_miqdor = State()

# --- KLAVIATURALAR ---
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi qarzdor qo'shish")],
        [KeyboardButton(text="📝 Qarzni o'zgartirish"), KeyboardButton(text="📋 Ro'yxatni ko'rish")]
    ],
    resize_keyboard=True
)

mijoz_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="💰 Mening qarzim")]],
    resize_keyboard=True
)

# --- AVTOMATIK TEKSHIRUVCHI (MUDDATI O'TGANLARNI ANIQLASH) ---
async def auto_check_debts():
    """Har 1 soatda bazani tekshiradi va muddati o'tgan bo'lsa xabar yuboradi"""
    while True:
        try:
            hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y")
            
            conn = sqlite3.connect("qarzlar.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, ism, qarz_miqdori, buyum, muddat FROM qarzdorlar")
            rows = cursor.fetchall()
            conn.close()
            
            for r in rows:
                uid, ism, miqdor, buyum, muddat = r
                try:
                    # Sanani taqqoslash
                    qarz_sana = datetime.strptime(muddat, "%d.%m.%Y")
                    bugun_sana = datetime.strptime(hozirgi_vaqt, "%d.%m.%Y")
                    
                    if bugun_sana >= qarz_sana:
                        # Mijozga ogohlantirish
                        try:
                            await bot.send_message(
                                uid,
                                f"⚠️ **DIQQAT! Qarzni to'lash muddati tugadi!**\n\n"
                                f"📦 Buyum: {buyum}\n"
                                f"💰 Qarz miqdori: {miqdor} so'm\n"
                                f"📅 To'lash kerak bo'lgan sana: {muddat}\n\n"
                                f"Iltimos, do'konga uchrab qarzni yoping yoki egasi bilan bog'laning!"
                            )
                        except Exception:
                            pass # Agar mijoz botni bloklagan bo'lsa xato bermasligi uchun
                            
                        # Adminga ogohlantirish
                        await bot.send_message(
                            ADMIN_ID,
                            f"🚨 **Muddati o'tgan qarz!**\n\n"
                            f"👤 Qarzdor: {ism} (ID: `{uid}`)\n"
                            f"📦 Buyum: {buyum}\n"
                            f"💰 Summa: {miqdor} so'm\n"
                            f"📅 Muddat: {muddat} da tugagan."
                        )
                except ValueError:
                    continue # Agar sana formati xato kiritilgan bo'lsa o'tkazib yuboradi
                    
        except Exception as e:
            print(f"Tekshirishda xatolik: {e}")
            
        await asyncio.sleep(3600)  # 3600 soniya = 1 soatda bir tekshiradi

# --- START BUYRUG'I ---
@dp.message(F.text == "/start")
async def start_cmd(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Xush kelibsiz, Do'kon egasi! Qarz daftari yangilandi.", reply_markup=admin_menu)
    else:
        await message.answer(
            f"Xush kelibsiz, {message.from_user.full_name}!\n"
            f"Sizning Telegram ID raqamingiz: `{message.from_user.id}`\n\n"
            "⚠️ Qarzingizni bilish uchun ushbu ID raqamni do'kon egasiga aytishingiz kerak.",
            parse_mode="Markdown",
            reply_markup=mijoz_menu
        )

# --- ADMIN: RO'YXATNI KO'RISH ---
@dp.message(F.text == "📋 Ro'yxatni ko'rish")
async def list_debts(message: Message):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect("qarzlar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, ism, qarz_miqdori, buyum, muddat FROM qarzdorlar")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("Hozircha qarzlar ro'yxati bo'sh.")
        return
        
    text = "📋 **Qarzdorlar ro'yxati va muddatlari:**\n\n"
    for r in rows:
        text += f"👤 **{r[1]}** (ID: `{r[0]}`)\n📦 Buyum: {r[3]}\n💰 Qarz: {r[2]} so'm\n📅 Muddat: {r[4]}\n\n"
    await message.answer(text, parse_mode="Markdown")

# --- ADMIN: YANGI QARZDOR QO'SHISH ---
@dp.message(F.text == "➕ Yangi qarzdor qo'shish")
async def add_debtor_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Qarzdorning ismini kiriting:")
    await state.set_state(QarzState.ism)

@dp.message(QarzState.ism)
async def process_ism(message: Message, state: FSMContext):
    await state.update_data(ism=message.text)
    await message.answer("Mijozning Telegram ID raqamini kiriting:")
    await state.set_state(QarzState.user_id)

@dp.message(QarzState.user_id)
async def process_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID faqat raqamlardan iborat bo'lishi kerak!")
        return
    await state.update_data(user_id=int(message.text))
    await message.answer("Olingan buyum nomini kiriting:")
    await state.set_state(QarzState.buyum)

@dp.message(QarzState.buyum)
async def process_buyum(message: Message, state: FSMContext):
    await state.update_data(buyum=message.text)
    await message.answer("Qarz miqdorini kiriting (faqat raqam):")
    await state.set_state(QarzState.miqdor)

@dp.message(QarzState.miqdor)
async def process_miqdor(message: Message, state: FSMContext):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Iltimos, qarzni to'g'ri raqamda kiriting!")
        return
    await state.update_data(miqdor=float(message.text))
    await message.answer("Qarzni qaytarish muddatini kiriting.\nFormat: `kun.oy.yil` (Masalan: `15.07.2026`)", parse_mode="Markdown")
    await state.set_state(QarzState.muddat)

@dp.message(QarzState.muddat)
async def process_muddat(message: Message, state: FSMContext):
    muddat_text = message.text.strip()
    try:
        # Sana formatini tekshirish
        datetime.strptime(muddat_text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Noto'g'ri sana formati! Iltimos, xuddi namunadagidek kiriting: `25.12.2026`")
        return

    data = await state.get_data()
    
    conn = sqlite3.connect("qarzlar.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO qarzdorlar (user_id, ism, qarz_miqdori, buyum, muddat) VALUES (?, ?, ?, ?, ?)",
        (data['user_id'], data['ism'], data['miqdor'], data['buyum'], muddat_text)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Qarzdor va to'lov muddati muvaffaqiyatli saqlandi!", reply_markup=admin_menu)
    
    try:
        await bot.send_message(
            data['user_id'], 
            f"🔔 **Do'kondan bildirishnoma!**\n\nSiz do'kondan qarzga buyum oldingiz.\n"
            f"📦 Buyum: {data['buyum']}\n"
            f"💰 Qarz miqdori: {data['miqdor']} so'm.\n"
            f"📅 Qaytarish muddati: {muddat_text} gacha.\n\n"
            f"Iltimos, o'z vaqtida to'lashni unutmang!"
        )
    except Exception:
        await message.answer("⚠️ Mijoz botni hali ishga tushirmagan, unga xabar yuborilmadi. Lekin bazaga qo'shildi.")
        
    await state.clear()

# --- ADMIN: QARZNI O'ZGARTIRISH (YANGILASH) ---
@dp.message(F.text == "📝 Qarzni o'zgartirish")
async def update_debt_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Qarzi o'zgaradigan mijozning Telegram ID raqamini kiriting:")
    await state.set_state(QarzState.change_miqdor)

@dp.message(QarzState.change_miqdor)
async def process_change(message: Message, state: FSMContext):
    try:
        uid, yangi_summa = message.text.split()
        uid = int(uid)
        yangi_summa = float(yangi_summa)
    except ValueError:
        await message.answer("Xato format! Quyidagicha yozing:\n`MijozID YangiSumma`\n\nMasalan: `12345678 50000`", parse_mode="Markdown")
        return

    conn = sqlite3.connect("qarzlar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ism, buyum FROM qarzdorlar WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    
    if not row:
        await message.answer("❌ Bu ID dagi qarzdor topilmadi!")
        conn.close()
        await state.clear()
        return

    if yangi_summa <= 0:
        cursor.execute("DELETE FROM qarzdorlar WHERE user_id = ?", (uid,))
        text_admin = f"✅ {row[0]}ning qarz daftari yopildi (O'chirildi)."
        text_mijoz = f"🎉 Tabriklaymiz! Do'kondagi qarzlaringiz to'liq yopildi. Rahmat!"
    else:
        cursor.execute("UPDATE qarzdorlar SET qarz_miqdori = ? WHERE user_id = ?", (yangi_summa, uid))
        text_admin = f"✅ {row[0]}ning yangi qarzi: {yangi_summa} so'm qilib belgilandi."
        text_mijoz = f"📝 **Qarz miqdori o'zgardi!**\n\nSizning do'kondagi qarz miqdoringiz yangilandi:\n💰 Qolgan qarz: {yangi_summa} so'm."

    conn.commit()
    conn.close()
    
    await message.answer(text_admin, reply_markup=admin_menu)
    try:
        await bot.send_message(uid, text_mijoz)
    except Exception:
        pass
    await state.clear()

# --- MIJOZ: O'Z QARZINI TEKSHIRISH ---
@dp.message(F.text == "💰 Mening qarzim")
async def check_my_debt(message: Message):
    conn = sqlite3.connect("qarzlar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT qarz_miqdori, buyum, muddat FROM qarzdorlar WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        await message.answer(f"📊 **Sizning qarz holatingiz:**\n\n📦 Olingan buyum: {row[1]}\n💰 Qolgan summa: {row[0]} so'm\n📅 Qaytarish muddati: {row[2]}")
    else:
        await message.answer("Sizning do'kondan qarzingiz yo'q. Rahmat! 😊")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    # Avtomatik tekshirish funksiyasini fon rejimi (background task) sifatida ishga tushiramiz
    asyncio.create_task(auto_check_debts())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())