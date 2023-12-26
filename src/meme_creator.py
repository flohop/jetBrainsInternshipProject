import json
import os.path
import typing

from dotenv import load_dotenv
from pymongo import MongoClient

from PIL import Image, ImageFont, ImageDraw


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
    def __init__(self, config_file):
        # Load the configs
        with open(config_file) as f:
            self.CONFIGS = json.load(f)

        self.ASSETS_DIRECTORY: str = self.CONFIGS["ASSETS_DIRECTORY"]
        self.CONFIGS_DIRECTORY: str = self.CONFIGS["CONFIGS_DIRECTORY"]

        self.STITCH_DIRECTORY: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["STITCH_DIRECTORY"]
        )
        self.TEMPLATE_DIRECTORY: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["TEMPLATE_DIRECTORY"]
        )
        self.CREATED_DIRECTORY: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["CREATED_DIRECTORY"]
        )
        self.DATA_LOCATION: str = os.path.join(
            self.CONFIGS_DIRECTORY, self.CONFIGS["DATA_LOCATION"]
        )

        self.RECTANGLE_FILL_COLOR = tuple(self.CONFIGS["RECTANGLE_FILL_COLOR"])
        self.RECTANGLE_OUTLINE_COLOR = tuple(self.CONFIGS["RECTANGLE_OUTLINE_COLOR"])
        self.RECTANGLE_SIZE = self.CONFIGS["RECTANGLE_SIZE"]
        self.FILE_FORMAT = self.CONFIGS["STITCH_FILE_FORMAT"]
        self.OPTIONS = self.CONFIGS["OPTIONS"]
        self.HEIGHT_BIAS = self.CONFIGS["HEIGHT_BIAS"]
        self.FILE_MODE = self.CONFIGS["FILE_MODE"]
        self.PLACEHOLDER_TEXT = self.CONFIGS["PLACEHOLDER_TEXT"]

        mongo_server_url = os.getenv("MONGO_SERVER_URL")
        database_name = self.CONFIGS["DATABASE_NAME"]
        collection_name = self.CONFIGS["COLLECTION_NAME"]

        load_dotenv()

        # Loading all items in memory
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
            self.collection.aggregate([{"$sample": {"size": len(self.OPTIONS)}}])
        ):
            res[self.OPTIONS[ind]] = sample

        return res

    def _images_in_row(self, images: list[Image]) -> bool:
        """
        Function is biased towards placing the images in a row
        :param images: List of the images that get stitched together
        :return: True if the images should be stitched in a row, false otherwise
        """
        votes = 0
        for image in images:
            if image.width > image.height * self.HEIGHT_BIAS:
                votes -= 1
            elif image.height > image.width:
                votes += 1
        return votes > 0

    def _determine_dimensions(self, images: list[Image], in_row) -> dict:
        """
        :param images: List of images
        :param in_row: Determine of the images should be stitched in a row
        :return: Dict containing the dimensions of the final image and the start location of each image
        """
        image_coordinates = [(0, 0)]  # x, y
        assert len(images) > 0, "Please provide at least one image"
        max_height = images[0].height
        max_width = images[0].width
        for ind in range(1, len(self.OPTIONS)):
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
        images: list[Image],
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

        prev_scale_ratio = [1] * (len(self.OPTIONS) + 1)
        for i in range(0, len(self.OPTIONS)):
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
                range(len(cur_rotation[self.OPTIONS[i]]["text-locations"]))
            ):
                x_co, y_co, w, h = cur_rotation[self.OPTIONS[i]]["text-locations"][
                    j
                ].values()
                cur_rotation[self.OPTIONS[i]]["text-locations"][ctr]["x"] = int(
                    x_co * scale_ratio
                )
                cur_rotation[self.OPTIONS[i]]["text-locations"][ctr]["y"] = int(
                    y_co * scale_ratio
                )

                cur_rotation[self.OPTIONS[i]]["text-locations"][ctr]["width"] = int(
                    w * scale_ratio
                )
                cur_rotation[self.OPTIONS[i]]["text-locations"][ctr]["height"] = int(
                    h * scale_ratio
                )

    def generate_shuffle_image(self, user_id, cur_rotation) -> str:
        """
        From the 3 selected shuffle images, create one composition
        where the letter "A"/"B"/"C" are added
        :return: Path to generated shuffle image

        """
        assert len(cur_rotation) != 0, "Call shuffle first to generate the images"
        images = []
        for opt in self.OPTIONS:
            images.append(
                Image.open(
                    os.path.join(
                        self.TEMPLATE_DIRECTORY, cur_rotation[opt]["template-location"]
                    )
                )
            )

        in_row = self._images_in_row(images)

        # Determine the width, height and start coordinates of the images of the stitched image
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
            stitched_image = Image.new(self.FILE_MODE, (width, max_height))
        else:
            height = image_coordinates[-1][1] + images[-1].height
            stitched_image = Image.new(
                self.FILE_MODE,
                (max_width, height),
            )

        # Paste the individual images onto the stitched image
        for ind in range(len(self.OPTIONS)):
            stitched_image.paste(images[ind], image_coordinates[ind])

        # Add "A"/"B"/"C" to the image
        draw = ImageDraw.Draw(stitched_image)

        # Add rectangle
        for i in range(len(self.OPTIONS)):
            x, y = image_coordinates[i]

            draw.rectangle(
                (x, y, x + self.RECTANGLE_SIZE, y + self.RECTANGLE_SIZE),
                fill=self.RECTANGLE_FILL_COLOR,
                outline=self.RECTANGLE_OUTLINE_COLOR,
            )
            ImageGenerator.add_text(
                draw,
                self.OPTIONS[i],
                x,
                y,
                self.RECTANGLE_SIZE,
                self.RECTANGLE_SIZE,
                config=self.CONFIGS,
            )

        # Add the guide text to the image
        for i in range(len(self.OPTIONS)):
            for ind, elem in enumerate(cur_rotation[self.OPTIONS[i]]["text-locations"]):
                elem_x, elem_y, elem_with, elem_height = elem.values()
                ImageGenerator.add_text(
                    draw,
                    f"{self.PLACEHOLDER_TEXT}{ind + 1}",
                    elem_x + image_coordinates[i][0],
                    elem_y + image_coordinates[i][1],
                    elem_with,
                    elem_height,
                    self.CONFIGS,
                )

        # Save the stitched image
        # create the directory if needed
        while not os.path.exists(self.STITCH_DIRECTORY):
            os.makedirs(self.STITCH_DIRECTORY)

        image_path = os.path.join(self.STITCH_DIRECTORY, self.FILE_FORMAT % user_id)
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

    # prevent loading the settings for each instance
    CONFIGS = None

    def __init__(
        self,
        _id,
        name,
        text_locations: list,
        template_location,
        username: str,
        config_file: str,
    ):
        """
        :param _id: meme template id
        :param name: The name of the meme
        :param text_locations: List of all locations of the text (x, y, width, height)
        :param template_location: The file location of the template
        :param username: id of user creating the meme
        """
        self.id = _id
        self.name = name
        self.text_locations = text_locations
        self.template_location = template_location
        self.username = username

        # Load the config file
        if ImageGenerator.CONFIGS is None:
            with open(config_file, "r") as f:
                self.CONFIGS = json.load(f)

        self.ASSETS_DIRECTORY: str = self.CONFIGS["ASSETS_DIRECTORY"]
        self.OUTPUT_DIRECTORY: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["CREATED_DIRECTORY"]
        )
        self.TEMPLATE_DIRECTORY: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["TEMPLATE_DIRECTORY"]
        )
        self.DATA_LOCATION: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["DATA_LOCATION"]
        )
        self.FONTS_DIRECTORY: str = os.path.join(
            self.ASSETS_DIRECTORY, self.CONFIGS["FONTS_DIRECTORY"]
        )

        self.FONT_MAX_SIZE: int = self.CONFIGS["FONT_MAX_SIZE"]
        self.FONT_MIN_SIZE: int = self.CONFIGS["FONT_MIN_SIZE"]
        self.FONT_STROKE_WIDTH: int = self.CONFIGS["FONT_STROKE_WIDTH"]
        self.FONT_STROKE_FILL: str = self.CONFIGS["FONT_STROKE_FILL"]
        self.FONT_LOCATION: str = os.path.join(
            self.FONTS_DIRECTORY, self.CONFIGS["FONT_PATH"]
        )
        self.FILE_FORMAT: str = self.CONFIGS["CREATED_FILE_FORMAT"]
        self.TEXT_BOX_WIDTH_RATIO: float = self.CONFIGS["TEXT_BOX_WIDTH_RATIO"]
        self.TEXT_BOX_HEIGHT_RATIO: float = self.CONFIGS["TEXT_BOX_HEIGHT_RATIO"]
        self.FILE_MODE = self.CONFIGS["FILE_MODE"]

        try:
            self.image = Image.open(
                os.path.join(str(self.TEMPLATE_DIRECTORY), self.template_location)
            )
        except FileNotFoundError:
            print("Could not find the file at location: ", self.template_location)

    def get_file_path(self):
        """
        :return: Path to where the finished image should be saved
        """
        # create the directory if needed
        while not os.path.exists(self.OUTPUT_DIRECTORY):
            os.makedirs(self.OUTPUT_DIRECTORY)

        return os.path.join(self.OUTPUT_DIRECTORY, self.FILE_FORMAT % self.username)

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

            self.add_text(draw, text, x, y, width, height, self.CONFIGS)

        # Convert to rgb to prevent RGBA mode errors
        if self.image.format == "PNG":
            self.image = self.image.convert(self.FILE_MODE)
        self.image.save(self.get_file_path())
        return self.get_file_path()

    @staticmethod
    def add_text(
        draw: ImageDraw,
        quote: str,
        x: int,
        y: int,
        width: int,
        height: int,
        config: dict,
    ) -> None:
        """
        Adds text to the ImageDraw object that fits the text box
        :param draw: Draw object
        :param quote: The text that should be added
        :param x: x-coordinate of text location
        :param y: y-coordinate of text location
        :param width: width of the text block
        :param height: height of the text block
        :param config: the configuration dictionary
        :return: None (Changed draw object in place)
        """
        text_width = width * config["TEXT_BOX_WIDTH_RATIO"]
        text_max_height = height * config["TEXT_BOX_HEIGHT_RATIO"]

        # Reduce the font size until it fits the box
        size = config["FONT_MAX_SIZE"]
        while size >= config["FONT_MIN_SIZE"]:
            font = ImageFont.truetype(
                os.path.join(
                    config["ASSETS_DIRECTORY"],
                    config["FONTS_DIRECTORY"],
                    config["FONT_PATH"],
                ),
                size,
                layout_engine=ImageFont.Layout.BASIC,
            )
            lines = []
            line = ""
            for word in quote.split():
                proposed_line = line
                if line:
                    proposed_line += " "
                proposed_line += word
                if font.getlength(proposed_line) <= text_width:
                    line = proposed_line
                else:
                    # If this word was added, the line would be too long
                    # Start a new line instead
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            quote = "\n".join(lines)

            x1, y1, x2, y2 = draw.multiline_textbbox(
                (0, 0), quote, font, stroke_width=2
            )
            w, h = x2 - x1, y2 - y1
            if h <= text_max_height:
                break
            else:
                # The text did not fit comfortably into the image
                # Try again at a smaller font size
                size -= 1

        draw.multiline_text(
            (x + (width / 2 - w / 2 - x1), y + (height / 2 - h / 2 - y1)),
            quote,
            font=font,
            align="center",
            stroke_width=config["FONT_STROKE_WIDTH"],
            stroke_fill=config["FONT_STROKE_FILL"],
        )


if __name__ == "__main__":
    # configure environment and staging
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    ENVIRONMENT = os.getenv("ENVIRONMENT")
    LANGUAGE = os.getenv("LANGUAGE")
    LANGUAGE_FILE_FORMAT = os.getenv("LANGUAGE_FILE_FORMAT")
    CONFIG_DIR = os.getenv("CONFIG_DIRECTORY")

    CONFIG_LOCATION = os.path.join(
        CONFIG_DIR, os.getenv("CONFIG_FILE_FORMAT") % ENVIRONMENT
    )
    shuffler = ImageShuffler(CONFIG_LOCATION)
    rotation = (
        shuffler.shuffle()
    )  # can generate a Gen from the date returned from here to avoid

    print(shuffler.generate_shuffle_image("flohop", rotation))
    print("Finished")

    # gen = ImageGenerator.factory("9", "flohop")
    # gen.add_all_text(["One", "Two"])

    # print(shuffler.generate_shuffle_image("flohop"))
    # item = shuffler.shuffle()["A"]
    # gen = ImageGenerator(item["id"], item["name"], item["text-locations"], item["template-location"], "flohop")
    # print(gen.add_all_text(["Text One", "Text Two"]))
