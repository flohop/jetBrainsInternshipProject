import copy
import os

import shlex
from meme_creator import ImageShuffler, ImageGenerator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Message
INSTRUCTIONS = """
    1. /shuffle (or /s): \nGet 3 random images to choose from. Not happy with them? Shuffle again
    2. /A "Text One" "Text Two": \nPick one of the images you like and send ALL the texts
"""

WRONG_FORMAT = """
Your text format was not correct.\n
Please make sure it follows this formula: \n
First pick the image you want -> /A or /B or /C \n
Then add all the needed texts -> \"Text One\" \" Text Two\"
Example: \A \"Hello \" \" World \""""

WRONG_COMMAND = "Wrong command, please use /A, /B or /C"

NO_SHUFFLE = "Not so quick there. You first have to call /shuffle"

TEXT_STRING = '"Text"'


def get_num_help_text(command: str, i: int) -> str:
    return "Did not get the right number of texts, please provide exactly %i separated texts.\n" \
            f"Example: /{command} {' '.join([TEXT_STRING] * i)}"


async def shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE, shuffler: ImageShuffler,
                  user_shuffle: dict) -> None:
    user_shuffle[update.effective_user.id] = shuffler.shuffle()
    image_path = shuffler.generate_shuffle_image(update.effective_user.id,
                                                 copy.deepcopy(user_shuffle[update.effective_user.id]))

    with open(image_path, 'rb') as f:
        await update.message.reply_photo(photo=f)


async def select(update: Update, context: ContextTypes.DEFAULT_TYPE, user_shuffle) -> None:
    # Already expect the message (the image already shows how many texts are needed)
    # Format /A "Text One" Text Two"

    # noinspection PyBroadException
    try:
        msg = update.message.text[1]
        texts = shlex.split(update.message.text[2:])
    except:
        await update.message.reply_text(WRONG_FORMAT)
        return

    if msg not in "ABC":
        await update.message.reply_text(WRONG_COMMAND)
        return
    if update.effective_user.id not in user_shuffle:
        await update.message.reply_text(NO_SHUFFLE)
        return

    item = user_shuffle[update.effective_user.id][msg]
    if not texts or texts[0] == '' or len(texts) != len(item["text-locations"]):
        await update.message.reply_text(get_num_help_text(msg, len(item["text-locations"])))
        return

    gen = ImageGenerator(item["id"], item["name"], item["text-locations"], item["template-location"],
                         update.effective_user.id)

    image_path = gen.add_all_text(texts)
    with open(image_path, 'rb') as f:
        await update.message.reply_photo(photo=f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    instr = f"""
    Hello {update.effective_user.first_name}👋
    {INSTRUCTIONS}"""
    await update.message.reply_html(instr)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"Sorry, I didn't understand that command."
                                        f"{INSTRUCTIONS}")


if __name__ == '__main__':
    # Need to store user<->shuffle
    app = ApplicationBuilder().token(TOKEN).build()

    user_shuffle = {}  # key: username, value: current shuffle

    shuffler = ImageShuffler()  # Everyone uses the same shuffler (is stateless).

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["shuffle", "s"], lambda x, y: shuffle(x, y, shuffler, user_shuffle)))
    app.add_handler(CommandHandler(["A", "a", "B", "b", "C", "c"], lambda x, y: select(x, y, user_shuffle)))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Started telegram bot")
    app.run_polling()