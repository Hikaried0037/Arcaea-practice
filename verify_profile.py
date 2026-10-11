import hashlib,sys,zipfile
expected='143e1c8bd6683a93ac02f895f500b3ff2a1143a528f1dab56788fa655d3cbb23'
with zipfile.ZipFile(sys.argv[1]) as z:
    actual=hashlib.sha256(z.read('lib/arm64-v8a/libcocos2dcpp.so')).hexdigest()
    if actual!=expected:
        raise SystemExit('Unsupported native library; refusing to patch offsets: '+actual)
print('Infinity 7.0.1f ARM64 profile verified')
