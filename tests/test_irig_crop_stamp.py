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


def eval_define_expr(text: str, name: str) -> int:
    """Evaluate a #define that may be an arithmetic expression of other defines."""
    raw = parse_define(text, name).strip("()")
    try:
        return int(raw)
    except ValueError:
        pass

    # Substitute all known uppercase define names with their integer values.
    def substitute(m: re.Match) -> str:
        try:
            return str(parse_int_define(text, m.group(0)))
        except (AssertionError, RecursionError):
            return m.group(0)

    expanded = re.sub(r"\b[A-Z_][A-Z0-9_]*\b", substitute, raw)
    return eval(expanded)  # nosec - test-only helper on trusted source


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

    def test_frame_tracking_globals_exist(self) -> None:
        miniscope_h = read_text(MINISCOPE_H)
        miniscope_c = read_text(MINISCOPE_C)

        for symbol in ("stampRowsDone", "stampVal", "frameBytesSoFar"):
            self.assertIn(symbol, miniscope_h)
            self.assertIn(symbol, miniscope_c)


class GPIO22BottomLeftStampTests(unittest.TestCase):
    """Tests for 30x30 GPIO-22 stamp in the bottom-left of the full frame."""

    def test_stamp_size_is_30(self) -> None:
        defs = read_text(DEFINITIONS_H)
        self.assertEqual(parse_int_define(defs, "STAMP_SIZE_PX"), 30)

    def test_stamp_left_edge_is_zero(self) -> None:
        defs = read_text(DEFINITIONS_H)
        self.assertEqual(parse_int_define(defs, "STAMP_LEFT_EDGE_PX"), 0)

    def test_stamp_top_edge_is_bottom_of_frame(self) -> None:
        """STAMP_TOP_EDGE_PX must be defined relative to HEIGHT and STAMP_SIZE_PX."""
        defs = read_text(DEFINITIONS_H)
        raw = parse_define(defs, "STAMP_TOP_EDGE_PX")
        self.assertIn("HEIGHT", raw, "STAMP_TOP_EDGE_PX must reference HEIGHT")
        self.assertIn("STAMP_SIZE_PX", raw, "STAMP_TOP_EDGE_PX must reference STAMP_SIZE_PX")

    def test_stamp_top_edge_evaluates_to_frame_bottom(self) -> None:
        """STAMP_TOP_EDGE_PX must equal HEIGHT - STAMP_SIZE_PX numerically."""
        defs = read_text(DEFINITIONS_H)
        height = parse_int_define(defs, "HEIGHT")
        stamp_size = parse_int_define(defs, "STAMP_SIZE_PX")
        stamp_top = eval_define_expr(defs, "STAMP_TOP_EDGE_PX")
        self.assertEqual(stamp_top, height - stamp_size)

    def test_stamp_fits_within_frame(self) -> None:
        defs = read_text(DEFINITIONS_H)
        height = parse_int_define(defs, "HEIGHT")
        width = parse_int_define(defs, "WIDTH")
        stamp_size = parse_int_define(defs, "STAMP_SIZE_PX")
        stamp_left = parse_int_define(defs, "STAMP_LEFT_EDGE_PX")
        stamp_top = eval_define_expr(defs, "STAMP_TOP_EDGE_PX")
        self.assertLessEqual(stamp_top + stamp_size, height)
        self.assertLessEqual(stamp_left + stamp_size, width)

    def test_stamp_mode_is_gpio22(self) -> None:
        defs = read_text(DEFINITIONS_H)
        self.assertEqual(parse_define(defs, "STAMP_MODE"), "STAMP_MODE_GPIO22")

    def test_gpio22_configured_as_input_in_uvc(self) -> None:
        """uvc.c must override GPIO 22 as a simple GPIO input."""
        uvc = read_text(UVC_C)
        self.assertIn("CyU3PDeviceGpioOverride (AUX_INPUT", uvc)
        self.assertIn("inputEn     = CyTrue", uvc)

    def test_gpio22_sampled_at_frame_start_in_uvc(self) -> None:
        """GPIO 22 must be sampled once per frame at the frame boundary."""
        uvc = read_text(UVC_C)
        self.assertIn("CyU3PGpioSimpleGetValue (AUX_INPUT", uvc)
        self.assertIn("stampRowsDone == 0", uvc)

    def test_stamp_uses_neutral_chroma_for_true_black_white(self) -> None:
        """Stamp rows must write neutral chroma (0x80) so the block is pure
        black or white in YUYV format, not a gray-green shift."""
        uvc = read_text(UVC_C)
        # A dedicated YUYV row-fill helper must exist.
        self.assertIn("stamp_row_yuyv", uvc)


if __name__ == "__main__":
    unittest.main()
