import copy
import json
import os.path
import random
import typing

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
    STITCH_DIRECTORY = "./stitched_memes"
    TEMPLATE_DIR = "./meme_templates"

    def __init__(self):
        f = open("./meme_data.json")
        file_data = json.load(f)
        f.close()

        self.items = file_data["items"]
        self.num_items = len(self.items)

        self.options = ["A", "B", "C"]

    def shuffle(self) -> dict[str, typing.Any]:
        """
        :return 3 image paths with their associated id, name and template_location
        """
        res = {}  # key: "A","B" or "C" value: template element
        temp_ids = random.Random().sample(population=range(0, self.num_items), k=3)

        for ind, temp_id in enumerate(temp_ids):
            res[self.options[ind]] = self.items[temp_id]

        return res

    def _images_in_row(self, images: list[Image]) -> bool:
        """
        :param images: List of the images that get stitched together
        :return: True if the images should be stitched in a row, false otherwise
        """
        votes = 0
        for image in images:
            if image.width > image.height * 1.25:
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
        max_height = images[0].height
        max_width = images[0].width
        for ind in range(1, len(self.options)):
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
            "image_coordinates": image_coordinates
        }

    def _scale_images(self, images: list[Image], image_coordinates: list[tuple],
                      in_row: bool, max_height: int, max_width: int, cur_rotation):
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

        prev_scale_ratio = [1] * (len(self.options) + 1)
        for i in range(0, len(self.options)):
            img = images[i]

            if in_row:
                scale_ratio = max_height / img.height
            else:
                scale_ratio = max_width / img.width

            new_size = (int(img.width * scale_ratio), int(img.height * scale_ratio))
            images[i] = img.resize(new_size)

            # Adjust the coordinates and text box location
            # x value is:
            # prev coordinate +
            if i > 0:
                if in_row:
                    new_x = int(image_coordinates[i - 1][0] + images[i - 1].width * prev_scale_ratio[i])
                    image_coordinates[i] = (new_x, image_coordinates[i][1])
                else:
                    new_y = int(image_coordinates[i - 1][1] + images[i - 1].height * prev_scale_ratio[i])
                    image_coordinates[i] = (image_coordinates[i][0], new_y)

            # Adjust the help text
            for ctr, j in enumerate(range(len(cur_rotation[self.options[i]]["text-locations"]))):
                x_co, y_co, w, h = cur_rotation[self.options[i]]["text-locations"][j].values()
                cur_rotation[self.options[i]]["text-locations"][ctr]["x"] = int(x_co * scale_ratio)
                cur_rotation[self.options[i]]["text-locations"][ctr]["y"] = int(y_co * scale_ratio)

                cur_rotation[self.options[i]]["text-locations"][ctr]["width"] = int(w * scale_ratio)
                cur_rotation[self.options[i]]["text-locations"][ctr]["height"] = int(h * scale_ratio)

    def generate_shuffle_image(self, user_id, cur_rotation) -> str:
        """
        From the 3 selected shuffle images, create one compositon
        where the letter "A"/"B"/"C" is added
        :return: Path to generated shuffle image

        """
        assert len(cur_rotation) != 0, "Call shuffle first to generate the images"
        images = []
        for opt in self.options:
            images.append(Image.open(os.path.join(self.TEMPLATE_DIR, cur_rotation[opt]["template-location"])))

        in_row = self._images_in_row(images)

        # Determine the width, height and start coordinates of the images of the stitched image
        max_width, max_height, image_coordinates = self._determine_dimensions(images, in_row).values()

        # Scale images to avoid black space
        self._scale_images(images, image_coordinates, in_row, max_height, max_width, cur_rotation)

        # Create a new blank image with the calculated dimensions
        if in_row:
            width = image_coordinates[-1][0] + images[-1].width
            stitched_image = Image.new('RGB', (width, max_height))
        else:
            stitched_image = Image.new('RGB', (max_width, image_coordinates[-1][1] + images[-1].height))

        # Paste the individual images onto the stitched image
        for ind in range(len(self.options)):
            stitched_image.paste(images[ind], image_coordinates[ind])

        # Add "A"/"B"/"C" to the image
        draw = ImageDraw.Draw(stitched_image)

        rectangle_fill_color = (0, 0, 0)
        rectangle_outline_color = (255, 255, 255)
        rectangle_size = 68

        # Add rectangle
        for i in range(len(self.options)):
            x, y = image_coordinates[i]

            draw.rectangle((x, y,
                            x + rectangle_size,
                            y + rectangle_size),
                           fill=rectangle_fill_color,
                           outline=rectangle_outline_color)
            ImageGenerator.add_text(draw, self.options[i], x, y, rectangle_size, rectangle_size)

        # Add the guide text to the image
        for i in range(len(self.options)):
            for ind, elem in enumerate(cur_rotation[self.options[i]]["text-locations"]):
                elem_x, elem_y, elem_with, elem_height = elem.values()
                ImageGenerator.add_text(draw,
                                        f"Text {ind + 1}",
                                        elem_x + image_coordinates[i][0],
                                        elem_y + image_coordinates[i][1],
                                        elem_with,
                                        elem_height)

        # Save the stitched image
        image_path = os.path.join(self.STITCH_DIRECTORY, f"stitch_{user_id}.jpeg")
        stitched_image.save(image_path)

        # Close all images
        for img in images:
            img.close()

        # Reset the image sizes
        return image_path


class ImageGenerator:
    """
    One instance of the generator per template
    for which text should be added
    """
    OUTPUT_DIR = "./created_memes"
    TEMPLATE_DIR = "./meme_templates"

    def __init__(self, _id, name, text_locations: list, template_location, username: str):
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

        try:
            self.image = Image.open(f"{self.TEMPLATE_DIR}/{self.template_location}")
        except FileNotFoundError:
            print("Could not find the file at location: ", self.template_location)

    def get_file_path(self):
        """
        :return: Path to where the finished image should be saved
        """
        return f"{self.OUTPUT_DIR}/{self.id}_{self.username}.jpeg"

    def add_all_text(self, texts: list[str]) -> str:
        """
        :param texts: List of texts to insert in the boxes.
        :return: image location
        :raises AssertionError if the length of texts does not match the number of boxes
        """
        assert len(texts) == len(self.text_locations), "The number of texts has to match the number of boxes"

        draw = ImageDraw.Draw(self.image)

        for i in range(len(texts)):
            text = texts[i]
            x, y, width, height = self.text_locations[i].values()

            self.add_text(draw, text, x, y, width, height)

        # Convert to rgb to prevent RGBA mode errors
        if self.image.format == "PNG":
            rgb_img = self.image.convert("RGB")
            rgb_img.save(self.get_file_path())
        else:
            self.image.save(self.get_file_path())
        return self.get_file_path()

    @staticmethod
    def add_text(draw: ImageDraw, quote: str, x: int, y: int, width: int, height: int) -> None:
        """
        Adds text to the ImageDraw object that fits the text box
        :param draw: Draw object
        :param quote: The text that should be added
        :param x: x-coordinate of text location
        :param y: y-coordinate of text location
        :param width: width of the text block
        :param height: height of the text block
        :return: None (Changed draw object in place)
        """
        text_width = width * 0.9
        text_max_height = height * 0.9

        # Reduce the font size until it fits the box
        size = 36
        while size > 9:
            font_path = "COMIC.TTF"
            font = ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.BASIC)
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

            x1, y1, x2, y2 = draw.multiline_textbbox((0, 0), quote, font, stroke_width=2)
            w, h = x2 - x1, y2 - y1
            if h <= text_max_height:
                break
            else:
                # The text did not fit comfortably into the image
                # Try again at a smaller font size
                size -= 1

        draw.multiline_text((x + (width / 2 - w / 2 - x1), y + (height / 2 - h / 2 - y1)), quote, font=font,
                            align="center",
                            stroke_width=2, stroke_fill="#000")

    @staticmethod
    def factory(template_id: str, username: str):
        """
        Convenience method
        :param template_id: Id of the template
        :param username: identifier of the person creating the meme
        :return:
        """
        # Given the id returns a Generator Object
        with open("./meme_data.json") as f:
            file_data = json.load(f)

            try:
                img_id, name, text_locations, template_location = file_data["items"][int(template_id)].values()
                return ImageGenerator(img_id, name, text_locations, template_location, username)
            except Exception as e:
                print(str(e))
                return None


if __name__ == '__main__':
    shuffler = ImageShuffler()
    rotation = shuffler.shuffle()  # can generate a Gen from the date returned from here to avoid

    shuffler.generate_shuffle_image("flohop", rotation)

    # gen = ImageGenerator.factory("9", "flohop")
    # gen.add_all_text(["One", "Two"])

    # print(shuffler.generate_shuffle_image("flohop"))
    # gen = ImageGenerator(item["id"], item["name"], item["text-locations"], item["template-location"], "flohop")
    # print(gen.add_all_text(["Text One", "Text Two"]))
