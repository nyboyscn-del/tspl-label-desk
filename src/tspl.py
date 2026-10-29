"""Small TSPL bitmap core. Bitmap pixels use 1=black; hardware polarity is a profile choice."""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def dots_per_mm(dpi: int) -> float:
    if dpi <= 0:
        raise ValueError("dpi must be positive")
    # The installed 203-class engines are 8 dots/mm (203.2 DPI); retain the
    # legacy raster grid. 300-DPI profiles use the exact nominal conversion.
    return 8.0 if dpi == 203 else dpi / 25.4

def mm(value: float, dpi: int = 203) -> int:
    return int(round(float(value) * dots_per_mm(dpi)))

def _pick_font(size: int, bold=False):
    font_dir=Path(os.environ.get("WINDIR", r"C:\Windows"))/"Fonts"
    names=("msyhbd.ttc","msyh.ttc","simhei.ttf") if bold else ("msyh.ttc","simsun.ttc","simhei.ttf")
    for name in names:
        path=font_dir/name
        if path.exists():
            try: return ImageFont.truetype(str(path),size)
            except OSError: pass
    return ImageFont.load_default()

def render_text_bitmap(content: str, size=28, bold=False, padding=2, stroke=0):
    font=_pick_font(size,bold)
    probe=ImageDraw.Draw(Image.new("1",(8,8)))
    l,t,r,b=probe.textbbox((0,0),content,font=font,stroke_width=stroke)
    pad=padding+stroke
    image=Image.new("1",(max(1,r-l+2*pad),max(1,b-t+2*pad)),0)
    ImageDraw.Draw(image).text((-l+pad,-t+pad),content,fill=1,font=font,stroke_width=stroke,stroke_fill=1)
    return image

def fit_lines_bitmaps(lines, max_w, max_h, bold=False, stroke=0):
    if not lines: raise ValueError("at least one line is required")
    base=100
    probes=[render_text_bitmap(line,base,bold,stroke=stroke) for line in lines]
    scale=min(float(max_w)/image.width for image in probes)
    size=max(6,int(base*scale)); scaled_stroke=max(0,int(round(stroke*scale)))
    images=[render_text_bitmap(line,size,bold,stroke=scaled_stroke) for line in lines]
    if max(image.height for image in images)>max_h:
        scale=float(max_h)/max(image.height for image in images)
        images=[image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.LANCZOS).convert("1") for image in images]
    return images

def bitmap_bytes(img: Image.Image, *, invert: bool = False) -> tuple[int, bytes]:
    """Return row byte width and MSB-first, row-padded 1bpp data."""
    image = img.convert("1")
    width, height = image.size
    row_bytes = (width + 7) // 8
    # Pillow mode 1 packs each row MSB-first and pads each row to a byte.
    # Mode-1 set bits (white pixels) are this app's foreground mask bits.
    out = bytearray(image.tobytes())
    if len(out) != row_bytes * height:
        raise ValueError("unexpected 1-bit image row layout")
    if invert:
        for i in range(len(out)):
            out[i] ^= 0xFF
    return row_bytes, bytes(out)

class Tspl:
    def __init__(self, width_mm=60, height_mm=40, gap_mm=2, dpi=203, invert_bitmap=False, density=8, speed=4):
        self.dpi = int(dpi)
        if self.dpi not in (203,300): raise ValueError("supported software DPI values: 203 or 300")
        self.w, self.h = mm(width_mm, self.dpi), mm(height_mm, self.dpi)
        if not (10 <= width_mm <= 200 and 10 <= height_mm <= 200): raise ValueError("label dimensions must be 10..200 mm")
        self.invert_bitmap = bool(invert_bitmap)
        self.parts: list[bytes] = [(
            f"SIZE {width_mm:g} mm,{height_mm:g} mm\nGAP {gap_mm:g} mm,0 mm\n"
            f"DIRECTION 0\nDENSITY {int(density)}\nSPEED {int(speed)}\nREFERENCE 0,0\nCLS\n"
        ).encode("ascii")]
        self.elements: list[tuple] = []

    def image(self, x: int, y: int, img: Image.Image, mode=0):
        bw, data = bitmap_bytes(img, invert=self.invert_bitmap)
        self.parts.extend([f"BITMAP {x},{y},{bw},{img.height},{mode},".encode("ascii"), data, b"\n"])
        self.elements.append(("img", x, y, img.convert("1")))
        return self

    def line(self, x, y, w, h=1):
        self.parts.append(f"BAR {x},{y},{w},{h}\n".encode("ascii")); self.elements.append(("rect", x, y, w, h)); return self

    def box(self,x,y,w,h,thickness=2):
        self.line(x,y,w,thickness).line(x,y+h-thickness,w,thickness)
        self.line(x,y,thickness,h).line(x+w-thickness,y,thickness,h); return self

    def cjk(self,x,y,content,size=28,bold=False,max_w=None,max_h=None):
        image=render_text_bitmap(content,size,bold)
        if max_w and image.width>max_w:
            factor=max_w/image.width
            image=image.resize((max_w,max(1,int(image.height*factor))),Image.Resampling.LANCZOS).convert("1")
        if max_h and image.height>max_h:
            factor=max_h/image.height
            image=image.resize((max(1,int(image.width*factor)),max_h),Image.Resampling.LANCZOS).convert("1")
        return self.image(x,y,image)

    def qrcode(self,x,y,content,ecc="H",cell=5,mode="A",rot=0):
        safe="".join(ch if 32<=ord(ch)<=126 and ch!='"' else " " for ch in str(content))
        self.parts.append(f'QRCODE {x},{y},{ecc},{cell},{mode},{rot},"{safe}"\n'.encode("ascii","replace"))
        self.elements.append(("qr",x,y,safe,cell,ecc)); return self

    def barcode128(self, x, y, content, height=80, readable=1, rot=0, narrow=2, wide=2):
        safe = "".join(ch if 32<=ord(ch)<=126 and ch!='"' else " " for ch in str(content))
        self.parts.append(f'BARCODE {x},{y},"128",{height},{readable},{rot},{narrow},{wide},"{safe}"\n'.encode("ascii", "replace"))
        self.elements.append(("bc128", x, y, safe, height, readable, narrow)); return self

    def print_cmd(self, copies=1):
        if not 1 <= int(copies) <= 100:
            raise ValueError("copies must be between 1 and 100")
        self.parts.append(f"PRINT {int(copies)},1\n".encode("ascii")); return self

    def bytes(self): return b"".join(self.parts)
