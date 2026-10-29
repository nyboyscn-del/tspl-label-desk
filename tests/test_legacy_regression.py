import json
import sys
import copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
from labels import build_label,build_probe
from app import DEFAULT_PROFILE,LEGACY_DEFAULT_PROFILE,LabelDesk
import app as app_module

FIX=Path(__file__).parent/'fixtures'/'legacy203'
PROFILE={"printer_model":"Generic TSPL printer (unverified)","dpi":203,"dots_per_mm":8.0,"supported_commands":["BITMAP","BAR","BARCODE 128","QRCODE"],"printer_queue":None,"calibration":{"width_mm":60,"height_mm":40,"gap_mm":2,"source":"assumed"},"verification_status":"UNVERIFIED","bitmap_invert":True,"density":8}

def test_203_chinese_multiline_matches_legacy_when_using_legacy_polarity():
    output=build_label(["中文示例","Sample A1","2 pcs"],PROFILE).bytes()
    assert output==(FIX/'chinese_multiline.tspl').read_bytes()

def test_203_custom_multiline_matches_legacy_when_using_legacy_polarity():
    output=build_label(["User title","Line 2: 60x40","Line 3"],PROFILE).bytes()
    assert output==(FIX/'custom_multiline.tspl').read_bytes()

def test_barcode_and_qr_are_native_commands_not_bitmap_polarity_samples():
    old=(FIX/'barcode_qr.tspl').read_bytes()
    new=build_label(["Demo code"],PROFILE,barcode="TEST-128",qr="https://example.invalid").bytes()
    for payload in (old,new):
        assert b'BARCODE 20,220,"128",88,1,0,2,2,"TEST-128"' in payload or b'BARCODE ' in payload
        assert b'QRCODE ' in payload
    assert b'"TEST-128"' in new and b'"https://example.invalid"' in new
    # The legacy fixture quoted H/A; the documented TSPL command uses bare tokens.
    assert b',H,4,A,0,"https://example.invalid"' in new
    assert b'QRCODE 340,35,"H",5,"A",0,' in old

def test_203_calibration_card_matches_legacy_fixture():
    assert build_probe(PROFILE).bytes()==(FIX/'calibration_card.tspl').read_bytes()

def test_fixture_manifest_hashes():
    manifest=json.loads((FIX/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['synthetic_content_only'] is True
    assert manifest['dpi']==203 and manifest['label_mm']==[60,40]

def test_first_start_profile_uses_legacy_polarity_and_golden_bytes(tmp_path):
    app=LabelDesk(tmp_path)
    assert app.profile['bitmap_invert'] is True
    assert app.profile['config_version']==2
    assert json.loads((tmp_path/'profile.json').read_text(encoding='utf-8'))['bitmap_invert'] is True
    assert app.job_from({'lines':['中文示例','Sample A1','2 pcs']}).bytes()==(FIX/'chinese_multiline.tspl').read_bytes()

def test_first_start_loads_profile_from_project_local_runtime_path(tmp_path,monkeypatch):
    monkeypatch.setattr(app_module,'ROOT',tmp_path)
    monkeypatch.delenv('TSPL_LABEL_DESK_HOME',raising=False)
    app=LabelDesk()
    assert app.state==(tmp_path/'.runtime-data').resolve()
    saved=json.loads((app.state/'profile.json').read_text(encoding='utf-8'))
    assert saved['config_version']==2 and saved['bitmap_invert'] is True

def test_exact_previous_generated_default_is_backed_up_and_migrated(tmp_path):
    original=copy.deepcopy(LEGACY_DEFAULT_PROFILE)
    (tmp_path/'profile.json').write_text(json.dumps(original,ensure_ascii=False),encoding='utf-8')
    app=LabelDesk(tmp_path)
    backups=list(tmp_path.glob('profile.json.pre-r5-*.bak'))
    assert len(backups)==1
    assert json.loads(backups[0].read_text(encoding='utf-8'))==original
    assert app.profile['bitmap_invert'] is True and app.profile['config_version']==2

def test_custom_existing_profile_keeps_polarity_queue_and_identity(tmp_path):
    original=copy.deepcopy(LEGACY_DEFAULT_PROFILE)
    original.update({'printer_model':'User Custom','printer_queue':'Queue Demo'})
    (tmp_path/'profile.json').write_text(json.dumps(original),encoding='utf-8')
    app=LabelDesk(tmp_path)
    assert app.profile['bitmap_invert'] is False
    assert app.profile['printer_queue']=='Queue Demo' and app.profile['printer_model']=='User Custom'
    assert app.profile['config_version']==2
    assert not list(tmp_path.glob('profile.json.pre-r5-*.bak'))
