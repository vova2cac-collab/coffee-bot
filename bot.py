import asyncio
import logging
import traceback
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, BOT_TOKEN, MENU, WORK_END, WORK_START

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


def _generate_times():
    times = []
    start_h, start_m = map(int, WORK_START.split(":"))
    end_h, end_m = map(int, WORK_END.split(":"))
    current = start_h * 60 + start_m
    end = end_h * 60 + end_m
    while current <= end:
        h = current // 60
        m = current % 60
        times.append(f"{h:02d}:{m:02d}")
        current += 15
    return times

ALL_TIMES = _generate_times()
TIMES_PER_PAGE = 20


class OrderStates(StatesGroup):
    in_cart = State()
    choosing_time = State()
    entering_name = State()
    confirming = State()


def format_cart(cart: list) -> str:
    if not cart:
        return "Корзина пуста"
    lines = []
    total = 0
    for i, item in enumerate(cart, 1):
        lines.append(f"{i}. {item['emoji']} {item['name']} — {item['price']}₽")
        total += item["price"]
    lines.append(f"\n<b>Итого: {total}₽</b>")
    return "\n".join(lines)


def get_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(
        text=f"{item['emoji']} {item['name']} — {item['price']}₽",
        callback_data=f"add:{key}"
    )] for key, item in MENU.items()]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cart_keyboard(cart: list) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="➕ Добавить ещё", callback_data="show_menu")]]
    if cart:
        buttons.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])
        buttons.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    start = page * TIMES_PER_PAGE
    end = start + TIMES_PER_PAGE
    page_times = ALL_TIMES[start:end]
    buttons = []
    row = []
    for t in page_times:
        row.append(InlineKeyboardButton(text=t, callback_data=f"time|{t}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« Ранее", callback_data=f"timepage|{page-1}"))
    if end < len(ALL_TIMES):
        nav.append(InlineKeyboardButton(text="Позже »", callback_data=f"timepage|{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="« Назад в корзину", callback_data="back_to_cart")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
    ]])


async def safe_edit(message, text, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"safe_edit fail: {e}")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    try:
        await state.clear()
        await state.update_data(cart=[])
        await state.set_state(OrderStates.in_cart)
        text = (
            "☕ <b>Добро пожаловать в Кофейню!</b>\n\n"
            f"Работаем с <b>{WORK_START}</b> до <b>{WORK_END}</b>.\n\n"
            "Выберите позиции — можно несколько.\n"
            "Когда закончите — «Оформить заказ»."
        )
        await message.answer(text, reply_markup=get_menu_keyboard(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"start error: {e}\n{traceback.format_exc()}")


@router.callback_query(F.data == "show_menu")
async def show_menu(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(OrderStates.in_cart)
        await safe_edit(callback.message, "📋 <b>Меню</b>\nВыберите, что добавить:", get_menu_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"show_menu: {e}")
        await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    try:
        key = callback.data.split(":")[1]
        item = MENU.get(key)
        if not item:
            await callback.answer("Нет позиции", show_alert=True)
            return
        data = await state.get_data()
        cart = list(data.get("cart") or [])
        cart.append({"key": key, "name": item["name"], "price": item["price"], "emoji": item["emoji"]})
        await state.update_data(cart=cart)
        await state.set_state(OrderStates.in_cart)
        text = (
            f"✅ Добавлено: <b>{item['emoji']} {item['name']}</b>\n\n"
            f"<b>Корзина:</b>\n{format_cart(cart)}\n\n"
            "Добавьте ещё или оформите заказ."
        )
        await safe_edit(callback.message, text, get_cart_keyboard(cart))
        await callback.answer(f"+ {item['name']}")
    except Exception as e:
        logger.error(f"add_to_cart: {e}\n{traceback.format_exc()}")
        await callback.answer("Ошибка", show_alert=True)


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    try:
        await state.update_data(cart=[])
        await state.set_state(OrderStates.in_cart)
        await safe_edit(callback.message, "🗑 Корзина очищена.\nВыберите позиции:", get_menu_keyboard())
        await callback.answer("Очищено")
    except Exception as e:
        logger.error(f"clear_cart: {e}")
        await callback.answer()


@router.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        cart = data.get("cart") or []
        await state.set_state(OrderStates.in_cart)
        text = f"<b>Корзина:</b>\n{format_cart(cart)}\n\nДобавьте ещё или оформите."
        await safe_edit(callback.message, text, get_cart_keyboard(cart))
        await callback.answer()
    except Exception as e:
        logger.error(f"back_to_cart: {e}")
        await callback.answer()


@router.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        cart = data.get("cart") or []
        if not cart:
            await callback.answer("Корзина пуста!", show_alert=True)
            return
        await state.set_state(OrderStates.choosing_time)
        text = f"<b>Заказ:</b>\n{format_cart(cart)}\n\n🕐 На какое время?\n({WORK_START}–{WORK_END})"
        await safe_edit(callback.message, text, get_time_keyboard(0))
        await callback.answer()
    except Exception as e:
        logger.error(f"checkout: {e}\n{traceback.format_exc()}")
        await callback.answer("Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("timepage|"))
async def time_page(callback: CallbackQuery, state: FSMContext):
    try:
        page = int(callback.data.split("|")[1])
        data = await state.get_data()
        cart = data.get("cart") or []
        text = f"<b>Заказ:</b>\n{format_cart(cart)}\n\n🕐 Время (стр. {page+1})"
        await safe_edit(callback.message, text, get_time_keyboard(page))
        await callback.answer()
    except Exception as e:
        logger.error(f"time_page: {e}")
        await callback.answer()


@router.callback_query(F.data.startswith("time|"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    try:
        order_time = callback.data.split("|", 1)[1]
        await state.update_data(order_time=order_time)
        await state.set_state(OrderStates.entering_name)
        await safe_edit(callback.message, f"🕐 Время: <b>{order_time}</b>\n\n✏️ Напишите ваше <b>имя</b>:")
        await callback.answer()
    except Exception as e:
        logger.error(f"choose_time: {e}\n{traceback.format_exc()}")
        await callback.answer("Ошибка", show_alert=True)


@router.message(OrderStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    try:
        name = (message.text or "").strip()
        if len(name) < 2:
            await message.answer("Имя слишком короткое. Напишите ещё раз:")
            return
        await state.update_data(customer_name=name)
        data = await state.get_data()
        cart = data.get("cart") or []
        order_time = data.get("order_time", "?")
        if not cart:
            await message.answer("Корзина пуста. /start")
            await state.clear()
            return
        await state.set_state(OrderStates.confirming)
        text = (
            "📝 <b>Проверьте заказ:</b>\n\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"🕐 Время: <b>{order_time}</b>\n\n"
            f"{format_cart(cart)}\n\nВсё верно?"
        )
        await message.answer(text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"enter_name: {e}\n{traceback.format_exc()}")
        await message.answer("Ошибка. Нажмите /start")
        await state.clear()


@router.callback_query(F.data == "confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        user = callback.from_user
        cart = data.get("cart") or []
        order_time = data.get("order_time")
        name = data.get("customer_name")

        if not cart or not order_time or not name:
            await safe_edit(callback.message, "⚠️ Данные устарели. /start")
            await state.clear()
            await callback.answer()
            return

        username = f"@{user.username}" if user.username else "нет username"
        total = sum(i["price"] for i in cart)
        items_text = "\n".join(f"• {i['emoji']} {i['name']} — {i['price']}₽" for i in cart)

        order_text = (
            "🆕 <b>НОВЫЙ ЗАКАЗ</b>\n\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📱 Telegram: {username}\n"
            f"🕐 Ко времени: <b>{order_time}</b>\n\n"
            f"{items_text}\n\n"
            f"<b>Итого: {total}₽</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(ADMIN_CHAT_ID, order_text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"group send: {e}")

        await safe_edit(
            callback.message,
            "✅ <b>Заказ принят!</b>\n\n"
            f"👤 {name}\n🕐 <b>{order_time}</b>\n\n"
            f"{format_cart(cart)}\n\nЖдём вас! ☕\n\nНовый заказ — /start"
        )
        await callback.answer("Готово!")
    except Exception as e:
        logger.error(f"confirm: {e}\n{traceback.format_exc()}")
        await callback.answer("Ошибка", show_alert=True)
    finally:
        try:
            await state.clear()
        except Exception:
            pass


@router.callback_query(F.data == "cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await safe_edit(callback.message, "❌ Отменено.\n\n/start — новый заказ")
        await callback.answer()
    except Exception as e:
        logger.error(f"cancel: {e}")
        await callback.answer()


@router.message(Command("chatid"))
async def get_chat_id(message: Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>", parse_mode="HTML")


@router.message()
async def any_message(message: Message, state: FSMContext):
    try:
        current = await state.get_state()
        if current == OrderStates.entering_name.state:
            return
        await message.answer("Нажмите /start, чтобы сделать заказ ☕")
    except Exception as e:
        logger.error(f"any_message: {e}")


async def main():
    logger.info("=== БОТ ЗАПУСКАЕТСЯ ===")
    while True:
        try:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception:
                pass
            logger.info("Polling started")
            await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
        except Exception as e:
            logger.error(f"Polling crashed: {e}\n{traceback.format_exc()}")
            logger.info("Перезапуск через 3 секунды...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
