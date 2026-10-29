"""Label layout and paper calibration card builders."""
from PIL import Image,ImageDraw
from tspl import Tspl,mm,fit_lines_bitmaps,render_text_bitmap

def build_label(lines,profile,*,barcode="",qr="",copies=1):
    lines=[str(line).strip() for line in lines if str(line).strip()]
    if not lines or len(lines)>5: raise ValueError("enter 1 to 5 non-empty lines")
    w=float(profile.get("calibration",{}).get("width_mm",60)); h=float(profile.get("calibration",{}).get("height_mm",40))
    dpi=int(profile.get("dpi",203))
    t=Tspl(w,h,gap_mm=float(profile.get("calibration",{}).get("gap_mm",2)),dpi=dpi,
           invert_bitmap=bool(profile.get("bitmap_invert",False)),density=int(profile.get("density",8)))
    margin=max(10,int(t.h*.035)); row=(t.h-2*margin)/len(lines)
    images=fit_lines_bitmaps(lines,t.w-2*margin,int(row*.9),bold=True)
    for index,image in enumerate(images):
        t.image((t.w-image.width)//2,int(margin+index*row+(row-image.height)/2),image)
    if barcode:
        y=max(margin,t.h-mm(13,dpi));t.barcode128(margin,y,barcode,height=mm(11,dpi),readable=1)
    if qr:
        cell=max(2,int(round(dpi/50.8)));side=mm(14,dpi);t.qrcode(t.w-margin-side,margin,qr,cell=cell)
    return t.print_cmd(copies)

def build_probe(profile):
    calibration=profile.get("calibration",{});w=float(calibration.get("width_mm",60));h=float(calibration.get("height_mm",40));dpi=int(profile.get("dpi",203))
    t=Tspl(w,h,dpi=dpi,invert_bitmap=bool(profile.get("bitmap_invert",False)))
    W,H=t.w,t.h;edge=mm(2,dpi);t.box(mm(.75,dpi),mm(.75,dpi),W-2*mm(.75,dpi),H-2*mm(.75,dpi),max(1,mm(.25,dpi)))
    for pos in range(0,int(w)+1,5):
        x=edge+mm(pos,dpi)
        if x>W-edge: break
        length=mm(2 if pos%10==0 else 1,dpi)
        t.line(x,edge,2 if dpi==203 else max(1,mm(.25,dpi)),length);t.line(x,H-edge-length,2 if dpi==203 else max(1,mm(.25,dpi)),length)
        if pos and pos%10==0:
            label=render_text_bitmap(str(pos),size=20 if dpi==203 else max(8,mm(2.5,dpi)),bold=True)
            t.image(x-label.width//2,edge+(18 if dpi==203 else mm(2.5,dpi)),label)
    for pos in range(0,int(h)+1,5):
        y=edge+mm(pos,dpi)
        if y>H-edge: break
        length=mm(2 if pos%10==0 else 1,dpi)
        t.line(edge,y,length,2 if dpi==203 else max(1,mm(.25,dpi)));t.line(W-edge-length,y,length,2 if dpi==203 else max(1,mm(.25,dpi)))
        if pos and pos%10==0:
            label=render_text_bitmap(str(pos),size=20 if dpi==203 else max(8,mm(2.5,dpi)),bold=True)
            t.image(edge+(18 if dpi==203 else mm(2.5,dpi)),y-label.height//2,label)
    cx,cy=W//2,H//2;cross=20 if dpi==203 else mm(2,dpi);thin=2 if dpi==203 else max(1,mm(.25,dpi))
    t.line(cx-cross,cy,cross*2,thin);t.line(cx,cy-cross,thin,cross*2)
    label=render_text_bitmap(f"{w:g}x{h:g}mm" if dpi==203 else f"{w:g} x {h:g} mm / {dpi} DPI",size=28 if dpi==203 else max(10,mm(3,dpi)),bold=True)
    t.image(max(edge,(W-label.width)//2),cy-label.height-(34 if dpi==203 else mm(4,dpi)),label)
    if dpi==203:
        label2=render_text_bitmap("标定卡",size=24,bold=True);t.image((W-label2.width)//2,cy+34,label2)
    return t.print_cmd(1)
