from __future__ import annotations

import os.path
import typing

from dotenv import load_dotenv
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from pymongo import MongoClient

from schemas import Settings


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@singleton
class ImageShuffler:
    """
    Stateless ImageShuffler that can generate
    a stitched image of the 3 randomly selected memes
    The results should be stored outside the class
    """

    # Constant
    def __init__(self, settings):
        # Load the settings
        self.settings = settings

        mongo_server_url = os.getenv("MONGO_SERVER_URL")
        database_name = self.settings.database_name
        collection_name = self.settings.collection_name

        load_dotenv()

        client = MongoClient(mongo_server_url)

        db = client[database_name]
        self.collection = db[collection_name]

        self.num_items = self.collection.count_documents({})

    def shuffle(self) -> dict[str, typing.Any]:
        """
        return 3 image paths with their associated id,
        name and template_location
        """
        res = {}  # key: "A","B" or "C" value: template element

        for ind, sample in enumerate(
            self.collection.aggregate(
                [{"$sample": {"size": len(self.settings.options)}}]
            )
        ):
            res[self.settings.options[ind]] = sample

        return res

    def _images_in_row(self, images: list[Image.Image]) -> bool:
        """
        Function is biased towards placing the images in a row
        :param images: List of the images that get stitched together
        :return: True if the images should be stitched in a row, false otherwise
        """
        votes = 0
        for image in images:
            if image.width > image.height * self.settings.height_bias:
                votes -= 1
            elif image.height > image.width:
                votes += 1
        return votes > 0

    def _determine_dimensions(self, images: list[Image.Image], in_row) -> dict:
        """
        :param images: List of images
        :param in_row: Determine of the images should be stitched in a row
        :return: Dict containing the dimensions of the final image
        and the start location of each image
        """
        image_coordinates = [(0, 0)]  # x, y
        assert len(images) > 0, "Please provide at least one image"
        if images[0] is None:
            raise ValueError("Value can not be none")
        max_height = images[0].height
        max_width = images[0].width
        for ind in range(1, len(self.settings.options)):
            if images[ind] is None:
                raise ValueError("Value can not be none")

            if in_row:
                x = image_coordinates[ind - 1][0] + images[ind - 1].width
                y = 0
                max_height = max(max_height, images[ind].height)
            else:
                x = 0
                y = image_coordinates[ind - 1][1] + images[ind - 1].height
                max_width = max(max_width, images[ind].width)
            image_coordinates.append((x, y))

        return {
            "max_width": max_width,
            "max_height": max_height,
            "image_coordinates": image_coordinates,
        }

    def _scale_images(
        self,
        images: list[Image.Image],
        image_coordinates: list[tuple],
        in_row: bool,
        max_height: int,
        max_width: int,
        cur_rotation,
    ):
        """
        Updates the parameter cur_rotation in place
        :param images: List of images
        :param image_coordinates: List of image coordinates and text coordinates
        :param in_row: Are images in a row or column
        :param max_height: Biggest image height
        :param max_width: Biggest image width
        :return: Scaled image coordinates
        """
        # Resize the image
        # In row => Set height
        # In column => Set width
        # Cur x coordinate = prev width * prev scale_ratio

        prev_scale_ratio = [1] * (len(self.settings.options) + 1)
        for i in range(0, len(self.settings.options)):
            img = images[i]

            scale_ratio = max_height / img.height if in_row else max_width / img.width

            new_size = (int(img.width * scale_ratio), int(img.height * scale_ratio))
            images[i] = img.resize(new_size)

            # Adjust the coordinates and text box location
            if i > 0:
                new_val = int(
                    image_coordinates[i - 1][0 if in_row else 1]
                    + (images[i - 1].width if in_row else images[i - 1].height)
                    * prev_scale_ratio[i]
                )

                image_coordinates[i] = (
                    (new_val, image_coordinates[i][1])
                    if in_row
                    else (image_coordinates[i][0], new_val)
                )

            # Adjust the help text
            for ctr, j in enumerate(
                range(len(cur_rotation[self.settings.options[i]]["text-locations"]))
            ):
                x_co, y_co, w, h = cur_rotation[self.settings.options[i]][
                    "text-locations"
                ][j].values()
                cur_rotation[self.settings.options[i]]["text-locations"][ctr][
                    "x"
                ] = int(x_co * scale_ratio)
                cur_rotation[self.settings.options[i]]["text-locations"][ctr][
                    "y"
                ] = int(y_co * scale_ratio)

                cur_rotation[self.settings.options[i]]["text-locations"][ctr][
                    "width"
                ] = int(w * scale_ratio)
                cur_rotation[self.settings.options[i]]["text-locations"][ctr][
                    "height"
                ] = int(h * scale_ratio)

    def generate_shuffle_image(self, user_id, cur_rotation) -> str:
        """
        From the 3 selected shuffle images, create one composition
        where the letter "A"/"B"/"C" are added
        :return: Path to generated shuffle image

        """
        assert len(cur_rotation) != 0, "Call shuffle first to generate the images"
        images = []
        for opt in self.settings.options:
            images.append(
                Image.open(
                    os.path.join(
                        self.settings.get_template_directory(),
                        cur_rotation[opt]["template-location"],
                    )
                )
            )

        in_row = self._images_in_row(images)

        # Determine the width, height and start coordinates
        # of the images of the stitched image
        max_width, max_height, image_coordinates = self._determine_dimensions(
            images, in_row
        ).values()

        assert len(image_coordinates) > 0, "There are no coordinates for the image"

        # Scale images to avoid black space
        self._scale_images(
            images, image_coordinates, in_row, max_height, max_width, cur_rotation
        )

        # Create a new blank image with the calculated dimensions
        if in_row:
            width = image_coordinates[-1][0] + images[-1].width
            stitched_image = Image.new(self.settings.file_mode, (width, max_height))
        else:
            height = image_coordinates[-1][1] + images[-1].height
            stitched_image = Image.new(
                self.settings.file_mode,
                (max_width, height),
            )

        # Paste the individual images onto the stitched image
        for ind in range(len(self.settings.options)):
            stitched_image.paste(images[ind], image_coordinates[ind])

        # Add "A"/"B"/"C" to the image
        draw = ImageDraw.Draw(stitched_image)

        # Add rectangle
        for i in range(len(self.settings.options)):
            x, y = image_coordinates[i]

            draw.rectangle(
                (
                    x,
                    y,
                    x + self.settings.rectangle_size,
                    y + self.settings.rectangle_size,
                ),
                fill=tuple(self.settings.rectangle_fill_color),
                outline=tuple(self.settings.rectangle_outline_color),
            )
            ImageGenerator.add_text(
                draw,
                self.settings.options[i],
                x,
                y,
                self.settings.rectangle_size,
                self.settings.rectangle_size,
                settings=self.settings,
            )

        # Add the guide text to the image
        for i in range(len(self.settings.options)):
            for ind, elem in enumerate(
                cur_rotation[self.settings.options[i]]["text-locations"]
            ):
                elem_x, elem_y, elem_with, elem_height = elem.values()
                ImageGenerator.add_text(
                    draw,
                    f"{self.settings.placeholder_text}{ind + 1}",
                    elem_x + image_coordinates[i][0],
                    elem_y + image_coordinates[i][1],
                    elem_with,
                    elem_height,
                    self.settings,
                )

        # Save the stitched image
        # create the directory if needed
        while not os.path.exists(self.settings.get_stitch_directory()):
            os.makedirs(self.settings.get_stitch_directory())

        image_path = str(
            os.path.join(
                self.settings.get_stitch_directory(),
                self.settings.stitch_file_format % user_id,
            )
        )
        stitched_image.save(image_path)

        # Close all images
        for img in images:
            img.close()

        return image_path


class ImageGenerator:
    """
    One instance of the generator per template
    for which text should be added
    """

    def __init__(
        self,
        _id,
        name,
        text_locations: list,
        template_name,
        username: str,
        settings: Settings,
    ):
        """
        :param _id: meme template id
        :param name: The name of the meme
        :param text_locations: List of all locations of the text (x, y, width, height)
        :param template_name: The file name of the template
        :param username: id of user creating the meme
        """
        self.id = _id
        self.name = name
        self.text_locations = text_locations
        self.template_name = template_name
        self.username = username

        self.settings = settings

        try:
            self.image = Image.open(
                os.path.join(self.settings.get_template_directory(), self.template_name)
            )
        except FileNotFoundError:
            print("Could not find the file at location: ", self.template_name)

    def get_file_path(self):
        """
        :return: Path to where the finished image should be saved
        """
        # create the directory if needed
        while not os.path.exists(self.settings.get_created_directory()):
            os.makedirs(self.settings.get_created_directory())

        return os.path.join(
            self.settings.get_created_directory(),
            self.settings.created_file_format % self.username,
        )

    def add_all_text(self, texts: list[str]) -> str:
        """
        :param texts: List of texts to insert in the boxes.
        :return: image location
        :raises AssertionError if the length of texts does not match the number of boxes
        """
        assert len(texts) == len(
            self.text_locations
        ), "The number of texts has to match the number of boxes"

        draw = ImageDraw.Draw(self.image)

        for i in range(len(texts)):
            text = texts[i]
            x, y, width, height = self.text_locations[i].values()

            self.add_text(draw, text, x, y, width, height, self.settings)

        # Convert to rgb to prevent RGBA mode errors
        if self.image.format == "PNG":
            self.image = self.image.convert(self.settings.file_mode)
        self.image.save(self.get_file_path())
        return self.get_file_path()

    @staticmethod
    def add_text(
        draw: ImageDraw.ImageDraw,
        quote: str,
        x: int,
        y: int,
        width: int,
        height: int,
        settings: Settings | None,
    ) -> None:
        """
        Adds text to the ImageDraw object that fits the text box
        Uses binary search to quickly find the biggest font size that fits the box
        :param draw: Draw object
        :param quote: The text that should be added
        :param x: x-coordinate of text location
        :param y: y-coordinate of text location
        :param width: width of the text block
        :param height: height of the text block
        :param settings: the configuration dictionary
        :return: None (Changed draw object in place)
        """

        if settings is None:
            raise ValueError("Please provide a valid configuration dictionary")

        text_width = width * settings.text_box_width_ratio
        text_max_height = height * settings.text_box_height_ratio

        # Binary search for the maximum font size
        low, high = settings.font_min_size, settings.font_max_size
        font = None

        while low <= high:
            mid = (low + high) // 2
            candidate_font = ImageFont.truetype(
                os.path.join(
                    settings.assets_directory,
                    settings.fonts_directory,
                    settings.font_path,
                ),
                mid,
                layout_engine=ImageFont.Layout.BASIC,
            )

            lines = []
            line = ""
            for word in quote.split():
                proposed_line = line
                if line:
                    proposed_line += " "
                proposed_line += word
                if candidate_font.getlength(proposed_line) <= text_width:
                    line = proposed_line
                else:
                    lines.append(line)
                    line = word

            if line:
                lines.append(line)
            formatted_text = "\n".join(lines)

            x1, y1, x2, y2 = draw.multiline_textbbox(
                (0, 0),
                formatted_text,
                candidate_font,
                stroke_width=settings.font_stroke_width,
            )
            w, h = x2 - x1, y2 - y1

            if h <= text_max_height:
                # The text fits comfortably
                font = candidate_font
                low = mid + 1
            else:
                # The text does not fit comfortably, try a smaller font size
                high = mid - 1

        if font is not None:
            draw.multiline_text(
                (x + (width / 2 - w / 2 - x1), y + (height / 2 - h / 2 - y1)),
                formatted_text,
                font=font,
                align="center",
                stroke_width=settings.font_stroke_width,
                stroke_fill=settings.font_stroke_fill,
            )
