"""Scan a source export or Git index without printing matched private values."""
import argparse,json,re,subprocess,hashlib
from pathlib import Path

RULES={
 'personal_path':re.compile(r'(?i)\b[A-Z]:[\\/](?:Users|Documents)[\\/]|'+'xwechat_'+r'files|wxid_[a-z0-9_]+'),
 'github_token':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
 'private_key':re.compile('-----BEGIN '+r'(?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
 'access_key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'embedded_password':re.compile(r'(?i)(?:password|passwd|api_key|client_secret)\s*[:=]\s*[\"\x27][^\"\x27\r\n]{12,}[\"\x27]'),
}
EMAIL=re.compile(r'\b[A-Za-z0-9_.+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
BLOCKED={'.apk','.aab','.zip','.p12','.pfx','.jks','.keystore','.key','.pem','.so','.dex','.class','.png','.jpg','.mp4'}

def scan(root,paths=None,secrets=()):
 root=root.resolve();findings=[];count=0
 # Public upstream author/license contacts are attribution, not user data.
 # The exemption applies only to exact pristine files in the pinned manifest;
 # private paths, credentials and known-secret checks still apply to them.
 allowed_attribution=set()
 for name in ['soundtouch','signalsmith-stretch','signalsmith-linear']:
  vendor=root/'third_party'/name;manifest=vendor/'UPSTREAM.json'
  if manifest.is_file():
   for relative,digest in json.loads(manifest.read_text(encoding='utf-8'))['files'].items():
    p=vendor/relative
    if p.is_file() and p.resolve().is_relative_to(vendor.resolve()) and hashlib.sha256(p.read_bytes()).hexdigest()==digest:allowed_attribution.add(p.resolve())
 if paths is None:
  paths=[p for p in root.rglob('*') if p.is_file() and not any(x in {'.git','out','__pycache__'} for x in p.relative_to(root).parts)]
 for path in paths:
  relative=path.relative_to(root).as_posix();count+=1
  if path.is_symlink() or path.suffix.lower() in BLOCKED:
   findings.append({'file':relative,'rule':'excluded_file_type'});continue
  data=path.read_bytes()
  try:text=data.decode('utf-8-sig')
  except UnicodeDecodeError:findings.append({'file':relative,'rule':'non_text_content'});continue
  for label,pattern in RULES.items():
   if pattern.search(text):findings.append({'file':relative,'rule':label})
  if path.resolve() not in allowed_attribution and any(not m.group().endswith('@users.noreply.github.com') and not m.group().endswith('@example.com') for m in EMAIL.finditer(text)):
   findings.append({'file':relative,'rule':'personal_email'})
  if any(secret and secret in data for secret in secrets):findings.append({'file':relative,'rule':'known_secret'})
 return {'files_checked':count,'passed':not findings,'findings':findings,'matched_values_included':False}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
 parser.add_argument('--staged',action='store_true',help='Scan files tracked in the Git index')
 parser.add_argument('--secret-file',type=Path,action='append',default=[],help='Compare against a local secret without printing it')
 parser.add_argument('--report',type=Path);args=parser.parse_args();paths=None
 if args.staged:
  raw=subprocess.check_output(['git','ls-files','-z'],cwd=args.root)
  paths=[args.root/n.decode('utf-8') for n in raw.split(b'\0') if n]
 secrets=[p.read_bytes().strip() for p in args.secret_file]
 result=scan(args.root,paths,secrets);output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if args.report:args.report.write_text(output,encoding='utf-8')
 print(output,end='');raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
