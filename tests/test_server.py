"""Local integration tests using the standard library. Never use real patient data."""
import json
import base64
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parent.parent

class DemoAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.port=8873
        env={**os.environ,'HIDVIA_DATA':cls.tmp.name,'HIDVIA_PORT':str(cls.port)}
        cls.server=subprocess.Popen([sys.executable,str(ROOT/'server/app.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(70):
            try:cls.get('/api/health');break
            except Exception:time.sleep(.1)
    @classmethod
    def tearDownClass(cls):cls.server.terminate();cls.server.wait(timeout=10);cls.tmp.cleanup()
    @classmethod
    def get(cls,path,token=None):
        req=Request(f'http://127.0.0.1:{cls.port}'+path,headers={'Authorization':'Bearer '+token if token else ''})
        with urlopen(req,timeout=5) as res:return json.load(res)
    @classmethod
    def post(cls,path,data,token=None):
        req=Request(f'http://127.0.0.1:{cls.port}'+path,data=json.dumps(data).encode(),method='POST',headers={'Content-Type':'application/json','Authorization':'Bearer '+token if token else ''})
        with urlopen(req,timeout=5) as res:return json.load(res)
    def test_full_patient_clinician_workflow(self):
        patient=self.post('/api/login',{'email':'patient@hidvia.test','password':'demo-pass-123'})['token']
        clinician=self.post('/api/login',{'email':'clinician@hidvia.test','password':'demo-pass-123'})['token']
        self.assertEqual(self.get('/api/calibration',patient)['calibrated'],False)
        before=len(self.get('/api/checkins',patient))
        entry=self.post('/api/checkins',{'pain':9,'swelling':9,'itch':8,'fatigue':9,'stress':7,'sleep':4,'drainage':True,'area':'example','notes':'fictional symptoms'},patient)
        self.assertEqual(entry['level'],'high')
        self.assertEqual(len(self.get('/api/checkins',patient)),before+1)
        self.assertGreaterEqual(len(self.get('/api/alerts',clinician)),1)
        self.post('/api/calibration',{'pain':2,'swelling':2,'fatigue':3},patient)
        self.assertIn('pain',self.get('/api/calibration',patient))
        self.post('/api/appointments',{'patient_id':1,'when_at':'2027-01-02T10:30','title':'Fictional review'},clinician)
        self.post('/api/results',{'patient_id':1,'summary':'Fictional result'},clinician)
        self.post('/api/visits',{'patient_id':1,'summary':'Fictional note'},clinician)
        self.assertTrue(any('Fictional review' in x['title'] for x in self.get('/api/appointments',patient)))
        self.assertTrue(any('Fictional result' in x['summary'] for x in self.get('/api/results',patient)))
        self.assertTrue(any('Fictional note' in x['summary'] for x in self.get('/api/visits',patient)))
    def test_sensors_and_protected_photos(self):
        patient=self.post('/api/login',{'email':'patient@hidvia.test','password':'demo-pass-123'})['token']
        clinician=self.post('/api/login',{'email':'clinician@hidvia.test','password':'demo-pass-123'})['token']
        one_pixel=base64.b64encode(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/uokAAAAASUVORK5CYII=')).decode()
        self.post('/api/checkins',{'pain':3,'swelling':4,'itch':2,'fatigue':2,'stress':4,'sleep':7,'drainage':False,'sensors':{'ambient_light_lux':20.0,'steps_since_boot':13000},'image_data':'data:image/png;base64,'+one_pixel},patient)
        entry=self.get('/api/checkins',clinician)[0]
        self.assertIsNotNone(entry['photo_id'])
        self.assertIn('steps_since_boot',entry['sensor_json'])
        uri=f'http://127.0.0.1:{self.port}/api/photos/'+entry['photo_id']
        with self.assertRaises(HTTPError) as error:urlopen(uri)
        self.assertEqual(error.exception.code,403)
        with urlopen(Request(uri,headers={'Authorization':'Bearer '+clinician})) as response:
            self.assertEqual(response.headers['Content-Type'],'image/png')
            self.assertTrue(response.read().startswith(b'\x89PNG'))

    def test_reject_unauthorized_access(self):
        patient=self.post('/api/login',{'email':'patient@hidvia.test','password':'demo-pass-123'})['token']
        for path,token in [('/api/alerts',patient),('/api/checkins',None)]:
            with self.assertRaises(HTTPError) as error:self.get(path,token)
            self.assertEqual(error.exception.code,403)
        with self.assertRaises(HTTPError) as error:self.post('/api/results',{'patient_id':1,'summary':'No'},patient)
        self.assertEqual(error.exception.code,403)
    def test_asset_routes(self):
        for path in ('/patient','/clinician','/styles.css','/i18n.js'):
            with urlopen(f'http://127.0.0.1:{self.port}'+path) as r:self.assertEqual(r.status,200)

if __name__=='__main__':unittest.main()
