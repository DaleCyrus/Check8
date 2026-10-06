import colorsys
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rgb(hex_color):
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(color):
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb(color)]
    return sum(c * weight for c, weight in zip(channels, (0.2126, 0.7152, 0.0722)))


class PaletteTests(unittest.TestCase):
    def test_authored_colors_are_white_or_orange(self):
        files = [ROOT / "app/static" / name for name in ("style.css", "neobrutal.css", "app.js")]
        files.extend((ROOT / "app/templates").rglob("*.html"))
        for file in files:
            source = file.read_text(encoding="utf-8")
            colors = [(color, rgb(color)) for color in re.findall(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", source)]
            for match in re.finditer(r"rgba?\(\s*(\d+)[, ]+\s*(\d+)[, ]+\s*(\d+)", source):
                colors.append((match.group(), tuple(int(c) / 255 for c in match.groups())))
            for label, channels in colors:
                with self.subTest(file=file.name, color=label):
                    if channels == (1, 1, 1):
                        continue
                    hue, _, saturation = colorsys.rgb_to_hls(*channels)
                    self.assertGreater(saturation, 0)
                    self.assertTrue(14 <= hue * 360 <= 38, f"Non-orange color: {label}")

    def test_primary_text_and_control_contrast(self):
        pairs = [("#632600", "#ff822e"), ("#632600", "#fff"),
                 ("#98400e", "#ffdfc7"), ("#98400e", "#fff"),
                 ("#a8440b", "#fff"), ("#a83b06", "#fff")]
        for foreground, background in pairs:
            with self.subTest(foreground=foreground, background=background):
                light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
                self.assertGreaterEqual((light + 0.05) / (dark + 0.05), 4.5)


if __name__ == "__main__":
    unittest.main()
