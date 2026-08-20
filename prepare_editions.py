#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath

BUNDLE_SHA256 = '0597aa8727aa7b02d450b04b66814e37ad1ec9555a3b9e3f441e1a230203647a'
USER_DIRNAME = 'production-site-autopilot-codex-user-v7.1.0'
ENGINEERING_DIRNAME = 'production-site-autopilot-codex-engineering-v7.1.0'
USER_ZIP = 'production-site-autopilot-codex-user-v7.1.0.zip'
ENGINEERING_ZIP = 'production-site-autopilot-codex-engineering-v7.1.0.zip'
USER_SHA256 = '90a118d52020b2307c8447ea81ad6cd520492d255a274440adaa0cf03d257886'
ENGINEERING_SHA256 = '97666e9ba94e41a7c4cd103d3023bf1fd7c243f15ef43dec96fa45822dfaaac6'

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive,'r:xz') as tf:
        for member in tf.getmembers():
            p=PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts: raise SystemExit(f'unsafe archive path: {member.name}')
            if member.issym() or member.islnk(): raise SystemExit(f'archive links are not allowed: {member.name}')
        tf.extractall(destination, filter='data')

def copy_flat(source: Path, target: Path) -> None:
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(source,target)

def main() -> int:
    parser=argparse.ArgumentParser(description='Materialize Production Site Autopilot User and Engineering editions from the verified repository bundle.')
    parser.add_argument('--build-zips',action='store_true',help='Also rebuild the exact release ZIP files in dist/.')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    parts=sorted((root/'packages'/'source-bundle-v7.1.0').glob('part-*'))
    if not parts: raise SystemExit('source bundle parts are missing')
    encoded=''.join(p.read_text(encoding='ascii').strip() for p in parts)
    payload=base64.b64decode(encoded,validate=True)
    if hashlib.sha256(payload).hexdigest()!=BUNDLE_SHA256: raise SystemExit('source bundle SHA-256 mismatch')
    with tempfile.TemporaryDirectory(prefix='site-autopilot-') as td:
        temp=Path(td)
        archive=temp/'bundle.tar.xz'; archive.write_bytes(payload)
        extracted=temp/'extracted'; extracted.mkdir()
        safe_extract(archive,extracted)
        user_source=extracted/'user'/USER_DIRNAME
        engineering_source=extracted/'engineering'/ENGINEERING_DIRNAME
        if not (user_source/'README.md').is_file() or not (engineering_source/'README.md').is_file():
            raise SystemExit('bundle layout validation failed')
        copy_flat(user_source,root/'user')
        copy_flat(engineering_source,root/'engineering')
    print('User Edition:',root/'user')
    print('Engineering Edition:',root/'engineering')
    if args.build_zips:
        dist=root/'dist'; dist.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='autopilot-build-') as build_td:
            build_root=Path(build_td)/ENGINEERING_DIRNAME
            shutil.copytree(root/'engineering',build_root)
            subprocess.run([sys.executable,str(build_root/'scripts'/'build_user_release.py'),'--package-root',str(build_root),'--output-dir',str(dist)],check=True)
            subprocess.run([sys.executable,str(build_root/'scripts'/'build_release.py'),'--package-root',str(build_root),'--output',str(dist/ENGINEERING_ZIP),'--skip-checks'],check=True)
        checks={USER_ZIP:USER_SHA256,ENGINEERING_ZIP:ENGINEERING_SHA256}
        for name,expected in checks.items():
            actual=sha256(dist/name)
            if actual!=expected: raise SystemExit(f'{name}: SHA-256 mismatch: {actual}')
            print(f'{name}: {actual}')
    return 0
if __name__=='__main__': raise SystemExit(main())
