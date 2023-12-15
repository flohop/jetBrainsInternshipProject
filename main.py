# type: ignore
import asyncio
import copy
import os

import shlex
from meme_creator import ImageShuffler, ImageGenerator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

user_shuffle = {}  # key: username, value: current shuffle dict (db)

shuffler = ImageShuffler()  # Everyone uses the same shuffler (is stateless).

commands = {
    "shuffle": ["Return a 3 randomly selected template from which you can choose one to create your meme",  # description
                lambda update, _: shuffle(update, shuffler, user_shuffle),  # function
                ["s"]],  # aliases
    "A": [
        "Pick image A (/A, /a), B (/B, /b) or C (/C, /c) and provide the right numbers of texts e.g. \"Text 1\" \"Text 2\"",
        lambda update, _: select(update, user_shuffle),
        ["a", "B", "b", "C", "c"]],
    "start": ["Intro text to show what the app can do",
              lambda update, _: start(update, _),
              []],
}


def format_instruction(command: str, commands_dict: dict):
    desc, _, aliases = commands_dict[command]

    alias_vals = ''
    if aliases:
        alias_vals = ' '.join("/" + elem for elem in aliases)
        alias_vals = " (" + alias_vals + ")"

    return f"/{command}{alias_vals} {desc}"


# Message
INSTRUCTIONS = f"""
    1. {format_instruction(list(commands.keys())[0], commands)}
    2. {format_instruction(list(commands.keys())[1], commands)}
"""

WRONG_FORMAT = f"""
Your text format was not correct.\n
Please make sure it follows the instructions: \n
{INSTRUCTIONS}
"""

WRONG_COMMAND = f"Wrong command, please use one of the following: {''.join('/' + elem for elem in list(commands.keys())[1])}"

NO_SHUFFLE = f"Not so quick there. You first have to call /{list(commands.keys())[0]}"


def get_num_help_text(command: str, i: int) -> str:
    text = '"Text'
    return "Did not get the right number of texts, please provide exactly %i separated texts.\n" \
           f"Example: /{command} {' '.join([text] * i)}"


async def shuffle(update: Update, shuffler: ImageShuffler,
                  user_shuffle: dict) -> None:
    # According to Google style guide, should not count on
    # atomicity of build in function:
    # https://stackoverflow.com/questions/2291069/is-python-variable-assignment-atomic/55279169#55279169
    async with asyncio.Lock():
        user_shuffle[update.effective_user.id] = shuffler.shuffle()

    image_path = shuffler.generate_shuffle_image(update.effective_user.id,
                                                 copy.deepcopy(user_shuffle[update.effective_user.id]))

    with open(image_path, 'rb') as f:
        await update.message.reply_photo(photo=f)


async def select(update: Update, user_shuffle: dict) -> None:
    # Already expect the message (the image already shows how many texts are needed)
    # Format /A "Text One" "Text Two"

    # Validate that the input format is correct
    # noinspection PyBroadException
    try:
        msg = update.message.text[1].upper()
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

    # Get the template the user selected
    item = user_shuffle[update.effective_user.id][msg]
    # make sure right number of texts were entered
    if not texts or texts[0] == '' or len(texts) != len(item["text-locations"]):
        await update.message.reply_text(get_num_help_text(msg, len(item["text-locations"])))
        return

    # Generate the image
    gen = ImageGenerator(item["id"],
                         item["name"],
                         item["text-locations"],
                         item["template-location"],
                         update.effective_user.id)

    image_path = gen.add_all_text(texts)
    with open(image_path, 'rb') as f:
        await update.message.reply_photo(photo=f)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    instr = f"""
    Hello {update.effective_user.first_name}👋
    {INSTRUCTIONS}"""
    await update.message.reply_html(instr)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"Sorry, I didn't understand that command."
                                        f"{INSTRUCTIONS}")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # register all commands
    for cmd, (descr, fct, alias) in commands.items():
        app.add_handler(CommandHandler([cmd] + alias, fct))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Started telegram bot")
    app.run_polling()
