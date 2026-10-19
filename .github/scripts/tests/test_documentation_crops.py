"""Synthetic rasters only; no Jira/Claude/network or published articles."""
import copy
import hashlib
import io
import unittest
from unittest import mock

from PIL import Image, PngImagePlugin
from test_documentation_images import IMAGES, item, block


def raster(fmt="PNG", orientation=None, mode="RGB"):
    source = Image.new(mode, (8, 6))
    if mode == "RGB":
        source.putdata([(x * 30, y * 40, (x + y) * 15) for y in range(6) for x in range(8)])
    output = io.BytesIO()
    options = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        exif[270] = "private metadata"
        options["exif"] = exif
    if fmt == "PNG":
        info = PngImagePlugin.PngInfo()
        info.add_text("Comment", "private metadata")
        options["pnginfo"] = info
    source.save(output, format=fmt, **options)
    return output.getvalue()


def crop_for(data, **changes):
    value = {"left": 1, "top": 2, "right": 7, "bottom": 5,
             "original_width": 8, "original_height": 6,
             "original_sha256": hashlib.sha256(data).hexdigest()}
    return {**value, **changes}


class CropTests(unittest.TestCase):
    def test_legacy_selection_and_exact_original_bytes(self):
        data = raster()
        self.assertEqual([item()], IMAGES.selection(block([item()])))
        result, original, published = IMAGES.process_image(data)
        self.assertEqual(data, result)
        self.assertEqual(original, published)

    def test_crop_pixels_dimensions_metadata_and_determinism(self):
        for fmt in ("PNG", "JPEG"):
            with self.subTest(fmt=fmt):
                data = raster(fmt, 1)
                crop = crop_for(data)
                result, original, published = IMAGES.process_image(data, crop)
                self.assertEqual((8, 6), (original["width"], original["height"]))
                self.assertEqual((6, 3), (published["width"], published["height"]))
                self.assertEqual(hashlib.sha256(result).hexdigest(), published["sha256"])
                self.assertEqual(len(result), published["size"])
                self.assertEqual(result, IMAGES.process_image(data, crop)[0])
                with Image.open(io.BytesIO(data)) as source, Image.open(io.BytesIO(result)) as derived:
                    self.assertEqual(source.crop((1, 2, 7, 5)).tobytes(), derived.tobytes())
                    self.assertEqual({}, derived.info)
                    self.assertEqual({}, dict(derived.getexif()))

    def test_strict_schema_types_and_bounds(self):
        crop = crop_for(raster())
        bad = [{**crop, field: value} for field in ("left", "top", "right", "bottom", "original_width", "original_height")
               for value in (True, False, 1.5, "1", None)]
        bad += [{**crop, "left": -1}, {**crop, "right": 9}, {**crop, "bottom": 7},
                {**crop, "top": 5}, {**crop, "left": 7}, {**crop, "original_width": 0},
                {**crop, "original_sha256": "A" * 64}, {**crop, "extra": 0}, {}, None]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(IMAGES.ImageError):
                IMAGES.selection(block([{**item(), "crop": value}]))

    def test_original_hash_and_dimensions_must_match(self):
        data = raster()
        for changes in ({"original_sha256": "0" * 64}, {"original_width": 9}, {"original_height": 7}):
            with self.subTest(changes=changes), self.assertRaisesRegex(IMAGES.ImageError, "mismatch"):
                IMAGES.process_image(data, crop_for(data, **changes))

    def test_exif_policy_rejects_all_nonidentity_orientations_for_crops(self):
        for fmt in ("PNG", "JPEG"):
            for orientation in range(2, 9):
                data = raster(fmt, orientation)
                self.assertEqual(data, IMAGES.process_image(data)[0])
                with self.subTest(fmt=fmt, orientation=orientation), self.assertRaisesRegex(IMAGES.ImageError, "EXIF"):
                    IMAGES.process_image(data, crop_for(data))

    def test_malformed_excessive_and_precision_loss_are_rejected(self):
        data = raster()
        with mock.patch.object(IMAGES, "MAX_PIXELS", 47), self.assertRaises(IMAGES.ImageError):
            IMAGES.process_image(data)
        # A container with invalid JPEG precision passes the old marker check,
        # but must fail actual decoding before any model request.
        from test_documentation_images import JPEG
        precision = JPEG.index(b"\xff\xc0") + 4
        malformed = JPEG[:precision] + b"\x00" + JPEG[precision + 1:]
        with self.assertRaises(IMAGES.ImageError):
            IMAGES.process_image(malformed)
        with self.assertRaises(IMAGES.ImageError):
            IMAGES.process_image(data[:-5])
        precise = raster(mode="I;16")
        with self.assertRaisesRegex(IMAGES.ImageError, "precision"):
            IMAGES.process_image(precise, crop_for(precise))

    def test_derived_paths_distinct_and_provenance_strict(self):
        data = raster()
        issues = {"APP-2": {"attachment": [{"id": "11", "size": len(data), "mimeType": "image/png"}]}}
        def catalogue(crop):
            return IMAGES.catalogue([block([{**item(), "crop": crop}])], issues,
                                    ("https://example.invalid", "unused", "unused"), 1,
                                    downloader=lambda *args: data)
        first, blobs = catalogue(crop_for(data))
        second, _ = catalogue(crop_for(data, left=2))
        self.assertNotEqual(first[0]["path"], second[0]["path"])
        self.assertEqual(first, catalogue(crop_for(data))[0])
        self.assertEqual(first, IMAGES.validate_entries(first))
        self.assertEqual(blobs[first[0]["path"]], IMAGES.process_image(data, crop_for(data))[0])
        for fields in ({"width": True}, {"height": 5}, {"original": {}},
                       {"crop": crop_for(data, original_sha256="0" * 64)}):
            tampered = [{**copy.deepcopy(first[0]), **fields}]
            with self.subTest(fields=fields), self.assertRaises(IMAGES.ImageError):
                IMAGES.validate_entries(tampered)

    def test_legacy_catalogue_still_valid(self):
        data = raster()
        issues = {"APP-2": {"attachment": [{"id": "11", "size": len(data), "mimeType": "image/png"}]}}
        entries, _ = IMAGES.catalogue([block([item()])], issues,
                                     ("https://example.invalid", "unused", "unused"), 1,
                                     downloader=lambda *args: data)
        legacy = [{k: v for k, v in entries[0].items() if k in IMAGES.IMAGE_FIELDS}]
        self.assertEqual(legacy, IMAGES.validate_entries(legacy))

    def test_palette_and_alpha_pixels_survive_without_metadata(self):
        for mode in ("P", "RGBA", "LA", "L"):
            with self.subTest(mode=mode):
                source = Image.new(mode, (8, 6))
                if mode == "P":
                    source.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
                    source.putdata([i % 2 for i in range(48)])
                    source.info["transparency"] = 0
                buffer = io.BytesIO()
                source.save(buffer, format="PNG")
                data = buffer.getvalue()
                derived = IMAGES.process_image(data, crop_for(data))[0]
                with Image.open(io.BytesIO(derived)) as result:
                    self.assertEqual(source.convert("RGBA").crop((1, 2, 7, 5)).tobytes(),
                                     result.convert("RGBA").tobytes())
                    self.assertEqual({}, result.info)

    def test_decoding_bomb_warning_and_animation_are_errors(self):
        data = raster()
        with mock.patch.object(Image, "MAX_IMAGE_PIXELS", 30), self.assertRaises(IMAGES.ImageError):
            IMAGES.process_image(data)
        first, second = Image.new("RGB", (8, 6), "red"), Image.new("RGB", (8, 6), "blue")
        buffer = io.BytesIO()
        first.save(buffer, format="PNG", save_all=True, append_images=[second], duration=100)
        with self.assertRaisesRegex(IMAGES.ImageError, "multi-frame"):
            IMAGES.process_image(buffer.getvalue())

    def test_derived_byte_limits_are_checked_independently(self):
        # A noisy raster exercises PNG growth beyond the JPEG byte count.
        import random
        source = Image.frombytes("RGB", (128, 128), random.Random(42).randbytes(128 * 128 * 3))
        buffer = io.BytesIO()
        source.save(buffer, format="JPEG")
        data = buffer.getvalue()
        crop = crop_for(data, left=0, top=0, right=128, bottom=128,
                        original_width=128, original_height=128)
        with mock.patch.object(IMAGES, "MAX_IMAGE_BYTES", len(data) + 1), self.assertRaises(IMAGES.ImageError):
            IMAGES.process_image(data, crop)
        issues = {"APP-2": {"attachment": [{"id": "11", "size": len(data), "mimeType": "image/jpeg"}]}}
        with mock.patch.object(IMAGES, "MAX_BATCH_BYTES", len(data) + 1), self.assertRaisesRegex(IMAGES.ImageError, "Derived"):
            IMAGES.catalogue([block([{**item(), "crop": crop}])], issues,
                             ("https://example.invalid", "unused", "unused"), 1,
                             downloader=lambda *args: data)


if __name__ == "__main__":
    unittest.main()
