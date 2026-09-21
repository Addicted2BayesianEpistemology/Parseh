"""Video difficulty choices in both editor and stored metadata."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "youtube" / "lib"))
import ytpages  # noqa: E402


class VideoLevelTests(unittest.TestCase):
    def test_intermediate_variants_can_be_saved_and_chosen(self):
        player = (ROOT / "youtube" / "lib" / "player.html").read_text(encoding="utf-8")
        for level in ("lower-intermediate", "upper-intermediate"):
            self.assertIn(level, ytpages.LEVELS)
            self.assertIn('<option value="%s">%s</option>' % (level, level), player)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "video.json"
                path.write_text('{"title":"Lesson","level":"beginner"}', encoding="utf-8")
                self.assertEqual(level, ytpages.edit_meta(folder, {"level": level})["level"])
                self.assertEqual(level, json.loads(path.read_text(encoding="utf-8"))["level"])


if __name__ == "__main__":
    unittest.main()
