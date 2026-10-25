"""Black box RNA-protocol smoke tests using fake payloads only."""
from test_server import DemoAPI
from urllib.error import HTTPError
class RNAEndpoints(DemoAPI):
    def test_rna_roundtrip_with_role_filter(self):
        patient=self.post('/api/login',{'email':'patient@hidvia.test','password':'demo-pass-123'})['token']
        doctor=self.post('/api/login',{'email':'clinician@hidvia.test','password':'demo-pass-123'})['token']
        sample={'schema':'hidvia-rna-v1','sample_id':'FAKE_123','sampled_at':'2026-10-25T10:00:00+01:00',
                'source':'file','device_id':'SIMULATOR','units':'normalized_expression','qc_pass':True,'markers':{'TESTA':.24,'TESTB':1.1}}
        post=self.post('/api/rna',sample,patient)
        self.assertTrue(post['received']);self.assertFalse(post['model_used'])
        self.assertIn('TESTA',self.get('/api/rna',patient)[0]['markers_json'])
        self.assertEqual(self.get('/api/rna?patient_id=1',doctor)[0]['sample_id'],'FAKE_123')
        self.assertEqual(self.get('/api/rna?patient_id=2',patient)[0]['patient_id'],1)
    def test_reject_unexpected_markers_and_missing_qc(self):
        patient=self.post('/api/login',{'email':'patient@hidvia.test','password':'demo-pass-123'})['token']
        sample={'schema':'hidvia-rna-v1','sample_id':'FAKE_123','sampled_at':'2026-10-25T10:00:00+01:00',
                'source':'file','device_id':'SIMULATOR','units':'normalized_expression','markers':{'IL1':float('nan')}}
        with self.assertRaises(HTTPError):self.post('/api/rna',sample,patient)
    def test_no_anonymous_rna(self):
        with self.assertRaises(HTTPError) as ex:self.get('/api/rna')
        self.assertEqual(ex.exception.code,403)
