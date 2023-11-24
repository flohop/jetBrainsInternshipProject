import json
import os.path
import random
import typing

from PIL import Image, ImageFont, ImageDraw


class ImageShuffler:
    STITCH_DIRECTORY = "./stitched_memes"
    TEMPLATE_DIR = "./meme_templates"

    def __init__(self):
        f = open("./meme_data.json")
        file_data = json.load(f)
        f.close()

        self.num_items = file_data["num_items"]
        self.items = file_data["items"]

        self.options = ["A", "B", "C"]
        self.cur_rotation = {}  # key: "A", "B", "C", value: (template_id, template_name, template_location

    def shuffle(self) -> dict[str, typing.Any]:
        """
        :return 3 image paths with their associated id, name and template_location
        """
        temp_ids = random.Random().sample(population=range(0, self.num_items), k=3, counts=[3])

        for ind, temp_id in enumerate(temp_ids):
            self.cur_rotation[self.options[ind]] = self.items[temp_id]

        return self.cur_rotation

    def generate_shuffle_image(self, user_id) -> str:
        """
        From the 3 selected shuffle images, create one compositon
        where the letter "A"/"B"/"C" is added
        :return: Path to generated shuffle image

        """
        assert len(self.cur_rotation) != 0, "Call shuffle first to generate the images"
        images = []
        for opt in self.options:
            images.append(Image.open(os.path.join(self.TEMPLATE_DIR, self.cur_rotation[opt]["template-location"])))

        # If more images have a higher width than height, then stitch in column
        # Neg => In column
        # Pos => In Row
        votes = 0
        for image in images:
            if image.width > image.height:
                votes -= 1
            elif image.height > image.width:
                votes += 1

        if votes < 0:
            in_row = False
        else:
            in_row = True

        # Determine the width and height of the stitched image
        image_coordinates = [(0, 0)]  # x, y
        max_height = 0
        max_width = 0
        for ind in range(1, len(self.options)):
            if in_row:
                x = image_coordinates[ind - 1][0] + images[ind - 1].width
                y = 0
                max_height = max(max_height, images[ind - 1].height)
            else:
                x = 0
                y = image_coordinates[ind - 1][1] + images[ind - 1].height
                max_width = max(max_width, images[ind - 1].width)
            image_coordinates.append((x, y))

        # Create a new blank image with the calculated dimensions
        if in_row:
            stitched_image = Image.new('RGB', (image_coordinates[-1][0] + images[-1].width, max_height))
        else:
            stitched_image = Image.new('RGB', (max_width, image_coordinates[-1][1] + images[-1].height))

        # Paste the individual images onto the stitched image
        for ind in range(len(self.options)):
            stitched_image.paste(images[ind], image_coordinates[ind])

        # Add A/B/C to the image
        draw = ImageDraw.Draw(stitched_image)

        # fnt = ImageFont.truetype("./COMIC.TTF", 64)

        rectangle_fill_color = (0, 0, 0)
        rectangle_outline_color = (255, 255, 255)
        rectangle_size = 68

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
            for ind, elem in enumerate(self.cur_rotation[self.options[i]]["text-locations"]):
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

        return image_path


class ImageGenerator:
    OUTPUT_DIR = "./created_memes"
    TEMPLATE_DIR = "./meme_templates"

    def __init__(self, id, name, text_locations: list, template_location, username: str):
        self.id = id
        self.name = name
        self.text_locations = text_locations
        self.template_location = template_location
        self.username = username

        try:
            self.image = Image.open(f"{self.TEMPLATE_DIR}/{self.template_location}")
        except FileNotFoundError:
            print("Could not find the file at location: ", self.template_location)

    def get_file_path(self):
        return f"{self.OUTPUT_DIR}/{self.id}_{self.username}.jpeg"

    def add_all_text(self, texts: str) -> str:
        """
        Add
        :param texts: List of texts to insert in the boxes.
        :return: returrn image location
        :raises AssertionError if the length of texts does not match the number of boxes
        """
        assert len(texts) == len(self.text_locations), "The number of texts has to match the number of boxes"

        draw = ImageDraw.Draw(self.image)

        for i in range(len(texts)):
            text = texts[i]
            x, y, width, height = self.text_locations[i].values()

            self.add_text(draw, text, x, y, width, height)

        self.image.save(self.get_file_path())
        return self.get_file_path()

    @staticmethod
    def add_text(draw: ImageDraw, quote: str, x: int, y: int, width: int, height: int) -> None:
        text_width = width * 0.8
        text_max_height = height * 0.8

        size = 36
        while size > 9:
            # Insert your own font path here
            font_path = "Times New Roman.ttf"
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
        # Given the id returns a Generator Object
        with open("./meme_data.json") as f:
            file_data = json.load(f)

            try:
                img_id, name, text_locations, template_location = file_data["items"][int(template_id)].values()
                return ImageGenerator(img_id, name, text_locations, template_location, username)
            except:
                return None


if __name__ == '__main__':
    shuffler = ImageShuffler()
    rotation = shuffler.shuffle()  # can generate a Gen from the date returned from here to avoid

    print(shuffler.generate_shuffle_image("flohop"))
