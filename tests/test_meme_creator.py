from meme_creator import ImageGenerator, ImageShuffler
from PIL import Image
import pytest

TEST_IMAGE_ONE = "./meme_templates/meme1.jpeg"
TEST_IMAGE_TWO = "./meme_templates/meme2.jpeg"
TEST_IMAGE_THREE = "./meme_templates/meme3.jpeg"

TEST_DATA = {
      "id": "0",
      "name": "The Rock in a car",
      "text-locations": [
        {
          "x": 280,
          "y": 30,
          "width": 210,
          "height": 100
        },
        {
          "x": 290,
          "y": 228,
          "width": 200,
          "height": 90
        }
      ],
      "template-location": "./meme1.jpeg"
    }

TEST_DATA_SHUFFLE = {'A': {'id': '0', 'name': 'The Rock in a car', 'text-locations': [{'x': 280, 'y': 30, 'width': 210, 'height': 100}, {'x': 290, 'y': 228, 'width': 200, 'height': 90}], 'template-location': './meme1.jpeg'},
                     'B': {'id': '1', 'name': 'Left Exit 12 Off Ramp', 'text-locations': [{'x': 130, 'y': 64, 'width': 76, 'height': 104}, {'x': 280, 'y': 60, 'width': 100, 'height': 111}, {'x': 170, 'y': 344, 'width': 200, 'height': 72}], 'template-location': './meme2.jpeg'},
                     'C': {'id': '2', 'name': "Gru's Plan", 'text-locations': [{'x': 216, 'y': 61, 'width': 123, 'height': 170}, {'x': 565, 'y': 59, 'width': 114, 'height': 161}, {'x': 216, 'y': 288, 'width': 115, 'height': 150}, {'x': 560, 'y': 279, 'width': 123, 'height': 170}], 'template-location': './meme3.jpeg'}}


@pytest.fixture()
def image_shuffler():
    image_shuffler = ImageShuffler()
    image_shuffler.cur_rotation = TEST_DATA_SHUFFLE
    return image_shuffler


@pytest.fixture()
def images():
    """
    :return: 3 PIL image objects
    """
    return [Image.open(TEST_IMAGE_ONE),
            Image.open(TEST_IMAGE_TWO),
            Image.open(TEST_IMAGE_THREE)]


@pytest.fixture()
def image_gen():
    return ImageGenerator(TEST_DATA["id"],
                          TEST_DATA["name"],
                          TEST_DATA["text-locations"],
                          TEST_DATA["template-location"],
                          "test_user")


class TestImageShuffler:
    def test_init(self, image_shuffler):
        """
        Test that the object is initialized correctly
        """
        assert len(image_shuffler.items) > 0
        assert image_shuffler.options == ["A", "B", "C"]
        assert image_shuffler.num_items == len(image_shuffler.items)

    def test_shuffle(self, image_shuffler):
        """
        Test that the shuffle method returns
        3 valid template data and sets the
        instance attribute
        """
        rotation = image_shuffler.shuffle()

        assert len(image_shuffler.cur_rotation.items()) == 3
        for k, v in rotation.items():
            assert k in "ABC"
            assert "id" in v
            assert "name" in v
            assert "text-locations" in v
            assert "template-location" in v

    def test_images_in_row(self, image_shuffler, images):
        assert not image_shuffler._images_in_row(images)

    def test_determine_dimensions_in_row(self, image_shuffler, images):
        w, h, coo = image_shuffler._determine_dimensions(images, True).values()

        assert w == 500
        assert h == 616

        assert len(coo) == 3
        assert coo == [(0, 0), (500, 0), (1024, 0)]

    def test_determine_dimensions_in_col(self, image_shuffler, images):
        w, h, coo = image_shuffler._determine_dimensions(images, False).values()

        assert w == 700
        assert h == 616

        assert len(coo) == 3
        assert coo == [(0, 0), (0, 616), (0, 1115)]

    def test_scale_image_in_row(self, image_shuffler, images):
        image_coordinates = [(0, 0), (0, 616), (0, 1115)]
        max_height = 616
        max_width = 700

        image_shuffler._scale_images(images, image_coordinates, True, max_height, max_width)

        # Test that the attribute self.cur_rotation gets changed correctly
        assert image_coordinates == [(0, 0), (500, 616), (1146, 1115)]
        assert image_shuffler.cur_rotation["A"]["text-locations"] == [{'x': 280, 'y': 30, 'width': 210, 'height': 100}, {'x': 290, 'y': 228, 'width': 200, 'height': 90}]
        assert image_shuffler.cur_rotation["B"]["text-locations"] == [{'x': 160, 'y': 79, 'width': 93, 'height': 128}, {'x': 345, 'y': 74, 'width': 123, 'height': 137}, {'x': 209, 'y': 424, 'width': 246, 'height': 88}]
        assert image_shuffler.cur_rotation["C"]["text-locations"] == [{'x': 296, 'y': 83, 'width': 168, 'height': 233}, {'x': 775, 'y': 80, 'width': 156, 'height': 220}, {'x': 296, 'y': 395, 'width': 157, 'height': 205}, {'x': 768, 'y': 382, 'width': 168, 'height': 233}]


@pytest.fixture()
def image_generator():
    return ImageGenerator.factory("0", "test_user")


class TestImageGenerator:

    def test_factory(self):
        img_id = "0"
        usr_id = "test_user"
        image_generator = ImageGenerator.factory(img_id, usr_id)

        assert image_generator is not None
        assert image_generator.id == img_id
        assert image_generator.name == "The Rock in a car"
        assert len(image_generator.text_locations) > 0
        assert image_generator.template_location == "./meme1.jpeg"
        assert image_generator.username == usr_id

    def test_get_file_path(self, image_generator):
        assert image_generator.get_file_path() == './created_memes/0_test_user.jpeg'


