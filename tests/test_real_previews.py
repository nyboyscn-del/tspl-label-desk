import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import preview
from labels import build_label
from tspl import Tspl, render_text_bitmap

PROFILE = {
    "dpi": 203,
    "bitmap_invert": False,
    "density": 8,
    "calibration": {"width_mm": 60, "height_mm": 40, "gap_mm": 2},
}


def test_chinese_code128_and_qr_render_as_real_symbols():
    assert preview.barcode_get is not None and preview.qrcode is not None
    job = build_label(["中文预览", "样本 123"], PROFILE, barcode="TSPL-128", qr="https://example.invalid/qr")
    image = preview.render(job, scale=1, margin=0)
    elements = {element[0]: element for element in job.elements if element[0] != "img"}

    text = job.elements[0][3]
    assert text.getbbox() is not None
    assert render_text_bitmap("中文").tobytes() != render_text_bitmap("测试").tobytes()

    _, x, y, content, height, readable, narrow = elements["bc128"]
    width = (11 * len(content) + 35) * narrow
    barcode = image.crop((x, y + 2, x + width, y + height - (24 if readable else 0)))
    transitions = max(
        sum(barcode.getpixel((i, row)) != barcode.getpixel((i - 1, row)) for i in range(1, barcode.width))
        for row in range(barcode.height)
    )
    assert transitions >= 10

    _, x, y, content, cell, _ecc = elements["qr"]
    matrix = preview.qrcode.QRCode(error_correction=preview.ERROR_CORRECT_H, border=0)
    matrix.add_data(content)
    matrix.make(fit=True)
    side = len(matrix.get_matrix()) * cell
    qr = image.crop((x, y, x + side, y + side))
    assert qr.getextrema() == (0, 255)


@pytest.mark.parametrize("kind", ["bc128", "qr"])
def test_missing_symbol_renderer_fails_loudly(kind, monkeypatch):
    job = Tspl(60, 40)
    if kind == "bc128":
        job.barcode128(10, 10, "TEST-128")
        monkeypatch.setattr(preview, "barcode_get", None)
    else:
        job.qrcode(10, 10, "TEST-QR")
        monkeypatch.setattr(preview, "qrcode", None)
    with pytest.raises(RuntimeError, match="preview requires"):
        preview.render(job)
