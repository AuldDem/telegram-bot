import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Initialize database connection
conn = sqlite3.connect('glossary.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables for words, meanings, and admin tracking
cursor.execute('''CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS meanings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL,
    meaning TEXT NOT NULL,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY(word_id) REFERENCES words(id)
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL
)''')

# Commit changes
conn.commit()

# Operator ID
operator_id = 2040196277

# Helper function to check admin status
def is_admin(user_id):
    cursor.execute("SELECT * FROM admins WHERE telegram_id=?", (user_id,))
    return cursor.fetchone() is not None

# Helper function to add a word
def add_word_to_db(word, meaning):
    cursor.execute("SELECT id FROM words WHERE word=?", (word,))
    word_id = cursor.fetchone()
    if not word_id:
        cursor.execute("INSERT INTO words (word) VALUES (?)", (word,))
        word_id = cursor.lastrowid
    else:
        word_id = word_id[0]

    cursor.execute("INSERT INTO meanings (word_id, meaning) VALUES (?, ?)", (word_id, meaning))
    conn.commit()

# Command to add a word and its meaning
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text('ပြထားသလိုပဲလုပ်ပါ : /add (စကားလုံး) = (အဓိပ္ပါယ်)')
        return

    word = context.args[0].lower()
    meaning = ' '.join(context.args[1:])
    add_word_to_db(word, meaning)
    await update.message.reply_text(f'Added "{word}" with meaning "{meaning}".')

# Command to search for a word and display its meanings
async def search_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await update.message.reply_text('Please use the format: /search <word>')
        return

    word = context.args[0].lower()
    cursor.execute('''SELECT words.word, meanings.meaning, meanings.verified
                      FROM words
                      JOIN meanings ON words.id = meanings.word_id
                      WHERE words.word = ?''', (word,))
    results = cursor.fetchall()

    if not results:
        await update.message.reply_text('Word not found in the glossary.')
    else:
        message = f"{word}:\n"
        for result in results:
            status = "အတည်ပြုပြီး" if result[2] == 1 else "စိစစ်ဆဲ"
            message += f" - {result[1]} ({status})\n"
        await update.message.reply_text(message)

# Command to display the word list (Admin only)
async def word_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You don't have permission to view the word list.")
        return

    cursor.execute("SELECT word FROM words")
    words = cursor.fetchall()
    if not words:
        await update.message.reply_text('No words added yet.')
    else:
        word_list_str = "\n".join([w[0] for w in words])
        await update.message.reply_text(f"Words list:\n{word_list_str}")

# Command to show available commands
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    menu_message = """
    Command Menu:
    /add (စကားလုံး) = (အဓိပ္ပါယ်) - Add a word and its meaning
    /search (စကားလုံး) - Search for a word and display meanings
    """

    # Admin commands
    if is_admin(update.message.from_user.id):
        menu_message += """
        Admin Commands:
        /word_list - Display all added words
        /verify (စကားလုံး) (အဓိပ္ပါယ်) - Verify a meaning
        /remove_word (စကားလုံး) - Remove a word
        /remove_meaning (စကားလုံး) (အဓိပ္ပါယ်) - Remove a specific meaning
        """

    # Operator commands
    if update.message.from_user.id == operator_id:
        menu_message += """
        Operator Commands:
        /add_admin (telegram_id) - Add an admin
        /remove_admin (telegram_id) - Remove an admin
        /admin_list - List all admins
        """

    await update.message.reply_text(menu_message)

# Command to add an admin (Operator only)
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != operator_id:
        await update.message.reply_text("You don't have permission to add admins.")
        return

    if len(context.args) < 1:
        await update.message.reply_text('Please provide a Telegram ID to add as an admin.')
        return

    new_admin_id = int(context.args[0])
    cursor.execute("INSERT INTO admins (telegram_id) VALUES (?)", (new_admin_id,))
    conn.commit()
    await update.message.reply_text(f"Added admin with ID {new_admin_id}")

# Command to remove an admin (Operator only)
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != operator_id:
        await update.message.reply_text("You don't have permission to remove admins.")
        return

    if len(context.args) < 1:
        await update.message.reply_text('Please provide a Telegram ID to remove from admins.')
        return

    remove_admin_id = int(context.args[0])
    cursor.execute("DELETE FROM admins WHERE telegram_id=?", (remove_admin_id,))
    conn.commit()
    await update.message.reply_text(f"Removed admin with ID {remove_admin_id}")

# Command to list admins (Operator only)
async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != operator_id:
        await update.message.reply_text("You don't have permission to view the admin list.")
        return

    cursor.execute("SELECT telegram_id FROM admins")
    admins = cursor.fetchall()
    if not admins:
        await update.message.reply_text('No admins found.')
    else:
        admin_list_str = "\n".join([str(admin[0]) for admin in admins])
        await update.message.reply_text(f"Admin list:\n{admin_list_str}")

# Command to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"မင်္ဂလာပါ {update.effective_user.first_name}, ခက်ဆစ်မှတ်ဉာဏ်ကနေ ကြိုဆိုပါတယ်။ cmd တွေကို ကြည့်ဖို့ /menu ကိုနှိပ်ပါ")

# Command to verify a meaning (Admin only)
async def verify_meaning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You don't have permission to verify meanings.")
        return

    if len(context.args) < 2:
        await update.message.reply_text('Please use the format: /verify (စကားလုံး) (အဓိပ္ပါယ်)')
        return

    word = context.args[0].lower()
    meaning = ' '.join(context.args[1:])

    cursor.execute('''UPDATE meanings
                      SET verified = 1
                      WHERE word_id = (SELECT id FROM words WHERE word = ?)
                      AND meaning = ?''', (word, meaning))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f'Verified meaning "{meaning}" for the word "{word}".')
    else:
        await update.message.reply_text(f'Could not verify meaning for the word "{word}".')

# Command to remove a word (Admin only)
async def remove_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You don't have permission to remove words.")
        return

    if len(context.args) < 1:
        await update.message.reply_text('Please use the format: /remove_word (စကားလုံး)')
        return

    word = context.args[0].lower()

    # Remove the word and associated meanings
    cursor.execute("DELETE FROM words WHERE word = ?", (word,))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f'Removed word "{word}" and all associated meanings.')
    else:
        await update.message.reply_text(f'Word "{word}" not found in the glossary.')

# Command to remove a specific meaning (Admin only)
async def remove_meaning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You don't have permission to remove meanings.")
        return

    if len(context.args) < 2:
        await update.message.reply_text('Please use the format: /remove_meaning (စကားလုံး) (အဓိပ္ပါယ်)')
        return

    word = context.args[0].lower()
    meaning = ' '.join(context.args[1:])

    # Remove the specific meaning
    cursor.execute('''DELETE FROM meanings
                      WHERE word_id = (SELECT id FROM words WHERE word = ?)
                      AND meaning = ?''', (word, meaning))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f'Removed meaning "{meaning}" for the word "{word}".')
    else:
        await update.message.reply_text(f'Meaning not found for the word "{word}".')

# Main function to start the bot
def main() -> None:
    application = ApplicationBuilder().token("7696110911:AAEZ_6EOvFUH3Ax9hUCOkEzl9kKE-_EAh2g").build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_word))
    application.add_handler(CommandHandler("search", search_word))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("add_admin", add_admin))
    application.add_handler(CommandHandler("remove_admin", remove_admin))
    application.add_handler(CommandHandler("admin_list", admin_list))
    application.add_handler(CommandHandler("word_list", word_list))
    application.add_handler(CommandHandler("verify", verify_meaning))  # New
    application.add_handler(CommandHandler("remove_word", remove_word))  # New
    application.add_handler(CommandHandler("remove_meaning", remove_meaning))  # New

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()

