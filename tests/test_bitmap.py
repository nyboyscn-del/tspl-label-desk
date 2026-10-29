import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))
from PIL import Image
from tspl import bitmap_bytes, mm, Tspl, render_text_bitmap
from preview import render

def test_golden_msb_first_and_padding():
    im=Image.new('1',(9,1),0); im.putpixel((0,0),1); im.putpixel((8,0),1)
    n,data=bitmap_bytes(im)
    assert n==2 and data==bytes([0x80,0x80])

def test_inversion_is_full_byte_and_row_padding():
    im=Image.new('1',(9,1),0); im.putpixel((0,0),1)
    n,data=bitmap_bytes(im,invert=True)
    assert n==2 and data==bytes([0x7f,0xff])

def test_pure_black_white_and_checkerboard_padding_semantics():
    black=Image.new('1',(9,1),0);white=Image.new('1',(9,1),1)
    checker=Image.new('1',(9,1),0)
    for x in range(0,9,2):checker.putpixel((x,0),1)
    assert bitmap_bytes(black)==(2,b'\x00\x00')
    assert bitmap_bytes(white)==(2,b'\xff\x80')
    assert bitmap_bytes(checker)==(2,b'\xaa\x80')
    assert bitmap_bytes(checker,invert=True)==(2,b'\x55\x7f')

def test_chinese_bitmap_uses_pillow_row_packing_and_default_conversion():
    image=render_text_bitmap('中文标签',size=28,bold=True)
    row_bytes,data=bitmap_bytes(image,invert=True)
    assert row_bytes==(image.width+7)//8
    assert len(data)==row_bytes*image.height
    assert any(byte != 0xff for byte in data)

def test_480x320_bulk_packing_matches_original_pixel_loop():
    image=Image.frombytes('1',(480,320),bytes([0xaa,0x55,0xf0,0x0f])* (480//8*320//4))
    row_bytes,actual=bitmap_bytes(image,invert=True)
    expected=bytearray(row_bytes*image.height)
    for y in range(image.height):
        for x in range(image.width):
            if image.getpixel((x,y)) != 0:
                expected[y*row_bytes+x//8] |= 0x80 >> (x%8)
    expected=bytes(byte ^ 0xff for byte in expected)
    assert actual==expected

def test_dpi_conversion():
    assert mm(25.4,203)==203
    assert mm(25.4,300)==300

def test_tspl_bitmap_declares_padded_byte_width():
    job=Tspl(20,10); job.image(0,0,Image.new('1',(9,2),0))
    data=job.bytes()
    assert b'BITMAP 0,0,2,2,0,' in data
    assert len(data.split(b'BITMAP 0,0,2,2,0,',1)[1].split(b'\n',1)[0])==4

def test_preview_and_label_geometry_at_both_dpi_values():
    for dpi in (203,300):
        job=Tspl(60,40,dpi=dpi)
        assert (job.w,job.h)==(mm(60,dpi),mm(40,dpi))
        assert render(job,scale=1,margin=0).size==(job.w,job.h)
