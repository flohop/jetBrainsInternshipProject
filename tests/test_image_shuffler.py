from __future__ import annotations

import copy
import json
import os
from unittest.mock import patch

import pytest
from PIL import Image

from src.meme_creator import ImageGenerator
from src.meme_creator import ImageShuffler

DEV_CONFIG_LOCATION = "./configs/dev.settings.json"
TEST_CONFIG_LOCATION = "./tests/mock_data.json"

with open(DEV_CONFIG_LOCATION) as f:
    DEV_CONF = json.load(f)

with open(TEST_CONFIG_LOCATION) as f:
    TEST_CONF = json.load(f)


@pytest.fixture()
def test_data():
    return TEST_CONF["TEST_DATA"]


@pytest.fixture()
def test_data_shuffle():
    return TEST_CONF["TEST_DATA_SHUFFLE"]


@pytest.fixture()
def test_images():
    assets_dir = DEV_CONF["ASSETS_DIRECTORY"]
    template_dir = DEV_CONF["TEMPLATE_DIRECTORY"]

    img_1 = TEST_CONF["TEST_IMAGE_ONE"]
    img_2 = TEST_CONF["TEST_IMAGE_TWO"]
    img_3 = TEST_CONF["TEST_IMAGE_THREE"]

    res = []
    for img in (img_1, img_2, img_3):
        res.append(os.path.join(assets_dir, template_dir, img))

    return res


@pytest.fixture()
@patch("pymongo.collection.Collection.count_documents")
def image_shuffler(mock_count, test_data_shuffle):
    mock_count.return_value = 3
    image_shuffler = ImageShuffler(DEV_CONFIG_LOCATION)
    image_shuffler.cur_rotation = test_data_shuffle
    return image_shuffler


@pytest.fixture()
def images(test_images):
    """
    :return: 3 PIL image objects
    """
    return [Image.open(img) for img in test_images]


@pytest.fixture()
def image_gen(test_data):
    return ImageGenerator(
        test_data["id"],
        test_data["name"],
        test_data["text-locations"],
        test_data["template-location"],
        "test_user",
        TEST_CONFIG_LOCATION,
    )


class TestImageShuffler:
    def test_init(self, image_shuffler):
        """
        Test that the object is initialized correctly
        """
        assert image_shuffler.num_items > 0
        assert image_shuffler.OPTIONS == ["A", "B", "C"]

    @patch("pymongo.collection.Collection.aggregate")
    def test_shuffle(self, aggregate_mock, image_shuffler, test_data):
        """
        Test that the shuffle method returns
        3 valid template data and sets the
        instance attribute
        """

        aggregate_mock.return_value = test_data
        rotation = image_shuffler.shuffle()

        assert len(rotation) == 3
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

    def test_scale_image_in_row(self, image_shuffler, images, test_data_shuffle):
        image_coordinates = [(0, 0), (0, 616), (0, 1115)]
        max_height = 616
        max_width = 700

        cur_shuffle = copy.deepcopy(test_data_shuffle)

        image_shuffler._scale_images(
            images, image_coordinates, True, max_height, max_width, cur_shuffle
        )

        # Test that the attribute self.cur_rotation gets changed correctly
        assert image_coordinates == [(0, 0), (500, 616), (1146, 1115)]
        assert cur_shuffle["A"]["text-locations"] == [
            {"x": 280, "y": 30, "width": 210, "height": 100},
            {"x": 290, "y": 228, "width": 200, "height": 90},
        ]
        assert cur_shuffle["B"]["text-locations"] == [
            {"x": 160, "y": 79, "width": 93, "height": 128},
            {"x": 345, "y": 74, "width": 123, "height": 137},
            {"x": 209, "y": 424, "width": 246, "height": 88},
        ]
        assert cur_shuffle["C"]["text-locations"] == [
            {"x": 296, "y": 83, "width": 168, "height": 233},
            {"x": 775, "y": 80, "width": 156, "height": 220},
            {"x": 296, "y": 395, "width": 157, "height": 205},
            {"x": 768, "y": 382, "width": 168, "height": 233},
        ]
