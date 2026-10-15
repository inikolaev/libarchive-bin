#!/usr/bin/env python3
"""Validate binary structure, link both CPUs, run native C and SwiftPM consumers."""
import argparse
import json
import platform
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def run(*args, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)
def output(*args, cwd=ROOT):
    return subprocess.check_output([str(a) for a in args], cwd=cwd, text=True).strip()
def audit(executable):
    lines = output('otool', '-L', executable).splitlines()[1:]
    for line in lines:
        dep = line.strip().split(' (')[0]
        if dep not in ('/usr/lib/libSystem.B.dylib', '/usr/lib/libiconv.2.dylib'):
            raise RuntimeError(f'Unexpected runtime dependency: {dep}')
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote', action='store_true', help='Use the published package version')
    args = parser.parse_args()
    lock = json.loads((ROOT/'sources.lock.json').read_text())
    framework = ROOT/'dist/CLibArchive.xcframework'
    info = plistlib.loads((framework/'Info.plist').read_bytes())
    assert len(info['AvailableLibraries']) == 1
    entry = info['AvailableLibraries'][0]
    assert entry['SupportedPlatform'] == 'macos'
    assert set(entry['SupportedArchitectures']) == {'arm64', 'x86_64'}
    library = framework/entry['LibraryIdentifier']/entry['LibraryPath']
    headers = framework/entry['LibraryIdentifier']/entry['HeadersPath']
    assert set(output('lipo', '-archs', library).split()) == {'arm64', 'x86_64'}
    work = ROOT/'build/smoke'
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    for arch in ('arm64', 'x86_64'):
        executable = work/f'smoke-{arch}'
        run('xcrun', 'clang', '-arch', arch, '-mmacosx-version-min=13.0', '-I', headers,
            ROOT/'tests/smoke.c', library, '-liconv', '-o', executable)
        audit(executable)
        if arch == platform.machine(): run(executable)
    package = work/'consumer'
    (package/'Sources/Smoke').mkdir(parents=True)
    if args.remote:
        dep = f'.package(url: "https://github.com/inikolaev/libarchive-bin.git", exact: "{lock["packageVersion"]}")'
        target = '.product(name: "CLibArchive", package: "libarchive-bin")'
        extra = ''
    else:
        dep = ''
        target = '"CLibArchive"'
        extra = f'.binaryTarget(name: "CLibArchive", path: "{framework}"),'
    (package/'Package.swift').write_text(f'''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "Smoke", platforms: [.macOS(.v13)], dependencies: [{dep}], targets: [
    {extra}
    .executableTarget(name: "Smoke", dependencies: [{target}])
])
''')
    (package/'Sources/Smoke/main.swift').write_text('''import CLibArchive
precondition(archive_version_number() == ARCHIVE_VERSION_NUMBER)
precondition(archive_zlib_version() != nil)
precondition(archive_liblzma_version() != nil)
precondition(archive_bzlib_version() != nil)
precondition(archive_libzstd_version() != nil)
let reader = archive_read_new()!
precondition(archive_read_support_filter_all(reader) == ARCHIVE_OK)
precondition(archive_read_support_format_all(reader) == ARCHIVE_OK)
precondition(archive_read_free(reader) == ARCHIVE_OK)
print(String(cString: archive_version_details()))
''')
    run('swift', 'run', '-c', 'release', '--package-path', package, 'Smoke')
    binary = Path(output('swift', 'build', '-c', 'release', '--package-path', package, '--show-bin-path'))/'Smoke'
    deps = output('otool', '-L', binary)
    assert not re.search(r'lib(archive|z|bz2|lzma|zstd)[.\d]', deps), deps
    assert '/opt/homebrew' not in deps and '/usr/local' not in deps, deps
    print('Binary structure, native execution, cross-architecture linking and SwiftPM passed')
if __name__ == '__main__': main()
