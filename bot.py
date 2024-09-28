import telebot
import random
from collections import defaultdict
from datetime import datetime, timedelta

# Replace with your actual bot API token and Telegram channel ID
API_TOKEN = "7825167784:AAFrNGXECQW0CB4oT9dlHJeYHUO9RnwnFHk"
BOT_OWNER_ID = 7222795580  # Replace with the owner’s Telegram ID
CHANNEL_ID = -1002438449944  # Replace with your Telegram channel ID where characters are logged

bot = telebot.TeleBot(API_TOKEN)

# In-memory store for game data
user_coins = defaultdict(int)  # User coin balance
user_profiles = {}  # User profiles (username or first_name)
user_correct_guesses = defaultdict(int)  # Track correct guesses
user_inventory = defaultdict(list)  # Collected characters
user_last_bonus = {}  # Track last bonus claim time
user_streak = defaultdict(int)  # Track user guess streak
characters = []  # List of uploaded characters (with ID)
current_character = None
message_counter = defaultdict(int)  # Track message count per chat

# Global message count
global_message_count = 0  # Global counter for messages in all chats

# Settings
BONUS_COINS = 50000  # Bonus amount for daily claim
BONUS_INTERVAL = timedelta(days=1)  # Bonus claim interval (24 hours)
COINS_PER_GUESS = 50  # Coins for correct guesses
STREAK_BONUS_COINS = 1000  # Additional coins for continuing a streak
RARITY_LEVELS = {
    'Common': '⭐',
    'Rare': '🌟',
    'Epic': '💫',
    'Legendary': '✨'
}
RARITY_WEIGHTS = [60, 25, 10, 5]
character_id_counter = 1  # Counter for character IDs
MESSAGE_THRESHOLD = 5  # Number of messages before sending a new character

# Helper Functions
def add_coins(user_id, coins):
    user_coins[user_id] += coins

def assign_rarity():
    return random.choices(list(RARITY_LEVELS.keys()), weights=RARITY_WEIGHTS, k=1)[0]

def fetch_new_character():
    if characters:
        return random.choice(characters)
    return None

def send_character(chat_id):
    global current_character
    current_character = fetch_new_character()
    if current_character:
        rarity = RARITY_LEVELS[current_character['rarity']]
        caption = (
            f"🎨 Guess the Anime Character!\n\n"
            f"💬 Name: ???\n"
            f"⚔️ Rarity: {rarity} {current_character['rarity']}\n"
        )
        bot.send_photo(chat_id, current_character['image_url'], caption=caption)

def find_character_by_id(char_id):
    for character in characters:
        if character['id'] == char_id:
            return character
    return None

# Command Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    # Capture the user's username, and if not available, fallback to first_name
    user_profiles[user_id] = message.from_user.username or message.from_user.first_name
    bot.reply_to(message, "Welcome to the Anime Character Guessing Game! Type /help for commands.")

@bot.message_handler(commands=['help'])
def show_help(message):
    help_message = """
Available Commands:
/bonus - Claim your daily reward (50,000 coins every 24 hours)
/profile - View your profile
/inventory - View your collected characters
/leaderboard - Show the top 10 leaderboard
/upload <image_url> <character_name> - Upload a new character (Owner only)
/delete <character_id> - Delete a character (Owner only)
/stats - Show bot statistics (Owner only)
"""
    bot.reply_to(message, help_message)

@bot.message_handler(commands=['bonus'])
def claim_bonus(message):
    user_id = message.from_user.id
    now = datetime.now()

    # Check if the user can claim the bonus
    if user_id in user_last_bonus and now - user_last_bonus[user_id] < BONUS_INTERVAL:
        next_claim = user_last_bonus[user_id] + BONUS_INTERVAL
        remaining_time = next_claim - now
        hours_left = remaining_time.seconds // 3600
        minutes_left = (remaining_time.seconds % 3600) // 60
        bot.reply_to(message, f"You can claim your next bonus in {hours_left} hours and {minutes_left} minutes.")
    else:
        add_coins(user_id, BONUS_COINS)
        user_last_bonus[user_id] = now
        bot.reply_to(message, f"🎉 You have received {BONUS_COINS} coins!")

@bot.message_handler(commands=['upload'])
def upload_character(message):
    global character_id_counter

    # Only the owner (BOT_OWNER_ID) can upload characters
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "You do not have permission to upload characters.")
        return

    try:
        _, image_url, character_name = message.text.split(maxsplit=2)
    except ValueError:
        bot.reply_to(message, "Format: /upload <image_url> <character_name>")
        return

    rarity = assign_rarity()
    character = {'id': character_id_counter, 'image_url': image_url, 'character_name': character_name, 'rarity': rarity}
    characters.append(character)
    bot.send_message(CHANNEL_ID, f"New character uploaded: {character_name} (ID: {character_id_counter}, {RARITY_LEVELS[rarity]} {rarity})")
    bot.reply_to(message, f"✅ Character '{character_name}' uploaded successfully with ID {character_id_counter}!")

    character_id_counter += 1

@bot.message_handler(commands=['delete'])
def delete_character(message):
    # Only the owner (BOT_OWNER_ID) can delete characters
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "You do not have permission to delete characters.")
        return

    try:
        _, char_id_str = message.text.split(maxsplit=1)
        char_id = int(char_id_str)
    except (ValueError, IndexError):
        bot.reply_to(message, "Format: /delete <character_id>")
        return

    character = find_character_by_id(char_id)
    if character:
        characters.remove(character)
        bot.reply_to(message, f"✅ Character with ID {char_id} ('{character['character_name']}') has been deleted.")
    else:
        bot.reply_to(message, f"❌ Character with ID {char_id} not found.")

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    coins = user_coins[user_id]
    correct_guesses = user_correct_guesses[user_id]
    inventory_count = len(user_inventory[user_id])
    streak = user_streak[user_id]  # Show streak

    profile_message = (
        f"Profile\nCoins: {coins}\nCorrect Guesses: {correct_guesses}\nStreak: {streak}\nInventory: {inventory_count} characters"
    )
    bot.reply_to(message, profile_message)

@bot.message_handler(commands=['inventory'])
def show_inventory(message):
    user_id = message.from_user.id
    inventory = user_inventory[user_id]

    if not inventory:
        bot.reply_to(message, "Your inventory is empty. Start guessing characters to collect them!")
    else:
        # Count characters and display in compact form (e.g., Naruto x2 if the user has multiple of the same character)
        inventory_count = {}
        for character in inventory:
            key = (character['character_name'], character['rarity'])
            inventory_count[key] = inventory_count.get(key, 0) + 1

        inventory_message = f"🎒 **{user_profiles.get(user_id)}**'s Character Collection:\n"
        for i, ((character_name, rarity), count) in enumerate(inventory_count.items(), 1):
            # Display character with a count if more than one is owned
            inventory_message += f"{i}. {character_name} ({rarity}) x{count if count > 1 else ''}\n"
        
        bot.reply_to(message, inventory_message)

@bot.message_handler(commands=['leaderboard'])
def show_leaderboard(message):
    # Combine coins for each unique user
    unique_user_coins = defaultdict(int)
    for user_id, coins in user_coins.items():
        unique_user_coins[user_id] = coins  # Aggregate coins per user ID

    # Sort unique users by their coin totals in descending order
    sorted_users = sorted(unique_user_coins.items(), key=lambda x: x[1], reverse=True)[:10]  # Top 10 users only

    leaderboard_message = "🏆 **Top 10 Leaderboard**:\n\n"
    for rank, (user_id, coins) in enumerate(sorted_users, start=1):
        # Fetch the Telegram profile name (username or first_name)
        profile_name = user_profiles.get(user_id)
        if not profile_name:
            # Retrieve the profile name from the message if missing
            profile_name = message.from_user.first_name
            user_profiles[user_id] = profile_name
        
        leaderboard_message += f"{rank}. {profile_name}: {coins} coins\n"
    
    bot.reply_to(message, leaderboard_message)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    # Only the owner (BOT_OWNER_ID) can see bot stats
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to view this information.")
        return

    total_users = len(user_profiles)
    total_coins_distributed = sum(user_coins.values())
    total_correct_guesses = sum(user_correct_guesses.values())

    stats_message = (
        f"📊 **Bot Stats**:\n\n"
        f"👥 Total Users: {total_users}\n"
        f"💰 Total Coins Distributed: {total_coins_distributed}\n"
        f"✅ Total Correct Guesses: {total_correct_guesses}"
    )
    bot.reply_to(message, stats_message, parse_mode='Markdown')

# Function to handle all types of messages and increment the message counter
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global global_message_count
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_guess = message.text.strip().lower() if message.text else ""

    # Increment global message counter
    global_message_count += 1

    # Check if the message count has reached the threshold
    if global_message_count >= MESSAGE_THRESHOLD:
        send_character(chat_id)  # Send a new character after the threshold is reached
        global_message_count = 0  # Reset the message counter

    # Check if the user is guessing the character
    if current_character:
        character_name = current_character['character_name'].strip().lower()
        if user_guess in character_name:  # Partial match
            add_coins(user_id, COINS_PER_GUESS)
            user_correct_guesses[user_id] += 1
            user_streak[user_id] += 1  # Increment streak
            user_inventory[user_id].append(current_character)  # Add character to user's inventory
            
            # Reward streak bonus
            streak_bonus = STREAK_BONUS_COINS * user_streak[user_id]
            add_coins(user_id, streak_bonus)
            bot.reply_to(message, f"🎉 Congratulations! You guessed correctly and earned {COINS_PER_GUESS} coins!\n"
                                  f"🔥 Streak Bonus: {streak_bonus} coins for a {user_streak[user_id]}-guess streak!")
            send_character(chat_id)  # Send a new character after correct guess
        else:
            user_streak[user_id] = 0  # Reset the streak if the guess is wrong

# Start polling the bot
bot.infinity_polling(timeout=60, long_polling_timeout=60)
