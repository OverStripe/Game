import os
import random
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["anime_bot"]
users_collection = db["users"]
characters_collection = db["characters"]
sudo_users_collection = db["sudo_users"]

# Define rarity levels
rarities = {
    "common": "Common 🌱",
    "elite": "Elite ✨",
    "rare": "Rare 🌟",
    "legendary": "Legendary 🌠"
}

# Global variables
current_character = None
message_counter = 0  # Counter for messages since the last correct guess
message_threshold = 5  # Number of messages required before showing the next character


# Helper Functions
def assign_random_rarity():
    """Assign a random rarity."""
    return random.choice(list(rarities.values()))


def add_character_to_db(name, rarity, image_url):
    """Add a character to MongoDB."""
    character = {"name": name, "rarity": rarity, "image_url": image_url}
    characters_collection.insert_one(character)
    return character


def update_user_coins(user_id, user_name, coins):
    """Update user's coins."""
    user = users_collection.find_one({"user_id": user_id})
    if user:
        users_collection.update_one({"user_id": user_id}, {"$inc": {"coins": coins}})
    else:
        users_collection.insert_one({"user_id": user_id, "name": user_name, "coins": coins})


async def show_random_character(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Show a random character in the chat."""
    global current_character, message_counter
    current_character = characters_collection.aggregate([{"$sample": {"size": 1}}]).next()
    message_counter = 0  # Reset the message counter
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=current_character["image_url"],
        caption=(
            f"📢 **Guess the Character!** 📢\n\n"
            f"⦿ **Rarity:** {current_character['rarity']}\n\n"
            "🔥 **Can you guess their name? Type it in the chat!** 🔥"
        ),
        parse_mode=ParseMode.MARKDOWN
    )


def is_sudo_user(user_id):
    """Check if a user is an owner or a sudo user."""
    return user_id == OWNER_ID or sudo_users_collection.find_one({"user_id": user_id}) is not None


# Command Handlers
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow the owner or sudo users to upload a character."""
    user_id = update.message.from_user.id
    if is_sudo_user(user_id):
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text("⚠️ Usage: /upload <image_url> <name> [rarity]", parse_mode=ParseMode.MARKDOWN)
                return
            
            image_url = args[0]
            name = args[1]
            rarity = rarities.get(args[2].lower(), assign_random_rarity()) if len(args) > 2 else assign_random_rarity()

            add_character_to_db(name, rarity, image_url)

            await update.message.reply_text(
                f"✅ **Character added successfully!** ✅\n\n"
                f"⦿ **Name:** {name}\n"
                f"⦿ **Rarity:** {rarity}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.message.reply_text(f"❌ **Error:** {str(e)}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ **You are not authorized to use this command.** ❌", parse_mode=ParseMode.MARKDOWN)


async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a sudo user (owner only)."""
    if update.message.from_user.id == OWNER_ID:
        try:
            user_id = int(context.args[0])
            if sudo_users_collection.find_one({"user_id": user_id}):
                await update.message.reply_text(f"⚠️ **User {user_id} is already a sudo user.**", parse_mode=ParseMode.MARKDOWN)
                return

            sudo_users_collection.insert_one({"user_id": user_id})
            await update.message.reply_text(f"✅ **User {user_id} added to sudo list.** ✅", parse_mode=ParseMode.MARKDOWN)
        except IndexError:
            await update.message.reply_text("⚠️ Usage: /addsudo <user_id>", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ **Error:** {str(e)}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ **You are not authorized to use this command.** ❌", parse_mode=ParseMode.MARKDOWN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome the user and start the bot."""
    keyboard = [
        [
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/TechPiro"),
            InlineKeyboardButton("📂 Source Code", url="https://t.me/TechPiroBots"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎉 **Welcome to the Anime Guessing Bot!** 🎉\n\n"
        "⦿ **Type a character's name to guess and earn coins!** 💰\n\n"
        "✨ Have fun playing! ✨",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    await show_random_character(context, update.effective_chat.id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the help message."""
    await update.message.reply_text(
        "📜 **Commands** 📜\n\n"
        "⦿ /start - Start the bot and display a random character.\n"
        "⦿ /help - Show this help menu.\n"
        "⦿ /upload - Upload a character (owner/sudo only).\n"
        "⦿ /stats - Check bot statistics.\n"
        "⦿ /level - View the top 10 players.\n"
        "⦿ /addsudo - Add a sudo user (owner only).\n\n"
        "✨ **How to Play** ✨\n\n"
        "1️⃣ A random character will appear.\n"
        "2️⃣ Guess their name by typing it in the chat.\n"
        "3️⃣ Earn coins for correct guesses!\n\n"
        "💡 **Enjoy the game and aim for the top leaderboard!** 💡",
        parse_mode=ParseMode.MARKDOWN
    )


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the top 10 players."""
    top_users = users_collection.find().sort("coins", -1).limit(10)
    leaderboard = "🏆 **Top 10 Players** 🏆\n\n"
    for i, user in enumerate(top_users, start=1):
        full_name = user["name"] if user["name"] else "Unknown Player"
        leaderboard += f"⦿ {i}. **{full_name}** - 💰 {user['coins']} coins\n"
    await update.message.reply_text(leaderboard, parse_mode=ParseMode.MARKDOWN)


async def guess_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user guesses and message threshold for new characters."""
    global current_character, message_counter

    if not current_character:
        return

    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name
    guess = update.message.text.strip().lower()
    character_name = current_character["name"].lower()

    if guess in character_name:
        update_user_coins(user_id, user_name, 1000)
        await update.message.reply_text(
            f"🎉 **Correct!** You guessed **{current_character['name']}**.\n"
            f"💰 **You earned 1000 coins!**",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        message_counter += 1
        if message_counter >= message_threshold:
            await show_random_character(context, update.effective_chat.id)
            return


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload))
    application.add_handler(CommandHandler("addsudo", addsudo))
    application.add_handler(CommandHandler("level", level))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess_handler))

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main()
    
