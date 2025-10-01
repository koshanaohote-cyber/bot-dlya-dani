import logging
import json
import os
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота от @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Файл для хранения данных
DATA_FILE = "user_data.json"

# Список дел по умолчанию
DEFAULT_TASKS = [
    "качалочка",
    "20 минут уборки",
    "не заходить в пасьян",
    "не играть в ДИПРОК СТАЛКРАФТ И МИНИ ИГРЫ ВК",

]

# Список санкций (можно настроить под себя)
SANCTIONS = [
    "штраф 100 рублей 89050375820 озон банк",
    
    "штраф 200 рублей 89050375820 озон банк",
    
    "штраф 50 рублей 89050375820 озон банк",
    
    "штраф 30 рублей 89059375820 озон банк",

    "штраф 150 рублей 89050375820 озон банк",


]


class HabitTrackerBot:
    def __init__(self):
        self.user_data = self.load_data()

    def load_data(self):
        """Загружаем данные пользователей из файла"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_data(self):
        """Сохраняем данные пользователей в файл"""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")

    def get_user_tasks(self, user_id):
        """Получаем или создаем задачи для пользователя"""
        user_id = str(user_id)

        if user_id not in self.user_data:
            # Создаем нового пользователя
            self.user_data[user_id] = {
                'tasks': {task: False for task in DEFAULT_TASKS},
                'last_reset': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'sanctions_count': 0,
                'total_fails': 0
            }
            self.save_data()

        # Проверяем, нужно ли сбросить задачи на новый день
        self.check_daily_reset(user_id)

        return self.user_data[user_id]['tasks']

    def check_daily_reset(self, user_id):
        """Сбрасываем задачи на новый день"""
        user_id = str(user_id)
        user = self.user_data[user_id]
        last_reset = datetime.fromisoformat(user['last_reset'])
        now = datetime.now()

        # Если прошло больше 24 часов - сбрасываем все задачи
        if now - last_reset > timedelta(hours=24):
            user['tasks'] = {task: False for task in DEFAULT_TASKS}
            user['last_reset'] = now.isoformat()
            user['streak'] = user.get('streak', 0) + 1  # Увеличиваем счетчик дней
            user['sanctions_count'] = 0  # Сбрасываем счетчик санкций за день
            self.save_data()

    def get_random_sanction(self):
        """Возвращает случайную санкцию"""
        return random.choice(SANCTIONS)

    def record_fail(self, user_id):
        """Записываем провал и возвращаем санкцию"""
        user_id = str(user_id)
        if user_id in self.user_data:
            self.user_data[user_id]['sanctions_count'] = self.user_data[user_id].get('sanctions_count', 0) + 1
            self.user_data[user_id]['total_fails'] = self.user_data[user_id].get('total_fails', 0) + 1
            self.save_data()

        return self.get_random_sanction()

    def get_progress_message(self, tasks, user_id=None):
        """Создаем сообщение с прогрессом"""
        total = len(tasks)
        completed = sum(1 for task in tasks.values() if task)
        percentage = (completed / total) * 100 if total > 0 else 0

        message = f"📊 **Сделал сегодня:**\n"
        message += f"✅ Выполнено: {completed}/{total} ({percentage:.1f}%)\n"

        # Добавляем информацию о санкциях, если передан user_id
        if user_id and str(user_id) in self.user_data:
            sanctions_today = self.user_data[str(user_id)].get('sanctions_count', 0)
            message += f" САНКЦИИ: {sanctions_today}\n"

        message += "\n"

        for task, is_done in tasks.items():
            status = "🥰" if is_done else "😑"
            message += f"{status} {task}\n"

        return message

    def create_keyboard(self, tasks):
        """Создаем клавиатуру с кнопками"""
        keyboard = []

        for task, is_done in tasks.items():
            button_text = f"🥰 {task}" if is_done else f"😑 {task}"
            callback_data = f"toggle_{task}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Добавляем дополнительные кнопки
        keyboard.append([
            InlineKeyboardButton("🔄 Сбросить все", callback_data="reset_all"),
            InlineKeyboardButton("😾 Не сделал", callback_data="show_sanctions")
        ])

        keyboard.append([
            InlineKeyboardButton("Отчет!", callback_data="show_stats")
        ])

        return InlineKeyboardMarkup(keyboard)

    def create_sanctions_keyboard(self):
        """Создаем клавиатуру для раздела санкций"""
        keyboard = [
            [InlineKeyboardButton("😈Бог решит твою судьбу", callback_data="get_sanction")],
            [InlineKeyboardButton("😈😈 Список всех санкций", callback_data="show_all_sanctions")],
            [InlineKeyboardButton("🔙 камбэк", callback_data="back_to_tasks")]
        ]
        return InlineKeyboardMarkup(keyboard)


# Создаем экземпляр бота
bot_manager = HabitTrackerBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id

    # Приветственное сообщение
    welcome_text = f"""
Здравия желаю, товарищ {user.first_name}! 👋

Я тупой бот которого написали чтобы ты тыкал кнопки и не лежал на диванчике весь день:)
Но иногда можно позволить себе поблажечку, ведь катя тоже хочет кушать🥺

Правила просты:
- Жми кнопку с заданием, если сделал
- Не ври!!!
- Данные автоматически сбрасываются каждые 24 часа

Удачи! 🥰🥰🥰
    """

    # Получаем задачи пользователя
    tasks = bot_manager.get_user_tasks(user_id)

    # Отправляем сообщение с клавиатурой
    await update.message.reply_text(
        welcome_text,
        reply_markup=bot_manager.create_keyboard(tasks),
        parse_mode='Markdown'
    )


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()  # Подтверждаем нажатие

    # Получаем текущие задачи пользователя
    tasks = bot_manager.get_user_tasks(user_id)

    if data.startswith("toggle_"):
        # Переключаем статус задачи
        task_name = data[7:]  # Убираем "toggle_" из callback_data
        if task_name in tasks:
            tasks[task_name] = not tasks[task_name]
            bot_manager.save_data()

        # Обновляем сообщение
        message = bot_manager.get_progress_message(tasks, user_id)
        await query.edit_message_text(
            text=message,
            reply_markup=bot_manager.create_keyboard(tasks),
            parse_mode='Markdown'
        )

    elif data == "reset_all":
        # Сбрасываем все задачи
        for task in tasks:
            tasks[task] = False
        bot_manager.save_data()

        message = bot_manager.get_progress_message(tasks, user_id)
        await query.edit_message_text(
            text=message,
            reply_markup=bot_manager.create_keyboard(tasks),
            parse_mode='Markdown'
        )

    elif data == "show_sanctions":
        # Показываем раздел с санкциями
        await show_sanctions_section(update, context)

    elif data == "get_sanction":
        # Выдаем случайную санкцию
        sanction = bot_manager.record_fail(user_id)
        sanction_message = f"""
😔 **О нет!**

⚖️ **твое наказание:**
{sanction}

        """

        await query.edit_message_text(
            text=sanction_message,
            reply_markup=bot_manager.create_sanctions_keyboard(),
            parse_mode='Markdown'
        )

    elif data == "show_all_sanctions":
        # Показываем все возможные санкции
        sanctions_list = " **Все возможные санкции:**\n\n"
        for i, sanction in enumerate(SANCTIONS, 1):
            sanctions_list += f"{i}. {sanction}\n"

        await query.edit_message_text(
            text=sanctions_list,
            reply_markup=bot_manager.create_sanctions_keyboard(),
            parse_mode='Markdown'
        )

    elif data == "back_to_tasks":
        # Возвращаемся к задачам
        message = bot_manager.get_progress_message(tasks, user_id)
        await query.edit_message_text(
            text=message,
            reply_markup=bot_manager.create_keyboard(tasks),
            parse_mode='Markdown'
        )

    elif data == "show_stats":
        # Показываем статистику
        await show_statistics(update, context)


async def show_sanctions_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает раздел с санкциями"""
    query = update.callback_query
    user_id = query.from_user.id

    sanctions_info = """
😔 **Раздел санкций**

Кормим катю

🎲 **«Бог решит твою судьбу»** - случайная санкция за пропущенную задачу
📋 **«Список всех санкций»** - посмотреть все возможные санкции

    """

    await query.edit_message_text(
        text=sanctions_info,
        reply_markup=bot_manager.create_sanctions_keyboard(),
        parse_mode='Markdown'
    )


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику пользователя"""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = bot_manager.user_data.get(str(user_id), {})

    tasks = user_data.get('tasks', {})
    completed = sum(1 for task in tasks.values() if task)
    total = len(tasks)
    streak = user_data.get('streak', 0)
    total_fails = user_data.get('total_fails', 0)
    sanctions_today = user_data.get('sanctions_count', 0)

    stats_text = f"""
📈 **Сводный отчет:**

🐱 **Сегодня:** {completed}/{total} выполнено
🐱 **Проебы за сегодня:** {sanctions_today}
🐱 **Дней без проебов:** {streak} дней подряд
🐱 **Всего проебов:** {total_fails}

Продолжай в том же духе, Данечка❤️
    """

    tasks = bot_manager.get_user_tasks(user_id)
    await query.edit_message_text(
        text=stats_text,
        reply_markup=bot_manager.create_keyboard(tasks),
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """
🤖 **Команды бота:**

/start - Начать работу с трекером
/help - Показать эту справку
/today - Показать задачи на сегодня

    """

    await update.message.reply_text(help_text)


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает задачи на сегодня"""
    user_id = update.effective_user.id
    tasks = bot_manager.get_user_tasks(user_id)

    message = bot_manager.get_progress_message(tasks, user_id)
    await update.message.reply_text(
        text=message,
        reply_markup=bot_manager.create_keyboard(tasks),
        parse_mode='Markdown'
    )


def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", show_today))
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Запускаем бота
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()


