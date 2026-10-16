"""Synthetic fixtures only; no real credentials or personal paths."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from privacy_check import scan

with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);path=root/'sample.txt'
 cases=[
  ('public documentation with a hash '+'a'*64,True),
  ('source',True),
  ('https://github.com/Hikaried0037/Arcaea-practice',True),
  ('gh'+'p_'+'a'*30,False),
  ('-----BEGIN '+'PRIVATE KEY-----',False),
  ('C:'+chr(92)+'Users'+chr(92)+'example'+chr(92)+'file',False),
  ('private-user'+'@'+'mail.invalid',False),
  ('328298942+Hikaried0037'+'@'+'users.noreply.github.com',True),
 ]
 for content,expected in cases:
  path.write_text(content,encoding='utf-8');assert scan(root)['passed']==expected
 path.write_text('synthetic-sensitive-value',encoding='utf-8')
 assert not scan(root,secrets=[b'synthetic-sensitive-value'])['passed']
 path.unlink();(root/'signing.p12').write_bytes(b'fixture')
 assert not scan(root)['passed']
print('Privacy scanner PASS checks=10')
