"""Create a no-print polarity and geometry check sheet (PNG + TSPL)."""
import argparse
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from tspl import Tspl, mm
from preview import save

def build(dpi=203):
    # Match the public profile's standard glyph-mask to BITMAP conversion.
    t = Tspl(60, 40, dpi=dpi, invert_bitmap=True)
    w, h = t.w, t.h
    t.line(0, 0, w, 2); t.line(0, h - 2, w, 2)
    t.line(0, 0, 2, h); t.line(w - 2, 0, 2, h)
    # Filled black patch, white hole, and one-dot geometry are explicit bitmap bytes.
    patch = Image.new("1", (32, 24), 1); ImageDraw.Draw(patch).rectangle((6, 6, 25, 17), fill=0)
    t.image(mm(3,dpi), mm(3,dpi), patch)
    checker = Image.new("1", (16, 16), 0); px=checker.load()
    for y in range(16):
        for x in range(16): px[x,y] = (x+y)%2
    t.image(mm(10,dpi), mm(3,dpi), checker)
    one = Image.new("1", (9, 9), 0); ImageDraw.Draw(one).line((0,0,8,8), fill=1, width=1)
    t.image(mm(20,dpi), mm(3,dpi), one)
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    font_path = next((p for p in (windows/'Fonts'/'msyh.ttc', windows/'Fonts'/'simsun.ttc', windows/'Fonts'/'simhei.ttf') if p.exists()), None)
    font = ImageFont.truetype(str(font_path), 20) if font_path else ImageFont.load_default()
    sample = "中文样本 TSPL" if font_path else "CJK FONT MISSING - install/select a CJK font"
    bbox=font.getbbox(sample); text=Image.new("1",(bbox[2]-bbox[0]+4,bbox[3]-bbox[1]+4),0)
    ImageDraw.Draw(text).text((2-bbox[0],2-bbox[1]),sample,fill=1,font=font)
    t.image(mm(3,dpi), mm(12,dpi), text)
    # Five-millimetre ruler ticks and a centre locator help physical measurement.
    for pos in range(5, 56, 5):
        x=mm(pos,dpi); tick=mm(2 if pos%10==0 else 1,dpi)
        t.line(x,mm(1,dpi),1,tick)
    cx,cy=w//2,h//2
    t.line(cx-mm(2,dpi),cy,mm(4,dpi),1); t.line(cx,cy-mm(2,dpi),1,mm(4,dpi))
    label=Image.new("1",(130,22),0); ImageDraw.Draw(label).text((1,1),f"60x40mm {dpi}dpi",fill=1,font=ImageFont.load_default())
    t.image(mm(35,dpi),mm(12,dpi),label)
    # Native BARCODE test remains a TSPL command, distinct from bitmap polarity tests.
    t.barcode128(mm(3,dpi), mm(21,dpi), "TEST-128", height=mm(10,dpi), readable=1)
    t.qrcode(mm(41,dpi), mm(21,dpi), "TSPL-TEST-QR", cell=3)
    return t.print_cmd(1)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dpi',type=int,choices=(203,300),default=203)
    ap.add_argument('--out',default='polarity-check'); ap.add_argument('--print',dest='do_print',action='store_true')
    ap.add_argument('--printer',help='Windows queue name (required with --print)'); a=ap.parse_args()
    base=Path(a.out); base.parent.mkdir(parents=True, exist_ok=True)
    job=build(a.dpi); save(job,str(base.with_suffix('.png')))
    base.with_suffix('.tspl').write_bytes(job.bytes())
    if a.do_print:
        if not a.printer: ap.error('--printer is required with --print')
        import win32print
        handle=win32print.OpenPrinter(a.printer)
        try:
            win32print.StartDocPrinter(handle,1,('TSPL polarity check',None,'RAW')); win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle,job.bytes()); win32print.EndPagePrinter(handle); win32print.EndDocPrinter(handle)
        finally: win32print.ClosePrinter(handle)
    print(f"Wrote {base.with_suffix('.png')} and {base.with_suffix('.tspl')}; print={'yes' if a.do_print else 'no'}")

if __name__=='__main__': main()
