"""Local TSPL label desk. Loopback/file output are defaults; LAN and Windows RAW are opt-in."""
from __future__ import annotations
import argparse,copy,hashlib,html,json,os,secrets,shutil,sys,threading,time,webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from labels import build_label,build_probe
from preview import render

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'static'
QUICK_TEMPLATES_PATH=ROOT/'profiles'/'quick-label-templates.json'
DEFAULT_MODELS=[{"label":"Sample model A","tag":"SAMPLE-A"},{"label":"Sample model B","tag":"SAMPLE-B"}]
DEFAULT_PROFILE={"printer_model":"Generic TSPL printer (unverified)","dpi":203,"dots_per_mm":8.0,
 "supported_commands":["BITMAP","BAR","BARCODE 128","QRCODE"],"printer_queue":None,
 "calibration":{"width_mm":60,"height_mm":40,"gap_mm":2,"source":"assumed"},
 "verification_status":"UNVERIFIED","bitmap_invert":True,"density":8,"config_version":2}
LEGACY_DEFAULT_PROFILE={"printer_model":"Generic TSPL printer (unverified)","dpi":203,"dots_per_mm":8.0,
 "supported_commands":["BITMAP","BAR","BARCODE 128","QRCODE"],"printer_queue":None,
 "calibration":{"width_mm":60,"height_mm":40,"gap_mm":2,"source":"assumed"},
 "verification_status":"UNVERIFIED","bitmap_invert":False,"density":8}
PROFILE_CONFIG_VERSION=2
MAX_BODY=65536

class LimitedHTTPServer(ThreadingHTTPServer):
 def __init__(self,*args,**kwargs):
  self._slots=threading.BoundedSemaphore(32);super().__init__(*args,**kwargs)
 def process_request(self,request,client_address):
  if not self._slots.acquire(blocking=False):request.close();return
  try:super().process_request(request,client_address)
  except Exception:self._slots.release();raise
 def process_request_thread(self,request,client_address):
  try:super().process_request_thread(request,client_address)
  finally:self._slots.release()

class LabelDesk:
 def __init__(self,state_dir=None,backend="file",lan=False,token=None):
  self.state=Path(state_dir or os.environ.get("TSPL_LABEL_DESK_HOME",ROOT/'.runtime-data')).resolve()
  self.state.mkdir(parents=True,exist_ok=True);self.outbox=self.state/'outbox';self.outbox.mkdir(exist_ok=True)
  self.backend=backend;self.lan=lan;self.token=token;self.limits={};self.lock=threading.Lock()
  self.models=self._read("models.json",{"models":DEFAULT_MODELS})
  profile_path=self.state/'profile.json';existing_profile=profile_path.is_file()
  self.profile=self._read("profile.json",DEFAULT_PROFILE)
  if existing_profile and self.profile.get("config_version")!=PROFILE_CONFIG_VERSION:
   if self.profile==LEGACY_DEFAULT_PROFILE:
    original=profile_path.read_bytes();digest=hashlib.sha256(original).hexdigest()[:12]
    backup=profile_path.with_name(f"profile.json.pre-r5-{digest}.bak")
    if not backup.exists(): shutil.copy2(profile_path,backup)
    self.profile["bitmap_invert"]=DEFAULT_PROFILE["bitmap_invert"]
   else:
    self.profile.setdefault("bitmap_invert",False)
   self.profile["config_version"]=PROFILE_CONFIG_VERSION
   self._write("profile.json",self.profile)
  self.paper=self._read("paper.json",{"width_mm":60,"height_mm":40,"gap_mm":2,"source":"assumed"})
  # Profile calibration is authoritative; paper.json is a compatibility mirror.
  if self.paper != self.profile["calibration"]:
   paper_path=self.state/'paper.json';original=paper_path.read_bytes();digest=hashlib.sha256(original).hexdigest()[:12]
   backup=paper_path.with_name(f"paper.json.pre-r5-{digest}.bak")
   if not backup.exists():shutil.copy2(paper_path,backup)
   self.paper=copy.deepcopy(self.profile["calibration"]);self._write("paper.json",self.paper)
  self.quick_templates=self._load_quick_templates()
  self._validate_models(self.models);self._validate_profile(self.profile)
 def _load_quick_templates(self):
  try:data=json.loads(QUICK_TEMPLATES_PATH.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError) as exc:raise ValueError("Invalid quick-label template configuration") from exc
  templates=data.get("templates") if isinstance(data,dict) else None
  if not isinstance(templates,list) or not templates:raise ValueError("quick-label templates must be a non-empty list")
  for template in templates:
   dims=template.get("dimensions")
   if not isinstance(dims,list) or not 1<=len(dims)<=3:raise ValueError("each quick-label template needs 1..3 dimensions")
   for dim in dims:
    if not isinstance(dim.get("options"),list) or not dim["options"]:raise ValueError("each quick-label dimension needs preset options")
  return data
 def compose_quick_label(self,data):
  template=next((t for t in self.quick_templates["templates"] if t["id"]==data.get("template_id")),None)
  if template is None:raise ValueError("unknown quick-label template")
  model=data.get("model","").strip()
  if not 1<=len(model)<=100:raise ValueError("choose a model or product")
  selected=[]
  choices=data.get("choices")
  if not isinstance(choices,dict):raise ValueError("dimension choices are required")
  for dim in template["dimensions"]:
   value=choices.get(dim["key"])
   option=next((o for o in dim["options"] if o["value"]==value),None)
   if option is None:raise ValueError(f"choose a preset for {dim['label']}")
   selected.append(f"{dim['label']}: {option['label']}")
  lines=[model,*selected]
  return {"lines":lines,"copies":int(data.get("copies",1)),"barcode":"","qr":""}
 def _read(self,name,default):
  path=self.state/name
  if not path.exists():
   value=copy.deepcopy(default);self._write(name,value);return value
  try:return json.loads(path.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError) as exc: raise ValueError(f"Invalid local {name}; back it up and repair it") from exc
 def _write(self,name,data):
  path=self.state/name;tmp=path.with_suffix(path.suffix+'.tmp')
  tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");os.replace(tmp,path)
 def _validate_models(self,data):
  items=data.get("models") if isinstance(data,dict) else None
  if not isinstance(items,list) or not 1<=len(items)<=500: raise ValueError("models must contain 1..500 entries")
  for item in items:
   if not isinstance(item,dict) or not all(isinstance(item.get(k),str) and 1<=len(item[k].strip())<=100 for k in ("label","tag")): raise ValueError("each model needs label/tag of 1..100 characters")
 def _validate_profile(self,p):
  if p.get("dpi") not in (203,300): raise ValueError("dpi must be 203 or 300")
  p["dots_per_mm"]=8.0 if p["dpi"]==203 else p["dpi"]/25.4
  cal=p.setdefault("calibration",{})
  for key in ("width_mm","height_mm"):
   value=float(cal.get(key,60 if key=="width_mm" else 40))
   if not 10<=value<=200: raise ValueError("paper dimensions must be 10..200 mm")
   cal[key]=value
  cal["gap_mm"]=min(20,max(0,float(cal.get("gap_mm",2))))
  p["bitmap_invert"]=bool(p.get("bitmap_invert",False))
  queue=p.get("printer_queue")
  if queue is not None and (not isinstance(queue,str) or len(queue)>256 or any(ord(c)<32 for c in queue)): raise ValueError("invalid printer queue name")
  p.setdefault("printer_model","Generic TSPL printer (unverified)")
  p.setdefault("verification_status","UNVERIFIED")
 def put_models(self,data):
  self._validate_models(data);self._write("models.json",data);self.models=data
 def put_profile(self,data):
  data=copy.deepcopy(data);data["calibration"]=copy.deepcopy(self.profile["calibration"])
  self._validate_profile(data);self._write("profile.json",data);self.profile=data
 def put_paper(self,data):
  p={"width_mm":float(data["width_mm"]),"height_mm":float(data["height_mm"]),"gap_mm":float(data.get("gap_mm",2)),"source":"user_entered"}
  probe={**self.profile,"calibration":p};self._validate_profile(probe)
  self.paper=p;self.profile["calibration"]=p;self._write("paper.json",p);self._write("profile.json",self.profile)
 def job_from(self,data):
  lines=data.get("lines")
  if not isinstance(lines,list): raise ValueError("lines must be a list")
  if any(len(str(line))>120 for line in lines): raise ValueError("each line is limited to 120 characters")
  barcode=str(data.get("barcode", ""));qr=str(data.get("qr", ""));copies=int(data.get("copies",1))
  if len(barcode)>24 or any(not 32<=ord(c)<=126 for c in barcode):raise ValueError("Code128 is limited to 24 printable ASCII characters")
  if len(qr)>180 or any(not 32<=ord(c)<=126 for c in qr):raise ValueError("QR input is limited to 180 printable ASCII characters")
  if not 1<=copies<=20:raise ValueError("copies must be 1..20")
  return build_label(lines,self.profile,barcode=barcode,qr=qr,copies=copies)
 def output(self,job,remote):
  if self.backend=="windows":
   queue=self.profile.get("printer_queue")
   if not queue: raise ValueError("Set a printer queue in the profile before printing")
   try: import win32print
   except ImportError as exc: raise RuntimeError("pywin32 is required for the Windows RAW backend") from exc
   handle=win32print.OpenPrinter(queue)
   try:
    doc=win32print.StartDocPrinter(handle,1,("tspl-label-desk",None,"RAW"))
    try:
     win32print.StartPagePrinter(handle);win32print.WritePrinter(handle,job.bytes());win32print.EndPagePrinter(handle)
    finally: win32print.EndDocPrinter(handle)
   finally: win32print.ClosePrinter(handle)
   return {"mode":"windows_raw","queue":queue}
  name=f"label-{int(time.time()*1000)}-{secrets.token_hex(3)}.tspl";path=self.outbox/name;path.write_bytes(job.bytes())
  return {"mode":"file","file":str(path.relative_to(self.state))}
 def authorized(self,handler):
  if self.lan and not secrets.compare_digest(handler.headers.get("X-TSPL-Token",""),self.token or ""): return False
  origin=handler.headers.get("Origin")
  if origin:
   parsed=urlparse(origin)
   if parsed.netloc.lower()!=handler.headers.get("Host","").lower() or parsed.scheme!="http": return False
  return True
 def allow_print(self,ip):
  now=time.monotonic()
  with self.lock:
   times=[t for t in self.limits.get(ip,[]) if now-t<60]
   if len(times)>=6:return False
   times.append(now);self.limits[ip]=times;return True

def make_handler(app):
 class Handler(BaseHTTPRequestHandler):
  server_version="TSPLLabelDesk/1";sys_version=""
  def setup(self):super().setup();self.connection.settimeout(10)
  def log_message(self,*args): pass
  def _send(self,status,body,ctype="application/json; charset=utf-8"):
   self.send_response(status);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(body)))
   self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff")
   self.send_header("Content-Security-Policy","default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
   self.end_headers();self.wfile.write(body)
  def _json(self,status,obj):self._send(status,json.dumps(obj,ensure_ascii=False).encode("utf-8"))
  def _auth(self):
   if app.authorized(self):return True
   self._json(401,{"error":"unauthorized"});return False
  def _body(self):
   try:n=int(self.headers.get("Content-Length","-1"))
   except ValueError:n=-1
   if n<0 or n>MAX_BODY:raise ValueError("request body missing or exceeds 64 KiB")
   if self.headers.get_content_type()!="application/json":raise ValueError("Content-Type must be application/json")
   return json.loads(self.rfile.read(n).decode("utf-8"))
  def do_GET(self):
   path=urlparse(self.path).path
   if path in ("/models","/api/models"):path="/api/models"
   if path in ("/paper","/api/paper"):path="/api/paper"
   if path=="/":
    data=(STATIC/'index.html').read_bytes();self._send(200,data,"text/html; charset=utf-8");return
   if path in ("/app.js","/app.css"):
    data=(STATIC/path.lstrip('/')).read_bytes();ctype="text/javascript; charset=utf-8" if path.endswith('.js') else "text/css; charset=utf-8";self._send(200,data,ctype);return
   if not self._auth():return
   if path=="/api/models":self._json(200,app.models);return
   if path=="/api/profile":self._json(200,app.profile);return
   if path=="/api/paper":self._json(200,app.paper);return
   if path=="/api/status":self._json(200,{"backend":app.backend,"lan":app.lan,"profile_status":app.profile.get("verification_status","UNVERIFIED")});return
   if path=="/api/quick-templates":self._json(200,app.quick_templates);return
   if path in ("/api/preview","/api/probe-preview"):
    try:
     query=parse_qs(urlparse(self.path).query)
     job=build_probe(app.profile) if path.endswith("probe-preview") else app.job_from(json.loads(query.get('job',['{}'])[0]))
     import io
     buffer=io.BytesIO();render(job).save(buffer,format="PNG");self._send(200,buffer.getvalue(),"image/png")
    except Exception as e:self._json(400,{"error":str(e)[:300]})
    return
   self._json(404,{"error":"not found"})
  def do_POST(self):
   if not self._auth():return
   path=urlparse(self.path).path
   path={"/print":"/api/print","/models":"/api/models","/paper":"/api/paper"}.get(path,path)
   if path not in ("/api/preview","/api/print","/api/models","/api/paper","/api/profile","/api/probe-output","/api/quick-compose"):
    self._json(404,{"error":"not found"});return
   try:
    data=self._body()
    if path=="/api/quick-compose":self._json(200,app.compose_quick_label(data));return
    if path=="/api/preview":
     job=app.job_from(data);import io
     buffer=io.BytesIO();render(job).save(buffer,format="PNG");self._send(200,buffer.getvalue(),"image/png");return
    if path=="/api/models":app.put_models(data);self._json(200,{"ok":True,"count":len(data['models'])});return
    if path=="/api/profile":app.put_profile(data);self._json(200,{"ok":True,"profile":app.profile});return
    if path=="/api/paper":app.put_paper(data);self._json(200,{"ok":True,"paper":app.paper});return
    if not app.allow_print(self.client_address[0]):self._json(429,{"error":"print rate limit exceeded (6/minute)"});return
    job=build_probe(app.profile) if path.endswith("probe-output") else app.job_from(data)
    self._json(200,{"ok":True,**app.output(job,self.client_address[0])})
   except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:self._json(400,{"error":str(e)[:300]})
   except Exception as e:self._json(500,{"error":str(e)[:300]})
 def log_message(self,*args):pass
 return Handler

def main(argv=None):
 parser=argparse.ArgumentParser(description="Local TSPL label desk")
 parser.add_argument("--host",default="127.0.0.1",help="bind address; --lan is required for non-loopback")
 parser.add_argument("--port",type=int,default=8630);parser.add_argument("--lan",action="store_true",help="allow LAN binding and require bearer token")
 parser.add_argument("--backend",choices=("file","windows"),default="file",help="file output by default; windows sends RAW jobs")
 parser.add_argument("--state-dir",type=Path);parser.add_argument("--no-browser",action="store_true");args=parser.parse_args(argv)
 is_loopback=args.host in ("127.0.0.1","::1","localhost")
 if not is_loopback and not args.lan: parser.error("non-loopback binding requires --lan")
 if args.lan and is_loopback: parser.error("--lan requires a non-loopback --host, e.g. 0.0.0.0")
 if not 1024<=args.port<=65535:parser.error("port must be in 1024..65535")
 token=secrets.token_urlsafe(24) if args.lan else None
 app=LabelDesk(args.state_dir,args.backend,args.lan,token)
 server=LimitedHTTPServer((args.host,args.port),make_handler(app));server.daemon_threads=True
 url=f"http://127.0.0.1:{args.port}/" if is_loopback else f"http://{args.host}:{args.port}/"
 print(f"TSPL Label Desk listening at {url}; backend={args.backend}; state={app.state}")
 if args.lan:
  import socket
  ips=sorted({row[4][0] for row in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not row[4][0].startswith('127.')})
  print("LAN addresses (use only on a trusted network): "+", ".join(f"http://{ip}:{args.port}/" for ip in ips))
  print(f"LAN bearer token (share only with trusted users): {token}")
 if not args.no_browser and is_loopback:webbrowser.open(url)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
 return 0

if __name__=="__main__":raise SystemExit(main())
