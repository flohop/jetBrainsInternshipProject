from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import shlex

import telegram.error
from command_names import CommandNames
from dotenv import load_dotenv
from meme_creator import ImageGenerator
from meme_creator import ImageShuffler
from schemas import Command
from schemas import Settings
from schemas import TranslationText
from telegram import Update
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import filters
from telegram.ext import MessageHandler

# from command_names import CommandNamesLiteral


def format_instruction(
    command_name: CommandNames, commands_dict: dict[CommandNames, Command]
) -> str:
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

    return f"/{command_name.value} {alias_vals} {cur_command.description}"


def get_instructions(all_commands: dict[CommandNames, Command]):
    return f"""
    1. {format_instruction(CommandNames.SHUFFLE, all_commands)}
    2. {format_instruction(CommandNames.PICK, all_commands)}
"""


# Message

def get_num_help_text(i: int) -> str:
    return text_data.wrong_num % (
        i,
        f" /{CommandNames.PICK.value} {' '.join([text_data.placeholder_text] * i)}",
    )


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

    # Handle updated message
    if update.message:
        incoming_message = update.message
    else:
        incoming_message = update.effective_message

    # Validate that the input format is correct
    try:
        cmd = incoming_message.text[1].upper()
        texts = shlex.split(incoming_message.text[2:])

    except (IndexError, ValueError, AttributeError):
        await incoming_message.reply_text(
            text_data.wrong_format % get_instructions(commands)
        )
        return

    if update.effective_user.id not in cur_shuffle:
        await incoming_message.reply_text(
            text_data.no_shuffle % f"/{CommandNames.SHUFFLE.value}"
        )
        return

    # Get the template the user selected
    item = cur_shuffle[update.effective_user.id][cmd]
    # make sure right number of texts were entered
    if not texts or texts[0] == "" or len(texts) != len(item["text-locations"]):
        await incoming_message.reply_text(
            get_num_help_text(len(item["text-locations"]))
        )
        return

    # Generate the image
    gen = ImageGenerator(
        item["id"],
        item["name"],
        item["text-locations"],
        item["template-location"],
        str(update.effective_user.id),
        settings,
    )

    image_path = gen.add_all_text(texts)
    with open(image_path, "rb") as f:
        await incoming_message.reply_photo(photo=f)

    # Remove the created image after it was sent
    os.remove(image_path)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    instr = f"""
    {text_data.hello_message % update.effective_user.first_name}
    {get_instructions(commands)}"""
    await update.message.reply_html(instr)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text_data.unknown_command + "\n" + get_instructions(commands),
    )


if __name__ == "__main__":
    # Get config file path from user
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        help="The path to the config file",
        default="./configs/dev.settings.json",
    )

    args = parser.parse_args()

    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    # Load settings
    with open(args.config, "r") as file:
        settings: Settings = Settings.from_dict(json.load(file))

    # Load language
    USER_TEXT_FILE_LOCATION = os.path.join(
        settings.configs_directory, settings.language_file_format % settings.language
    )

    with open(USER_TEXT_FILE_LOCATION, "r") as file:
        text_data: TranslationText = TranslationText.from_dict(json.load(file))

    user_shuffle: dict[
        str, dict
    ] = {}  # key: username, value: current shuffle dict (db)

    # get all env variables and settings
    shuffler = ImageShuffler(
        settings
    )  # Everyone uses the same shuffler (is stateless).

    commands = {
        CommandNames.SHUFFLE: Command(
            description=text_data.shuffle_help_text,
            callback=lambda update, _: shuffle(
                update, shuffler, user_shuffle
            ),  # function
            aliases=[CommandNames.SHUFFLE.value.lower()],
        ),
        CommandNames.PICK: Command(
            description=text_data.pick_help_text,
            callback=lambda update, _: select(update, user_shuffle),
            aliases=[
                x for x in shuffler.settings.options if x != CommandNames.PICK.value
            ],
        ),
        CommandNames.START: Command(
            description=text_data.start_help_text,
            callback=lambda update, _: start(update, _),
            aliases=[],
        ),
    }

    # Start the telegram bot
    app = ApplicationBuilder().token(TOKEN).build()

    # register all commands
    for cmd_name, command in commands.items():
        app.add_handler(
            CommandHandler([cmd_name.value] + command.aliases, command.callback)
        )

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Started telegram bot")
    try:
        app.run_polling()
    except telegram.error.Conflict:
        print(
            "More than one instance of the telegram bot is running. "
            "Make sure only one is running"
        )
