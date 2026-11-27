#!/usr/bin/env python3
"""Regenerate kernel patch 0001 from mainline/sm6150-xiaomi-mojito.dts and update its APKBUILD checksum.

Run from anywhere after editing the DTS; then bump pkgrel and sync the package to pmaports.
"""
import hashlib, pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent / 'mainline'
pkg = root / 'linux-postmarketos-qcom-sm6150'
patch = pkg / '0001-arm64-dts-qcom-add-xiaomi-mojito.patch'
dts = (root / 'sm6150-xiaomi-mojito.dts').read_text()
assert dts.endswith('\n')
old = patch.read_text()
head = old[:old.index('@@ -0,0 +1,')]
body = ''.join('+' + line + '\n' for line in dts[:-1].split('\n'))
patch.write_text(head + '@@ -0,0 +1,%d @@\n' % dts.count('\n') + body)
apk = pkg / 'APKBUILD'
digest = hashlib.sha512(patch.read_bytes()).hexdigest()
apk.write_text(re.sub(r'[0-9a-f]{100,}  ' + re.escape(patch.name), digest + '  ' + patch.name, apk.read_text()))
print('updated', patch.name)
