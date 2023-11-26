import asyncio

from github import Auth, Github
from meme_creator import ImageShuffler, ImageGenerator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = "6616259259:AAHzHq1aS8D5_03Zyu9XLxXzouPIJzv46qg"
GITHUB_TOKEN = "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"


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Alles gute zum Jahrestag❤️")


async def shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE, shuffler: ImageShuffler, user_shuffle: dict) -> None:
    user_shuffle[update.effective_user.id] = shuffler.shuffle()
    image_path = shuffler.generate_shuffle_image(update.effective_user.id)

    with open(image_path, 'rb') as f:
        await update.message.reply_photo(photo=f)


async def select(update: Update, context: ContextTypes.DEFAULT_TYPE, user_shuffle) -> None:
    # Already expect the message (the image already shows how many texts are needed)
    # TODO: Get message inside " so that the user can use :
    try:
        msg = update.message.text.split(" ")[1].upper()
        texts = ' '.join(update.message.text.split(" ")[2:]).split(":")
    except:
        await update.message.reply_text("Your text format was not correct")
        return

    if msg not in "ABC":
        await update.message.reply_text("Wrong char, please select A, B or C")
        return
    if update.effective_user.id not in user_shuffle:
        await update.message.reply_text("Not so quick there. You first have to call /shuffle")
        return

    item = user_shuffle[update.effective_user.id][msg]
    if texts[0] == '' or len(texts) != len(item["text-locations"]):
        await update.message.reply_text(f"Did not get the right number of texts, please provide exactly {len(item['text-locations'])} : separated texts")
        return

    gen = ImageGenerator(item["id"], item["name"], item["text-locations"], item["template-location"], update.effective_user.id)

    image_path = gen.add_all_text(texts)
    with open(image_path, 'rb') as f:
        await update.message.reply_photo(photo=f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    instr = f"""
    Hello {update.effective_user.first_name}👋
    
    1. /shuffle \nGet 3 random images to choose from. Not happy with them? Shuffle again
    2. /pick \nA Text One : Text Two -> Pick one of the images you like and send ALL the texts separated by ':'
    Example: /pick B Sentence One : Sentence Two 
    """
    await update.message.reply_html(instr)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


if __name__ == '__main__':
    # Need to store user<->shuffle
    app = ApplicationBuilder().token(TOKEN).build()

    user_shuffle = {}  # key: username, value: current shuffle

    shuffler = ImageShuffler()

    app.add_handler(CommandHandler("shuffle", lambda x, y: shuffle(x, y, shuffler, user_shuffle)))
    app.add_handler(CommandHandler("select", lambda x, y: select(x, y, user_shuffle)))
    app.add_handler(CommandHandler("pick", lambda x, y: select(x, y, user_shuffle)))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sara", hello))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Started telegram bot")
    app.run_polling()