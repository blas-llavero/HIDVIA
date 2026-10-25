"""HIDVIA demonstration backend. NOT suitable for storing real patient health information.
Python 3.10+, standard library only. Binds to loopback by default.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import math
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / 'web'
DATA = Path(os.environ.get('HIDVIA_DATA', str(ROOT / 'demo_data'))).resolve()
DB_PATH = DATA / 'hidvia.sqlite3'
SESSION: dict[str, dict] = {}
MAX_BODY = 8_500_000

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def conn():
    c = sqlite3.connect(str(DB_PATH), timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 150000).hex()

def verify_password(password, stored):
    salt, expected = stored.split(':', 1)
    return hmac.compare_digest(password_hash(password, salt).split(':')[1], expected)

def seed():
    DATA.mkdir(parents=True, exist_ok=True)
    with conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, secret TEXT NOT NULL, role TEXT NOT NULL, patient_id INTEGER, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkins (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, created_at TEXT NOT NULL, pain REAL NOT NULL, itch REAL NOT NULL, swelling REAL NOT NULL, fatigue REAL NOT NULL, stress REAL NOT NULL, sleep REAL NOT NULL, drainage INTEGER NOT NULL, area TEXT NOT NULL, notes TEXT NOT NULL, score INTEGER NOT NULL, level TEXT NOT NULL, method TEXT NOT NULL, photo_id TEXT, sensor_json TEXT);
        CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, patient_id INTEGER NOT NULL, mime TEXT NOT NULL, bytes BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, checkin_id INTEGER NOT NULL, patient_id INTEGER NOT NULL, created_at TEXT NOT NULL, message TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS calibration (patient_id INTEGER PRIMARY KEY, pain REAL NOT NULL, swelling REAL NOT NULL, fatigue REAL NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, when_at TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, clinician TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL, seen INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS rna_readings (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, received_at TEXT NOT NULL, sampled_at TEXT NOT NULL, sample_id TEXT NOT NULL, source TEXT NOT NULL, device_id TEXT NOT NULL, units TEXT NOT NULL, qc_pass INTEGER NOT NULL, markers_json TEXT NOT NULL);
        ''')
        if 'sensor_json' not in [r['name'] for r in db.execute('PRAGMA table_info(checkins)')]:
            db.execute('ALTER TABLE checkins ADD COLUMN sensor_json TEXT')
        # The demo password is administered by Render, not by the browser's prefill.
        # Reconcile seeded fictional accounts when the environment secret is rotated.
        configured_demo_password = os.environ.get('HIDVIA_DEMO_PASSWORD')
        if configured_demo_password:
            for email in ('patient@hidvia.test', 'clinician@hidvia.test'):
                row = db.execute('SELECT secret FROM users WHERE email=?', (email,)).fetchone()
                if row and not verify_password(configured_demo_password, row['secret']):
                    db.execute('UPDATE users SET secret=? WHERE email=?',
                               (password_hash(configured_demo_password), email))
        if not db.execute('SELECT id FROM users LIMIT 1').fetchone():
            pwd = os.environ.get('HIDVIA_DEMO_PASSWORD', 'demo-pass-123')
            db.execute('INSERT INTO users (id,email,secret,role,patient_id,name) VALUES (1,?,?,?,?,?)', ('patient@hidvia.test',password_hash(pwd),'patient',1,'Demo Patient'))
            db.execute('INSERT INTO users (id,email,secret,role,patient_id,name) VALUES (2,?,?,?,?,?)', ('clinician@hidvia.test',password_hash(pwd),'clinician',None,'Demo Clinician'))
            today = datetime.now(timezone.utc)
            for days,pain,itch,swelling,fatigue,stress,sleep,drainage in [
                (6,2,2,1,2,3,7.5,0),(4,3,2,2,3,4,7,0),(2,3,3,2,3,5,6.5,0),(1,4,4,3,4,5,6,0)]:
                score,level,method = signal_score({'pain':pain,'itch':itch,'swelling':swelling,'fatigue':fatigue,'stress':stress,'sleep':sleep,'drainage':drainage}, [], None)
                db.execute('INSERT INTO checkins (patient_id,created_at,pain,itch,swelling,fatigue,stress,sleep,drainage,area,notes,score,level,method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (1,(today-timedelta(days=days)).isoformat(timespec='seconds'),pain,itch,swelling,fatigue,stress,sleep,drainage,'Underarm','Synthetic demonstration record',score,level,method))
            db.execute('INSERT INTO appointments (patient_id,when_at,title,created_at) VALUES (1,?,?,?)', ((today+timedelta(days=8)).isoformat(timespec='minutes'),'Dermatology follow-up',utcnow()))
            db.execute('INSERT INTO notifications (patient_id,kind,message,created_at) VALUES (1,?,?,?)', ('appointment','Dermatology follow-up scheduled in 8 days.',utcnow()))
            db.execute('INSERT INTO visits (patient_id,clinician,summary,created_at) VALUES (1,?,?,?)', ('Demo Clinician','Example record only. No clinical decision has been made.',utcnow()))

def clamp(value, default=0, lo=0, hi=10):
    try: return min(hi,max(lo,float(value)))
    except (ValueError,TypeError): return default

def signal_score(checkin, recent, calibration):
    """NON-VALIDATED research demonstrator, not a disease prediction."""
    p = clamp(checkin.get('pain')); s=clamp(checkin.get('swelling'))
    f=clamp(checkin.get('fatigue')); i=clamp(checkin.get('itch'))
    stress=clamp(checkin.get('stress')); sleep=clamp(checkin.get('sleep'),7,0,12)
    drainage = 1 if checkin.get('drainage') else 0
    # Transparent illustrative composite index. No claim of sensitivity/specificity.
    score = p*2.1 + s*2.6 + f*1.0 + i*0.9 + stress*0.45 + max(0,7.5-sleep)*2.3 + drainage*12
    if recent:
        score += max(0,p-float(recent[0]['pain']))*2.4
        score += max(0,s-float(recent[0]['swelling']))*2.4
    if calibration:
        score += max(0,p-float(calibration['pain']))*1.4
        score += max(0,s-float(calibration['swelling']))*1.6
    score = min(100, max(0, round(score)))
    level = 'high' if score>=65 else 'elevated' if score>=40 else 'low'
    return score, level, 'illustrative_heuristic_v1'

def ml_score(checkin, recent):
    """Opt-in exploratory model; never use as a clinical decision threshold."""
    model_path=os.environ.get('HIDVIA_MODEL_PATH','')
    if not model_path:return None
    path=Path(model_path)
    if not path.is_file():raise ValueError('Configured research model path is missing')
    artifact=json.loads(path.read_text(encoding='utf-8'))
    expected=['pain','itch','swelling','fatigue','stress','sleep','drainage','pain_delta','swelling_delta']
    if artifact.get('status')!='EXPERIMENTAL_UNVALIDATED' or artifact.get('features')!=expected:raise ValueError('Invalid research model metadata')
    p0=float(recent[0]['pain']) if recent else float(checkin['pain'])
    s0=float(recent[0]['swelling']) if recent else float(checkin['swelling'])
    vals=[float(checkin[k]) for k in expected[:7]]+[float(checkin['pain'])-p0,float(checkin['swelling'])-s0]
    logits=artifact['intercept']+sum(w*((v-m)/max(sc,1e-9)) for w,v,m,sc in zip(artifact['coef'],vals,artifact['mean'],artifact['scale']))
    # A rank score for the research UI. Thresholds are DEMO display labels, not treatment criteria.
    score=round(100/(1+math.exp(-max(-30,min(30,logits)))))
    return score, ('high' if score>=65 else 'elevated' if score>=40 else 'low'), 'research_logistic_regression_7d_unvalidated'

def valid_rna(data):
    """Provisional transport schema, NOT a vendor sensor protocol or a clinical RNA assay."""
    if data.get('schema') != 'hidvia-rna-v1':
        raise ValueError('Expected schema hidvia-rna-v1')
    markers=data.get('markers')
    if not isinstance(markers,dict) or not (1 <= len(markers) <= 40):
        raise ValueError('1 to 40 numeric marker values required')
    clean={}
    for key, value in markers.items():
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,48}',key):
            raise ValueError('Invalid marker identifier')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>1e9:
            raise ValueError('Marker values must be finite numeric assay outputs')
        clean[key]=float(value)
    if type(data.get('qc_pass')) is not bool:raise ValueError('Explicit boolean qc_pass required')
    stamp=str(data.get('sampled_at',''))
    try:
        dt=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        if not dt.tzinfo:raise ValueError()
    except ValueError:raise ValueError('sampled_at must be an ISO8601 timestamp with timezone')
    sample_id=str(data.get('sample_id',''))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',sample_id):raise ValueError('sample_id must be pseudonymous')
    source=str(data.get('source','file'))
    if source not in ('file','ble','serial','api'):raise ValueError('Unsupported source')
    device_id=str(data.get('device_id','unknown'))[:80]
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',device_id):raise ValueError('Invalid pseudonymous device ID')
    units=str(data.get('units','arbitrary'))
    if units not in ('arbitrary','counts','copies_per_ml','normalized_expression','ct'):raise ValueError('Unsupported units')
    return {'sampled_at':stamp,'sample_id':sample_id,'source':source,'device_id':device_id,'units':units,'qc_pass':int(data['qc_pass']),'markers_json':json.dumps(clean,sort_keys=True)}

def json_rows(rows): return [dict(r) for r in rows]

class Handler(BaseHTTPRequestHandler):
    server_version = 'HidviaDemo/0.2'
    def log_message(self, format, *args):
        super().log_message(format, *args)
    def respond(self, status, data):
        payload=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(payload)
    def input(self):
        n=int(self.headers.get('Content-Length','0'))
        if n<0 or n>MAX_BODY: raise ValueError('Payload too large')
        return json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
    def actor(self):
        auth=self.headers.get('Authorization','')
        token = auth[7:] if auth.startswith('Bearer ') else ''
        return SESSION.get(token)
    def require(self, role=None):
        actor=self.actor()
        if not actor: raise PermissionError('Please sign in')
        if role and actor['role']!=role: raise PermissionError('Not authorized for this role')
        return actor
    def path_and_query(self):
        u=urlparse(self.path)
        return u.path,parse_qs(u.query)
    def do_GET(self):
        try:
            path,qs=self.path_and_query()
            if path=='/api/health':return self.respond(200,{'ok':True,'mode':'research demo','brand':'HIDVIA'})
            if path.startswith('/api/'):
                actor=self.require()
                with conn() as db:
                    if path=='/api/me': return self.respond(200,actor)
                    if path=='/api/patients':
                        self.require('clinician')
                        return self.respond(200,json_rows(db.execute("SELECT id AS patient_id,name FROM users WHERE role='patient' ORDER BY id")))
                    if path=='/api/checkins':
                        pid=1 if actor['role']=='clinician' else actor['patient_id']
                        if actor['role']=='clinician':pid=int(qs.get('patient_id',[1])[0])
                        rows=db.execute('SELECT id,patient_id,created_at,pain,itch,swelling,fatigue,stress,sleep,drainage,area,notes,score,level,method,photo_id,sensor_json FROM checkins WHERE patient_id=? ORDER BY id DESC LIMIT 100',(pid,))
                        return self.respond(200,json_rows(rows))
                    if path=='/api/rna':
                        pid=actor['patient_id'] if actor['role']=='patient' else int(qs.get('patient_id',[1])[0])
                        return self.respond(200,json_rows(db.execute('SELECT * FROM rna_readings WHERE patient_id=? ORDER BY id DESC LIMIT 50',(pid,))))
                    if path=='/api/calibration':
                        self.require('patient')
                        row=db.execute('SELECT pain,swelling,fatigue,updated_at FROM calibration WHERE patient_id=?',(actor['patient_id'],)).fetchone()
                        return self.respond(200,dict(row) if row else {'calibrated':False})
                    if path=='/api/alerts':
                        self.require('clinician')
                        rows=db.execute('SELECT a.*,u.name AS patient_name FROM alerts a LEFT JOIN users u ON u.patient_id=a.patient_id AND u.role="patient" ORDER BY a.id DESC LIMIT 100')
                        return self.respond(200,json_rows(rows))
                    if path in ('/api/appointments','/api/results','/api/visits','/api/notifications'):
                        table=path.split('/')[-1]
                        if table=='notifications':self.require('patient')
                        if actor['role']=='patient': rows=db.execute(f'SELECT * FROM {table} WHERE patient_id=? ORDER BY id DESC LIMIT 100',(actor['patient_id'],))
                        else: rows=db.execute(f'SELECT * FROM {table} ORDER BY id DESC LIMIT 100')
                        return self.respond(200,json_rows(rows))
                    if re.fullmatch(r'/api/photos/[0-9a-f]{32}',path):
                        photo_id=path.rsplit('/',1)[-1]
                        photo=db.execute('SELECT * FROM photos WHERE id=?',(photo_id,)).fetchone()
                        if not photo:return self.respond(404,{'error':'Photo not found'})
                        if actor['role']=='patient' and photo['patient_id']!=actor['patient_id']: raise PermissionError('Photo access denied')
                        self.send_response(200)
                        self.send_header('Content-Type',photo['mime']);self.send_header('Content-Length',str(len(photo['bytes'])))
                        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                        self.end_headers();self.wfile.write(photo['bytes']);return
                    return self.respond(404,{'error':'Endpoint not found'})
            # Serve only allowlisted public files, no DB or source paths.
            files={'/':'patient.html','/patient':'patient.html','/clinician':'clinician.html','/patient.html':'patient.html','/clinician.html':'clinician.html','/styles.css':'styles.css','/patient.js':'patient.js','/clinician.js':'clinician.js','/i18n.js':'i18n.js','/rna.js':'rna.js','/manifest.webmanifest':'manifest.webmanifest','/sw.js':'sw.js','/icon.svg':'icon.svg'}
            item=files.get(path)
            if not item:return self.respond(404,{'error':'Not found'})
            content=(WEB/item).read_bytes()
            mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.webmanifest':'application/manifest+json'}.get(Path(item).suffix,'application/octet-stream')
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(content)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(content)
        except PermissionError as e:self.respond(403,{'error':str(e)})
        except Exception as e:self.respond(400,{'error':str(e)})
    def do_POST(self):
        try:
            path,_=self.path_and_query(); data=self.input()
            if path=='/api/login':
                email=str(data.get('email','')).lower().strip();pwd=str(data.get('password',''))
                with conn() as db: user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                if not user or not verify_password(pwd,user['secret']):return self.respond(401,{'error':'Invalid sign-in'})
                actor={'id':user['id'],'name':user['name'],'email':user['email'],'role':user['role'],'patient_id':user['patient_id']}
                token=secrets.token_urlsafe(32);SESSION[token]=actor
                return self.respond(200,{'token':token,'user':actor})
            if path=='/api/logout':
                auth=self.headers.get('Authorization','');SESSION.pop(auth[7:],None)
                return self.respond(200,{'ok':True})
            actor=self.require()
            with conn() as db:
                if path=='/api/rna':
                    # Patient can only submit own readings; clinician selects existing patient.
                    if actor['role']=='patient':pid=actor['patient_id']
                    else:
                        pid=int(data.get('patient_id',0))
                        if not db.execute('SELECT 1 FROM users WHERE patient_id=? AND role="patient"',(pid,)).fetchone():raise ValueError('Unknown patient')
                    reading=valid_rna(data)
                    cur=db.execute('INSERT INTO rna_readings (patient_id,received_at,sampled_at,sample_id,source,device_id,units,qc_pass,markers_json) VALUES (?,?,?,?,?,?,?,?,?)',
                        (pid,utcnow(),reading['sampled_at'],reading['sample_id'],reading['source'],reading['device_id'],reading['units'],reading['qc_pass'],reading['markers_json']))
                    return self.respond(201,{'id':cur.lastrowid,'received':True,'model_used':False,'note':'Research transport only; not interpreted as flare prediction.'})
                if path=='/api/checkins':
                    self.require('patient');pid=actor['patient_id']
                    for k in ('pain','itch','swelling','fatigue','stress'):
                        if k not in data:raise ValueError(f'Missing {k}')
                    vals={k:clamp(data.get(k)) for k in ('pain','itch','swelling','fatigue','stress')}
                    vals['sleep']=clamp(data.get('sleep'),7,0,12); vals['drainage']=bool(data.get('drainage',False))
                    recent=json_rows(db.execute('SELECT pain,swelling FROM checkins WHERE patient_id=? ORDER BY id DESC LIMIT 1',(pid,)))
                    baseline=db.execute('SELECT * FROM calibration WHERE patient_id=?',(pid,)).fetchone()
                    score,level,method=ml_score(vals,recent) or signal_score(vals,recent,baseline)
                    area=str(data.get('area','')).strip()[:100];notes=str(data.get('notes','')).strip()[:1200]
                    sensor_payload=data.get('sensors')
                    if sensor_payload is not None and not isinstance(sensor_payload,dict):raise ValueError('Invalid optional sensor payload')
                    sensor_json=json.dumps({str(k)[:45]:v for k,v in (sensor_payload or {}).items() if isinstance(v,(int,float,bool,str))},ensure_ascii=False)[:1200] if sensor_payload else None
                    photo_id=None
                    image_data=data.get('image_data')
                    if image_data:
                        match=re.fullmatch(r'data:(image/jpeg|image/png|image/webp);base64,([A-Za-z0-9+/=]+)',image_data)
                        if not match:raise ValueError('Only base64 JPEG, PNG or WebP images are accepted')
                        img=base64.b64decode(match.group(2),validate=True)
                        if len(img)>4_000_000:raise ValueError('Image exceeds 4MB')
                        # Basic magic-byte verification, not a sanitization pipeline.
                        if not (img.startswith(b'\xff\xd8\xff') or img.startswith(b'\x89PNG\r\n\x1a\n') or (img.startswith(b'RIFF') and img[8:12]==b'WEBP')):raise ValueError('Invalid image signature')
                        photo_id=secrets.token_hex(16)
                        db.execute('INSERT INTO photos (id,patient_id,mime,bytes) VALUES (?,?,?,?)',(photo_id,pid,match.group(1),img))
                    cursor=db.execute('INSERT INTO checkins (patient_id,created_at,pain,itch,swelling,fatigue,stress,sleep,drainage,area,notes,score,level,method,photo_id,sensor_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (pid,utcnow(),vals['pain'],vals['itch'],vals['swelling'],vals['fatigue'],vals['stress'],vals['sleep'],int(vals['drainage']),area,notes,score,level,method,photo_id,sensor_json))
                    if level in ('high','elevated'):
                        db.execute('INSERT INTO alerts (checkin_id,patient_id,created_at,message) VALUES (?,?,?,?)',(cursor.lastrowid,pid,utcnow(),f'{level.title()} illustrative signal ({score}/100). Review patient entry; not a validated flare forecast.'))
                    return self.respond(201,{'id':cursor.lastrowid,'score':score,'level':level,'method':method,'calibrated':bool(baseline),'alert_sent':level in ('high','elevated')})
                if path=='/api/calibration':
                    self.require('patient')
                    vals={k:clamp(data.get(k)) for k in ('pain','swelling','fatigue')}
                    db.execute('INSERT INTO calibration (patient_id,pain,swelling,fatigue,updated_at) VALUES (?,?,?,?,?) ON CONFLICT(patient_id) DO UPDATE SET pain=excluded.pain,swelling=excluded.swelling,fatigue=excluded.fatigue,updated_at=excluded.updated_at',(actor['patient_id'],vals['pain'],vals['swelling'],vals['fatigue'],utcnow()))
                    return self.respond(200,{'ok':True,'message':'Optional personal reference saved; no clinical accuracy claim.'})
                if path=='/api/alerts/ack':
                    self.require('clinician');aid=int(data.get('id',0))
                    db.execute('UPDATE alerts SET acknowledged=1 WHERE id=?',(aid,))
                    return self.respond(200,{'ok':True})
                if path in ('/api/appointments','/api/results','/api/visits'):
                    self.require('clinician');pid=int(data.get('patient_id',1))
                    patient=db.execute("SELECT id FROM users WHERE patient_id=? AND role='patient'",(pid,)).fetchone()
                    if not patient:raise ValueError('Unknown patient')
                    table=path.split('/')[-1]
                    if table=='appointments':
                        when_at=str(data.get('when_at','')).strip()[:40];title=str(data.get('title','')).strip()[:200]
                        if not when_at or not title:raise ValueError('Date/time and appointment title are required')
                        db.execute('INSERT INTO appointments (patient_id,when_at,title,created_at) VALUES (?,?,?,?)',(pid,when_at,title,utcnow()))
                        msg=f'Upcoming appointment: {title} — {when_at}'
                    elif table=='results':
                        summary=str(data.get('summary','')).strip()[:1500]
                        if not summary:raise ValueError('Result summary required')
                        db.execute('INSERT INTO results (patient_id,summary,created_at) VALUES (?,?,?)',(pid,summary,utcnow()))
                        msg='A new test-result update is available in your clinic portal.'
                    else:
                        summary=str(data.get('summary','')).strip()[:1500]
                        if not summary:raise ValueError('Visit summary required')
                        db.execute('INSERT INTO visits (patient_id,clinician,summary,created_at) VALUES (?,?,?,?)',(pid,actor['name'],summary,utcnow()))
                        msg='Your clinician added a visit note.'
                    db.execute('INSERT INTO notifications (patient_id,kind,message,created_at) VALUES (?,?,?,?)',(pid,table,msg,utcnow()))
                    return self.respond(201,{'ok':True})
                if path=='/api/notifications/seen':
                    self.require('patient')
                    db.execute('UPDATE notifications SET seen=1 WHERE patient_id=? AND id=?',(actor['patient_id'],int(data.get('id',0))))
                    return self.respond(200,{'ok':True})
            return self.respond(404,{'error':'Endpoint not found'})
        except PermissionError as e:self.respond(403,{'error':str(e)})
        except Exception as e:self.respond(400,{'error':str(e)})

def serve():
    seed()
    host=os.environ.get('HIDVIA_HOST','127.0.0.1')
    if host not in ('127.0.0.1','localhost','::1') and os.environ.get('HIDVIA_EXPOSE_DEMO')!='I_ACKNOWLEDGE_PUBLIC_FAKE_DATA_ONLY':
        raise RuntimeError('Network binding is restricted. Set HIDVIA_EXPOSE_DEMO=I_ACKNOWLEDGE_PUBLIC_FAKE_DATA_ONLY for fictional-only demonstration.')
    port=int(os.environ.get('PORT',os.environ.get('HIDVIA_PORT','8765')))
    print(f'HIDVIA Research Demo | http://{host}:{port}/patient | http://{host}:{port}/clinician',flush=True)
    print('DEMO ONLY: do not enter real health information. Use TLS, audited auth and encryption before clinical deployment.',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=='__main__':serve()
