"""Preview renderer for the supported bitmap and rectangle subset."""
from PIL import Image, ImageDraw
try:
    from barcode import get as barcode_get
    from barcode.writer import ImageWriter
except ImportError:
    barcode_get = ImageWriter = None
try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
except ImportError:
    qrcode = ERROR_CORRECT_H = None

def render(job, scale=3, margin=12):
    canvas = Image.new("L", (job.w, job.h), 255)
    for el in job.elements:
        if el[0] == "img":
            _, x, y, image = el
            mask = image.convert("1")
            canvas.paste(0, (x, y), mask)
        elif el[0] == "rect":
            _, x, y, w, h = el
            ImageDraw.Draw(canvas).rectangle((x, y, x + w - 1, y + h - 1), fill=0)
        elif el[0] == "bc128":
            _, x, y, content, height, readable, narrow = el
            if barcode_get is None:
                raise RuntimeError("Code128 preview requires python-barcode; install requirements.txt")
            try:
                raw = barcode_get("code128", content, writer=ImageWriter()).render()
                bars = raw.convert("L").point(lambda value: 255 if value < 128 else 0).convert("1")
                bw = (11 * len(content) + 35) * narrow
                bar_h = max(1, height - (24 if readable else 0))
                bars = bars.resize((max(1, bw), bar_h), Image.Resampling.NEAREST)
                canvas.paste(0, (x, y), bars)
            except Exception as exc:
                raise RuntimeError("Code128 preview rendering failed") from exc
        elif el[0] == "qr":
            _, x, y, content, cell, ecc = el
            if qrcode is None:
                raise RuntimeError("QR preview requires qrcode; install requirements.txt")
            try:
                corrections = {"L": qrcode.constants.ERROR_CORRECT_L,
                               "M": qrcode.constants.ERROR_CORRECT_M,
                               "Q": qrcode.constants.ERROR_CORRECT_Q,
                               "H": ERROR_CORRECT_H}
                code = qrcode.QRCode(error_correction=corrections[ecc], box_size=1, border=0)
                code.add_data(content)
                code.make(fit=True)
                matrix = code.get_matrix()
                size = len(matrix)
                symbol = Image.new("1", (size, size), 0)
                pixels = symbol.load()
                for row in range(size):
                    for col in range(size):
                        if matrix[row][col]:
                            pixels[col, row] = 1
                symbol = symbol.resize((size * cell, size * cell), Image.Resampling.NEAREST)
                canvas.paste(0, (x, y), symbol)
            except Exception as exc:
                raise RuntimeError("QR preview rendering failed") from exc
    result = canvas.resize((job.w * scale, job.h * scale), Image.Resampling.NEAREST)
    if margin:
        board = Image.new("L", (result.width + margin * 2, result.height + margin * 2), 255)
        board.paste(result, (margin, margin)); result = board
    return result

def save(job, path, scale=3):
    render(job, scale=scale).save(path)
    return path
