import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from reconcile import run
class ReconcileTests(unittest.TestCase):
 def test_sample_snapshot(self):
  base=Path(__file__).resolve().parents[1]
  r=run(base/'data')
  self.assertEqual(r['summary']['invoice_rows'],13)
  self.assertEqual(r['summary']['auto_approve_ready'],3)
  self.assertEqual(r['summary']['exceptions'],12)
  codes={e['reason_code'] for e in r['exceptions']}
  for c in ['PARENT_CONTACT_MISMATCH','BATCH_AT_CAPACITY','DUPLICATE_FORM','PARTIAL_PAYMENT','PAYMENT_FAILED','BATCH_CHANGE_REQUEST','INVOICE_NOT_FOUND','PAID_INVOICE_NO_FORM']:
   self.assertIn(c,codes)
if __name__=='__main__':unittest.main()
