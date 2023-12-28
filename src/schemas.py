from dataclasses_json import dataclass_json
from dataclasses import dataclass
from typing import List, Callable


@dataclass_json
@dataclass
class TranslationText:
    wrong_format: str
    no_shuffle: str
    wrong_num: str
    shuffle_help_text: str
    a_help_text: str
    start_help_text: str
    unknown_command: str
    hello_message: str
    placeholder_text: str


@dataclass_json
@dataclass
class Settings:
    assets_directory: str
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


@dataclass
class Command:
    description: str
    callback: Callable
    aliases: list[str]

