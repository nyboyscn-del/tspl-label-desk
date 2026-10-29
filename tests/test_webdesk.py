import json,sys,threading,urllib.error,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
from app import LabelDesk,make_handler
from http.server import ThreadingHTTPServer

class Desk:
 def __init__(self,tmp_path,lan=False,backend='file'):
  self.app=LabelDesk(tmp_path,backend=backend,lan=lan,token='test-token' if lan else None)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.app));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.base=f'http://127.0.0.1:{self.server.server_port}'
 def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
 def request(self,path,method='GET',payload=None,token=None):
  data=None if payload is None else json.dumps(payload).encode()
  headers={}
  if data is not None:headers['Content-Type']='application/json'
  if token:headers['X-TSPL-Token']=token
  req=urllib.request.Request(self.base+path,data=data,headers=headers,method=method)
  try:
   with urllib.request.urlopen(req,timeout=5) as r:return r.status,r.headers.get('Content-Type'),r.read()
  except urllib.error.HTTPError as e:return e.code,e.headers.get('Content-Type'),e.read()

def test_web_ui_model_profile_preview_calibration_and_file_output(tmp_path):
 d=Desk(tmp_path)
 try:
  assert d.request('/')[0]==200 and d.request('/app.js')[0]==200
  assert d.request('/api/models')[0]==200
  templates=json.loads(d.request('/api/quick-templates')[2])['templates']
  assert len(templates[0]['dimensions'])==2 and len(templates[1]['dimensions'])==3
  status,_,body=d.request('/api/quick-compose','POST',{'template_id':'warehouse-bin','model':'Demo item','choices':{'aisle':'b','bin':'02','status':'inspect'}})
  composed=json.loads(body)
  assert status==200 and composed['lines']==['Demo item','Aisle: B','Bin: 02','Status: Inspect']
  status,ctype,png=d.request('/api/preview','POST',composed)
  assert status==200 and ctype=='image/png' and png.startswith(b'\x89PNG')
  assert d.request('/api/quick-compose','POST',{'template_id':'warehouse-bin','model':'Demo','choices':{'aisle':'invalid'}})[0]==400
  assert d.request('/api/models','POST',{'models':[{'label':'Demo model','tag':'DEMO-1'}]})[0]==200
  assert d.request('/api/profile','POST',{**d.app.profile,'dpi':300})[0]==200
  assert d.request('/api/paper','POST',{'width_mm':60,'height_mm':40,'gap_mm':2})[0]==200
  status,ctype,png=d.request('/api/preview','POST',{'lines':['中文示例','Line 2'],'barcode':'TEST-128','qr':'TEST-QR'})
  assert status==200 and ctype=='image/png' and png.startswith(b'\x89PNG')
  assert d.request('/api/probe-preview')[0]==200
  status,_,body=d.request('/api/print','POST',{'lines':['Demo label'],'copies':1})
  result=json.loads(body);assert status==200 and result['mode']=='file'
  output=(tmp_path/result['file']).read_bytes();assert b'PRINT 1,1' in output
  assert d.app.backend=='file'
 finally:d.close()

def test_lan_requires_token_for_print_model_and_paper_mutations(tmp_path):
 d=Desk(tmp_path,lan=True)
 try:
  for path,payload in [('/print',{'lines':['No auth']}),('/models',{'models':[{'label':'X','tag':'X'}]}),('/paper',{'width_mm':60,'height_mm':40})]:
   assert d.request(path,'POST',payload)[0]==401
  assert d.request('/api/models','POST',{'models':[{'label':'Authorized','tag':'OK'}]},token='test-token')[0]==200
  assert d.request('/api/print','POST',{'lines':['Authorized']},token='test-token')[0]==200
 finally:d.close()

def test_oversized_body_and_foreign_origin_rejected(tmp_path):
 d=Desk(tmp_path)
 try:
  request=urllib.request.Request(d.base+'/api/paper',data=b'{}',headers={'Content-Type':'application/json','Origin':'http://attacker.invalid'},method='POST')
  try:urllib.request.urlopen(request,timeout=5);assert False
  except urllib.error.HTTPError as e:assert e.code==401
  assert d.request('/api/print','POST',{'lines':['x']*7,'copies':99})[0]==400
 finally:d.close()

def test_windows_raw_backend_uses_mock_queue_only(tmp_path,monkeypatch):
 import types
 calls=[];fake=types.SimpleNamespace(OpenPrinter=lambda q:('handle',q),StartDocPrinter=lambda *a:(calls.append(('doc',a[2])) or 7),StartPagePrinter=lambda h:calls.append(('start_page',h)),WritePrinter=lambda h,b:calls.append(('write',bytes(b))),EndPagePrinter=lambda h:calls.append(('end_page',h)),EndDocPrinter=lambda *a:calls.append(('end_doc',a)),ClosePrinter=lambda h:calls.append(('close',h)))
 monkeypatch.setitem(sys.modules,'win32print',fake)
 app=LabelDesk(tmp_path,backend='windows');app.profile['printer_queue']='MOCK QUEUE'
 job=app.job_from({'lines':['Mock output']});result=app.output(job,'127.0.0.1')
 assert result=={'mode':'windows_raw','queue':'MOCK QUEUE'}
 assert any(call[0]=='write' and call[1]==job.bytes() for call in calls)

def test_windows_raw_requires_a_configured_queue(tmp_path):
 d=Desk(tmp_path,backend='windows')
 try:
  status,_,body=d.request('/api/print','POST',{'lines':['Synthetic test']})
  assert status==400 and json.loads(body)['error']=='Set a printer queue in the profile before printing', (status,body)
 finally:d.close()

def test_windows_raw_spooler_failure_returns_error_and_closes_queue(tmp_path,monkeypatch):
 import types
 calls=[]
 def start_doc(*_args):raise OSError('synthetic spooler failure')
 fake=types.SimpleNamespace(OpenPrinter=lambda q:('handle',q),StartDocPrinter=start_doc,ClosePrinter=lambda h:calls.append(('close',h)))
 monkeypatch.setitem(sys.modules,'win32print',fake)
 d=Desk(tmp_path,backend='windows');d.app.profile['printer_queue']='MOCK QUEUE'
 try:
  status,_,body=d.request('/api/print','POST',{'lines':['Synthetic test']})
  assert status==500 and json.loads(body)['error']=='synthetic spooler failure'
  assert calls==[('close',('handle','MOCK QUEUE'))]
 finally:d.close()

def test_profile_calibration_is_authoritative_and_stale_paper_is_backed_up(tmp_path):
 import hashlib
 app=LabelDesk(tmp_path)
 app.profile['calibration']={'width_mm':70.0,'height_mm':30.0,'gap_mm':3.0,'source':'user_entered'}
 app._write('profile.json',app.profile)
 stale={'width_mm':60,'height_mm':40,'gap_mm':2,'source':'assumed'}
 raw=json.dumps(stale,ensure_ascii=False,indent=2).encode('utf-8')
 (tmp_path/'paper.json').write_bytes(raw)
 app=LabelDesk(tmp_path)
 assert app.paper==app.profile['calibration']
 backup=tmp_path/f"paper.json.pre-r5-{hashlib.sha256(raw).hexdigest()[:12]}.bak"
 assert backup.read_bytes()==raw
 incoming={**app.profile,'calibration':{'width_mm':90,'height_mm':90,'gap_mm':0}}
 app.put_profile(incoming)
 assert app.profile['calibration']['width_mm']==70.0
