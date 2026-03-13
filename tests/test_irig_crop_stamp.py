import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_H = REPO_ROOT / "Miniscope_DAQ" / "definitions.h"
MINISCOPE_H = REPO_ROOT / "Miniscope_DAQ" / "miniscope.h"
MINISCOPE_C = REPO_ROOT / "Miniscope_DAQ" / "miniscope.c"


def read_text(path: Path) -> str:
    return path.read_text(encoding="ascii")


def parse_define(text: str, name: str) -> str:
    match = re.search(rf"^\s*#define\s+{name}\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing #define for {name}")
    return match.group(1).strip()


class CropStampLayoutTests(unittest.TestCase):
    def test_gitignore_ignores_ds_store(self) -> None:
        gitignore = read_text(REPO_ROOT / ".gitignore")
        self.assertIn(".DS_Store", gitignore)

    def test_expected_crop_and_stamp_defines_exist(self) -> None:
        definitions_text = read_text(DEFINITIONS_H)

        required_defines = [
            "AUX_INPUT",
            "CROP_LEFT_EDGE_PX",
            "CROP_TOP_EDGE_PX",
            "CROP_WIDTH_PX",
            "CROP_HEIGHT_PX",
            "STAMP_SIZE_PX",
            "STAMP_BYTES_PER_ROW",
            "STAMP_LEFT_EDGE_PX",
            "STAMP_TOP_EDGE_PX",
            "STAMP_MODE_ALWAYS_WHITE",
            "STAMP_MODE_GPIO22",
            "STAMP_MODE",
        ]

        for define_name in required_defines:
            parse_define(definitions_text, define_name)

    def test_stamp_lands_inside_assumed_crop(self) -> None:
        definitions_text = read_text(DEFINITIONS_H)

        crop_left = int(parse_define(definitions_text, "CROP_LEFT_EDGE_PX"))
        crop_top = int(parse_define(definitions_text, "CROP_TOP_EDGE_PX"))
        crop_width = int(parse_define(definitions_text, "CROP_WIDTH_PX"))
        crop_height = int(parse_define(definitions_text, "CROP_HEIGHT_PX"))
        stamp_left = int(parse_define(definitions_text, "STAMP_LEFT_EDGE_PX"))
        stamp_top = int(parse_define(definitions_text, "STAMP_TOP_EDGE_PX"))
        stamp_size = int(parse_define(definitions_text, "STAMP_SIZE_PX"))

        self.assertGreaterEqual(stamp_left, crop_left)
        self.assertGreaterEqual(stamp_top, crop_top)
        self.assertLessEqual(stamp_left + stamp_size, crop_left + crop_width)
        self.assertLessEqual(stamp_top + stamp_size, crop_top + crop_height)

    def test_frame_tracking_globals_exist(self) -> None:
        miniscope_h = read_text(MINISCOPE_H)
        miniscope_c = read_text(MINISCOPE_C)

        for symbol in ("stampRowsDone", "stampVal", "frameBytesSoFar"):
            self.assertIn(symbol, miniscope_h)
            self.assertIn(symbol, miniscope_c)


if __name__ == "__main__":
    unittest.main()
