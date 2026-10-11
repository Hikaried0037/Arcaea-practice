"""Create a share folder and ZIP from an already verified full APK."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = (
    'README.md', 'BUILDING.md', 'CHANGELOG.md', 'VALIDATION.md', '.gitignore',
    'build.ps1', 'repack.py', 'rename_package.py', 'verify_profile.py',
    'verify_package.py', 'package_share.py', 'native/practice.cpp',
    'java/moe/practice/PracticeOverlay.java', 'support/test-silence.ogg',
)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_archive(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in SOURCE_FILES:
            archive.write(ROOT / relative, 'practice/' + relative)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'practice/' + n for n in SOURCE_FILES}
        assert all(archive.read('practice/' + n) == (ROOT / n).read_bytes() for n in SOURCE_FILES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--panel-image', type=Path)
    parser.add_argument('--game-image', type=Path)
    args = parser.parse_args()
    report = json.loads(args.verification.read_text(encoding='utf-8-sig'))
    if report['application_id'] != 'moe.inf.arc.practice':
        raise SystemExit('Expected the standalone practice package')
    if digest(args.apk) != report['sha256'] or args.apk.stat().st_size != report['size']:
        raise SystemExit('APK does not match the completed verification report')
    for field in ('all_original_assets_preserved', 'compressed_payloads_sha256_match', 'injected_files_match_build'):
        if report[field] is not True:
            raise SystemExit('Missing successful package check: ' + field)
    destination = args.destination.resolve()
    # Require a fresh folder so an old test APK or signing key cannot be retained.
    if destination.exists():
        raise SystemExit('Use a fresh destination folder: ' + str(destination))
    destination.mkdir(parents=True)
    apk_name = 'Arcaea-Infinity-7.0.1f-Practice.apk'
    shutil.copy2(args.apk, destination / apk_name)
    assert digest(destination / apk_name) == report['sha256']
    for name in ('README.md', 'CHANGELOG.md', 'VALIDATION.md'):
        shutil.copy2(ROOT / name, destination / name)
    source_archive(destination / 'source' / 'Arcaea-Practice-source.zip')
    public_report = {k: report[k] for k in (
        'application_id', 'preserved_entries', 'all_original_assets_preserved',
        'compressed_payloads_sha256_match', 'injected_files_match_build', 'size', 'sha256',
    )}
    public_report['package'] = apk_name
    (destination / 'verification.json').write_text(
        json.dumps(public_report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for source, name in ((args.panel_image, 'practice-panel.png'), (args.game_image, 'practice-in-game.png')):
        if source:
            (destination / 'screenshots').mkdir(exist_ok=True)
            shutil.copy2(source, destination / 'screenshots' / name)
    readme = (destination / 'README.md').read_text(encoding='utf-8')
    introduction = '''
## 分享包内容

| 文件 | 用途 |
| --- | --- |
| `Arcaea-Infinity-7.0.1f-Practice.apk` | 完整安装包，直接安装 |
| `README.md` | 安装和功能使用说明 |
| `CHANGELOG.md` | 更新记录 |
| `VALIDATION.md` | 已完成的验证及当前限制 |
| `SHA256SUMS.txt` | 文件完整性校验 |
| `verification.json` | 完整 APK 的资源一致性检查结果 |
| `source/Arcaea-Practice-source.zip` | 源码、构建说明和脚本 |
| `screenshots/` | 练习面板和曲目内的界面示例 |

传给普通使用者时，可直接分享整个文件夹或对应的 `-share.zip`，解压后安装上面的 APK。源码 ZIP 用于自行构建。

下载后可在 PowerShell 中运行 `Get-FileHash .\\Arcaea-Infinity-7.0.1f-Practice.apk -Algorithm SHA256`，与 `SHA256SUMS.txt` 中同名文件的数值对照。
'''
    readme = readme.replace('## 安装与使用', introduction + '\n## 安装与使用', 1)
    if args.panel_image:
        readme += '\n## 界面示例\n\n![练习面板](screenshots/practice-panel.png)\n'
    if args.game_image:
        readme += '\n![曲目中的练习面板](screenshots/practice-in-game.png)\n'
    (destination / 'README.md').write_text(readme, encoding='utf-8')
    files = sorted(p for p in destination.rglob('*') if p.is_file())
    checksums = {p.relative_to(destination).as_posix(): digest(p) for p in files}
    (destination / 'SHA256SUMS.txt').write_text(
        ''.join(f'{value}  {name}\n' for name, value in checksums.items()), encoding='utf-8')
    # Already-compressed APK data is stored without another expensive compression pass.
    zip_path = destination.with_name(destination.name + '-share.zip')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path in sorted(p for p in destination.rglob('*') if p.is_file()):
            archive.write(path, destination.name + '/' + path.relative_to(destination).as_posix())
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        for name, value in checksums.items():
            with archive.open(destination.name + '/' + name) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == value
    (zip_path.parent / (zip_path.name + '.sha256')).write_text(
        digest(zip_path) + '  ' + zip_path.name + '\n', encoding='utf-8')
    print(json.dumps({'folder': str(destination), 'archive': str(zip_path),
                      'source_files': len(SOURCE_FILES), 'apk_sha256': report['sha256'],
                      'zip_integrity_verified': True}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
