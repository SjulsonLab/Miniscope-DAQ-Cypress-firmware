import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_H = REPO_ROOT / "Miniscope_DAQ" / "definitions.h"
MINISCOPE_H = REPO_ROOT / "Miniscope_DAQ" / "miniscope.h"
MINISCOPE_C = REPO_ROOT / "Miniscope_DAQ" / "miniscope.c"
UVC_C = REPO_ROOT / "Miniscope_DAQ" / "uvc.c"


def read_text(path: Path) -> str:
    return path.read_text(encoding="ascii")


def parse_define(text: str, name: str) -> str:
    match = re.search(rf"^\s*#define\s+{name}\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing #define for {name}")
    return match.group(1).strip()


def parse_int_define(text: str, name: str) -> int:
    value = parse_define(text, name)
    if re.fullmatch(r"\d+", value):
        return int(value)
    return parse_int_define(text, value)


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

        crop_left = parse_int_define(definitions_text, "CROP_LEFT_EDGE_PX")
        crop_top = parse_int_define(definitions_text, "CROP_TOP_EDGE_PX")
        crop_width = parse_int_define(definitions_text, "CROP_WIDTH_PX")
        crop_height = parse_int_define(definitions_text, "CROP_HEIGHT_PX")
        stamp_left = parse_int_define(definitions_text, "STAMP_LEFT_EDGE_PX")
        stamp_top = parse_int_define(definitions_text, "STAMP_TOP_EDGE_PX")
        stamp_size = parse_int_define(definitions_text, "STAMP_SIZE_PX")

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

    def test_gpio22_mode_is_enabled(self) -> None:
        definitions_text = read_text(DEFINITIONS_H)
        self.assertEqual(parse_define(definitions_text, "STAMP_MODE"), "STAMP_MODE_GPIO22")

    def test_aux_gpio_is_sampled_and_initialized(self) -> None:
        uvc_text = read_text(UVC_C)

        required_snippets = [
            "CyU3PGpioSimpleGetValue (AUX_INPUT, &ttlState);",
            "CyU3PDeviceGpioOverride (AUX_INPUT, CyTrue);",
            "CyU3PGpioSetSimpleConfig (AUX_INPUT, &gpioConfig);",
            "CyU3PGpioSetIoMode (AUX_INPUT, CY_U3P_GPIO_IO_MODE_WPD);",
        ]

        for snippet in required_snippets:
            self.assertIn(snippet, uvc_text)


if __name__ == "__main__":
    unittest.main()
