from __future__ import annotations

import asyncio
import copy
import dataclasses
import json
import os
import shlex
import typing

import telegram.error
from dotenv import load_dotenv
from meme_creator import ImageGenerator
from meme_creator import ImageShuffler
from telegram import Update
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import filters
from telegram.ext import MessageHandler

# configure environment and staging
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

ENVIRONMENT = os.getenv("ENVIRONMENT")
LANGUAGE = os.getenv("LANGUAGE")

CONFIG_DIR = "./configs"
CONFIG_FILE_FORMAT = "%s.settings.json"
LANGUAGE_FILE_FORMAT = "%s.text.json"


CONFIG_LOCATION = os.path.join(CONFIG_DIR, CONFIG_FILE_FORMAT % ENVIRONMENT)

USER_TEXT_FILE_LOCATION = os.path.join(CONFIG_DIR, LANGUAGE_FILE_FORMAT % LANGUAGE)

with open(USER_TEXT_FILE_LOCATION, "r") as file:
    TEXT_DATA = json.load(file)


user_shuffle: dict[str, dict] = {}  # key: username, value: current shuffle dict (db)

shuffler = ImageShuffler(
    CONFIG_LOCATION
)  # Everyone uses the same shuffler (is stateless).


@dataclasses.dataclass
class Command:
    description: str
    callback: typing.Callable
    aliases: list[str]


commands = {
    "shuffle": Command(
        description=TEXT_DATA["SHUFFLE_HELP_TEXT"],
        callback=lambda update, _: shuffle(update, shuffler, user_shuffle),  # function
        aliases=["s"],
    ),
    "A": Command(
        description=TEXT_DATA["A_HELP_TEXT"],
        callback=lambda update, _: select(update, user_shuffle),
        aliases=[x for x in shuffler.OPTIONS if x != "A"]
        + [x.lower() for x in shuffler.OPTIONS],
    ),
    "start": Command(
        description=TEXT_DATA["START_HELP_TEXT"],
        callback=lambda update, _: start(update, _),
        aliases=[],
    ),
}


def format_instruction(command_name: str, commands_dict: dict[str, Command]) -> str:
    """
    Helper function to format an instruction
    :param command_name: The name of the command
    :param commands_dict: The commands dictionary containing the Command object
    :return: The formatted command string
    """

    cur_command = commands_dict[command_name]

    alias_vals = ""
    if cur_command.aliases:
        alias_vals = "(" + " ".join("/" + elem for elem in cur_command.aliases) + ")"

    return f"/{cur_command} {alias_vals} {cur_command.description}"


# Message
INSTRUCTIONS = f"""
    1. {format_instruction(list(commands.keys())[0], commands)}
    2. {format_instruction(list(commands.keys())[1], commands)}
"""

# Step 1: Read the JSON file
# Step 2: Extract the string from JSON
WRONG_FORMAT = TEXT_DATA["WRONG_FORMAT"] % INSTRUCTIONS

WRONG_COMMAND = TEXT_DATA["WRONG_COMMAND"] % {
    "".join("/" + elem for elem in list(commands.keys())[1])
}

NO_SHUFFLE = TEXT_DATA["NO_SHUFFLE"] % f"/{list(commands.keys())[0]}"

WRONG_NUM = TEXT_DATA["WRONG_NUM"]

UNKNOWN_COMMAND = TEXT_DATA["UNKNOWN_COMMAND"]

HELLO_MESSAGE = TEXT_DATA["HELLO_MESSAGE"]

PLACEHOLDER_TEXT = TEXT_DATA["PLACEHOLDER_TEXT"]


def get_num_help_text(command: str, i: int) -> str:
    return WRONG_NUM % (i, f" /{command} {' '.join([PLACEHOLDER_TEXT] * i)}")


async def shuffle(
    update: Update, shuffler_obj: ImageShuffler, current_shuffle: dict
) -> None:
    # According to Google style guide, should not count on
    # atomicity of build in function:
    # https://stackoverflow.com/questions/2291069/is-python-variable-assignment-atomic/55279169#55279169
    async with asyncio.Lock():
        current_shuffle[update.effective_user.id] = shuffler_obj.shuffle()

    image_path = shuffler_obj.generate_shuffle_image(
        update.effective_user.id,
        copy.deepcopy(current_shuffle[update.effective_user.id]),
    )

    with open(image_path, "rb") as f:
        await update.message.reply_photo(photo=f)

    # Delete the stitch image after it was sent
    os.remove(image_path)


async def select(update: Update, cur_shuffle: dict) -> None:
    """
    Format /A "Text One" "Text Two"

    :param update: The telegram update object
    :param cur_shuffle: The list of the 3 templates the user shuffles
    :return:
    """

    # Validate that the input format is correct
    try:
        msg = update.message.text[1].upper()
        texts = shlex.split(update.message.text[2:])
    except (IndexError, ValueError):
        await update.message.reply_text(WRONG_FORMAT)
        return

    if msg not in shuffler.OPTIONS:
        await update.message.reply_text(WRONG_COMMAND)
        return
    if update.effective_user.id not in cur_shuffle:
        await update.message.reply_text(NO_SHUFFLE)
        return

    # Get the template the user selected
    item = cur_shuffle[update.effective_user.id][msg]
    # make sure right number of texts were entered
    if not texts or texts[0] == "" or len(texts) != len(item["text-locations"]):
        await update.message.reply_text(
            get_num_help_text(msg, len(item["text-locations"]))
        )
        return

    # Generate the image
    gen = ImageGenerator(
        item["id"],
        item["name"],
        item["text-locations"],
        item["template-location"],
        str(update.effective_user.id),
        CONFIG_LOCATION,
    )

    image_path = gen.add_all_text(texts)
    with open(image_path, "rb") as f:
        await update.message.reply_photo(photo=f)

    # Remove the created image after it was sent
    os.remove(image_path)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    instr = f"""
    {HELLO_MESSAGE % update.effective_user.first_name}
    {INSTRUCTIONS}"""
    await update.message.reply_html(instr)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=UNKNOWN_COMMAND + "\n" + INSTRUCTIONS
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # register all commands
    for cmd_name, command in commands.items():
        app.add_handler(CommandHandler([cmd_name] + command.aliases, command.callback))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Started telegram bot")
    try:
        app.run_polling()
    except telegram.error.Conflict:
        print(
            "More than one instance of the telegram bot is running. "
            "Make sure only one is running"
        )
