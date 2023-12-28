from __future__ import annotations

import os.path
from dataclasses import dataclass
from typing import Callable
from typing import List

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class TranslationText:
    wrong_format: str
    no_shuffle: str
    wrong_num: str
    shuffle_help_text: str
    pick_help_text: str
    start_help_text: str
    unknown_command: str
    hello_message: str
    placeholder_text: str


@dataclass_json
@dataclass
class Settings:
    assets_directory: str
    language: str
    database_name: str
    collection_name: str
    fonts_directory: str
    configs_directory: str
    stitch_directory: str
    template_directory: str
    created_directory: str
    data_location: str
    rectangle_fill_color: List[int]
    rectangle_outline_color: List[int]
    rectangle_size: int
    file_mode: str
    placeholder_text: str
    stitch_file_format: str
    language_file_format: str
    options: List[str]
    height_bias: float
    font_max_size: int
    font_min_size: int
    font_stroke_width: int
    font_stroke_fill: str
    font_path: str
    created_file_format: str
    text_box_width_ratio: float
    text_box_height_ratio: float

    def get_stitch_directory(self):
        return os.path.join(self.assets_directory, self.stitch_directory)

    def get_template_directory(self):
        return os.path.join(self.assets_directory, self.template_directory)

    def get_created_directory(self):
        return os.path.join(self.assets_directory, self.created_directory)

    def get_fonts_directory(self):
        return os.path.join(self.assets_directory, self.fonts_directory)


@dataclass
class Command:
    description: str
    callback: Callable
    aliases: list[str]
