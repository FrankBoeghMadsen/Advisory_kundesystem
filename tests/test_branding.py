import hashlib
from pathlib import Path
import tomllib
import unittest

from PIL import Image


class BrandingTests(unittest.TestCase):
    def test_manual_palette_and_original_logo(self):
        root=Path(__file__).resolve().parents[1]
        theme=tomllib.loads((root/'.streamlit/config.toml').read_text())['theme']
        self.assertEqual(theme['primaryColor'],'#000080')
        self.assertEqual(theme['textColor'],'#1F2933')
        self.assertEqual(theme['backgroundColor'],'#FFFFFF')
        self.assertEqual(theme['secondaryBackgroundColor'],'#F7F5EF')
        logo=root/'assets/advisory-compass.png'
        self.assertEqual(hashlib.sha256(logo.read_bytes()).hexdigest(),
                         '487bea6d1425add4b62fe8a9eeee7fbb3554d01cc6995c6dc534b770fb6df345')
        with Image.open(logo) as image:
            image.verify()
