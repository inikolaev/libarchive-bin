#!/usr/bin/env python3
"""Build pinned static libraries. All generated files stay in build/ and dist/."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'sources.lock.json').read_text())
BUILD = ROOT / 'build'
DIST = ROOT / 'dist'
ENV = os.environ.copy()
for key in ('CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CMAKE_PREFIX_PATH', 'SDKROOT'):
    ENV.pop(key, None)
ENV.update(ZERO_AR_DATE='1', LC_ALL='C', TZ='UTC')

def run(*args, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, env=ENV, check=True)

def output(*args):
    return subprocess.check_output([str(a) for a in args], env=ENV, text=True).strip()

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def fetch():
    result = {}
    for name, spec in LOCK['sources'].items():
        archive = BUILD / 'downloads' / (name + '.tar.gz')
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            temporary = archive.with_suffix('.partial')
            run('curl', '--fail', '--location', '--retry', '3', '--proto', '=https', spec['url'], '-o', temporary)
            temporary.replace(archive)
        if digest(archive) != spec['sha256']:
            raise RuntimeError(f'Checksum mismatch: {archive}; remove and retry after investigating')
        source = BUILD / 'sources' / f"{name}-{spec['version']}"
        if source.exists():
            shutil.rmtree(source)
        source.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as tar:
            # Reject path escapes, device files and links escaping the source tree.
            base = source.parent.resolve()
            for entry in tar.getmembers():
                dest = (base / entry.name).resolve()
                if base not in dest.parents or entry.isdev():
                    raise RuntimeError('Unsafe source archive member')
                if entry.issym() or entry.islnk():
                    link = (dest.parent / entry.linkname).resolve() if entry.issym() else (base / entry.linkname).resolve()
                    if base not in link.parents:
                        raise RuntimeError('Unsafe source archive link')
            tar.extractall(base)
        result[name] = source
        for license_file in spec['licenses']:
            if (source / license_file).read_bytes() != (ROOT / 'LICENSES' / name / license_file).read_bytes():
                raise RuntimeError(f'License differs from pinned source: {name}/{license_file}')
    return result

def main():
    if output('cmake', '--version').splitlines()[0] != 'cmake version ' + LOCK['cmake']:
        raise RuntimeError('Install the exact CMake version from sources.lock.json')
    sources = fetch()
    sdk = output('xcrun', '--sdk', 'macosx', '--show-sdk-path')
    clang = output('xcrun', '--find', 'clang')
    cxx = output('xcrun', '--find', 'clang++')
    libraries = []
    for arch in ('arm64', 'x86_64'):
        stage = BUILD / arch
        if stage.exists():
            shutil.rmtree(stage)
        prefix = stage / 'install'
        (prefix / 'lib').mkdir(parents=True)
        (prefix / 'include').mkdir()
        flags = f'-ffile-prefix-map={ROOT}=. -fdebug-prefix-map={ROOT}=.'
        common = ['-G', 'Unix Makefiles', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=OFF',
                  '-DCMAKE_INSTALL_LIBDIR=lib', f'-DCMAKE_INSTALL_PREFIX={prefix}',
                  f'-DCMAKE_OSX_ARCHITECTURES={arch}', f'-DCMAKE_OSX_DEPLOYMENT_TARGET={LOCK["deploymentTarget"]}',
                  f'-DCMAKE_OSX_SYSROOT={sdk}', '-DCMAKE_SYSTEM_NAME=Darwin', f'-DCMAKE_SYSTEM_PROCESSOR={arch}',
                  f'-DCMAKE_C_COMPILER={clang}', f'-DCMAKE_CXX_COMPILER={cxx}',
                  f'-DCMAKE_C_FLAGS={flags}', f'-DCMAKE_CXX_FLAGS={flags}',
                  '-DCMAKE_IGNORE_PREFIX_PATH=/opt/homebrew;/usr/local;/opt/local',
                  '-DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF', '-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF']
        def cmake(name, opts, subdir=''):
            folder = stage / name
            run('cmake', '-S', sources[name] / subdir, '-B', folder, *common, *opts)
            run('cmake', '--build', folder, '--parallel', str(min(os.cpu_count() or 2, 8)))
            run('cmake', '--install', folder)
        cmake('zlib', ['-DZLIB_BUILD_SHARED=OFF', '-DZLIB_BUILD_TESTING=OFF'])
        cmake('xz', ['-DBUILD_TESTING=OFF', '-DXZ_NLS=OFF', '-DXZ_TOOL_XZ=OFF', '-DXZ_TOOL_XZDEC=OFF',
                     '-DXZ_TOOL_LZMADEC=OFF', '-DXZ_TOOL_LZMAINFO=OFF', '-DXZ_DOC=OFF'])
        cmake('zstd', ['-DZSTD_BUILD_SHARED=OFF', '-DZSTD_BUILD_STATIC=ON', '-DZSTD_BUILD_PROGRAMS=OFF',
                       '-DZSTD_BUILD_TESTS=OFF'], 'build/cmake')
        bzbuild = stage / 'bzip2'
        bzbuild.mkdir()
        objects = []
        for name in ('blocksort', 'huffman', 'crctable', 'randtable', 'compress', 'decompress', 'bzlib'):
            obj = bzbuild / (name + '.o')
            run(clang, '-c', '-O2', '-fPIC', '-arch', arch, '-isysroot', sdk,
                '-mmacosx-version-min=' + LOCK['deploymentTarget'], f'-ffile-prefix-map={ROOT}=.',
                sources['bzip2'] / (name + '.c'), '-o', obj)
            objects.append(obj)
        run('xcrun', 'libtool', '-static', '-D', '-o', prefix / 'lib/libbz2.a', *objects)
        shutil.copyfile(sources['bzip2'] / 'bzlib.h', prefix / 'include/bzlib.h')
        disabled = ('OPENSSL', 'MBEDTLS', 'NETTLE', 'MD', 'LIBB2', 'LZ4', 'LZO', 'LIBXML2', 'BSDXML',
                    'EXPAT', 'PCREPOSIX', 'PCRE2POSIX', 'LIBGCC', 'TAR', 'CPIO', 'CAT', 'UNZIP', 'TEST')
        opts = [f'-DENABLE_{x}=OFF' for x in disabled]
        for opt, lib in [('ZLIB', 'z'), ('BZIP2', 'bz2'), ('LIBLZMA', 'lzma'), ('ZSTD', 'zstd')]:
            opts += [f'-D{opt}_INCLUDE_DIR={prefix}/include', f'-D{opt}_LIBRARY={prefix}/lib/lib{lib}.a']
        opts += [f'-DCMAKE_PREFIX_PATH={prefix}', '-DENABLE_ZLIB=ON', '-DENABLE_BZip2=ON', '-DENABLE_LZMA=ON', '-DENABLE_ZSTD=ON']
        cmake('libarchive', opts)
        config = (stage / 'libarchive/config.h').read_text()
        for macro in ('HAVE_ZLIB_H', 'HAVE_BZLIB_H', 'HAVE_LZMA_H', 'HAVE_ZSTD_H'):
            if f'#define {macro} 1' not in config:
                raise RuntimeError(f'Missing required codec: {macro}')
        merged = stage / 'libCLibArchive.a'
        run('xcrun', 'libtool', '-static', '-D', '-o', merged,
            *[prefix / f'lib/lib{x}.a' for x in ('archive', 'z', 'bz2', 'lzma', 'zstd')])
        libraries.append(merged)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    universal = BUILD / 'libCLibArchive.a'
    run('xcrun', 'lipo', '-create', *libraries, '-output', universal)
    headers = BUILD / 'Headers'
    headers.mkdir(exist_ok=True)
    for name in ('archive.h', 'archive_entry.h'):
        shutil.copyfile(BUILD / 'arm64/install/include' / name, headers / name)
    (headers / 'module.modulemap').write_text('module CLibArchive {\n  header "archive.h"\n  header "archive_entry.h"\n  link "iconv"\n  export *\n}\n')
    framework = DIST / 'CLibArchive.xcframework'
    run('xcodebuild', '-create-xcframework', '-library', universal, '-headers', headers, '-output', framework)
    shutil.copytree(ROOT / 'LICENSES', framework / 'LICENSES')
    shutil.copyfile(ROOT / 'sources.lock.json', framework / 'sources.lock.json')
    # Fixed ordering, permissions and timestamps; ZIP_STORED avoids zlib-version-dependent bytes.
    with zipfile.ZipFile(DIST / 'CLibArchive.xcframework.zip', 'w', compression=zipfile.ZIP_STORED) as z:
        for path in sorted(framework.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(DIST)), (2020, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                z.writestr(info, path.read_bytes())
    checksum = digest(DIST / 'CLibArchive.xcframework.zip')
    if output('swift', 'package', 'compute-checksum', DIST / 'CLibArchive.xcframework.zip') != checksum:
        raise RuntimeError('SwiftPM checksum mismatch')
    (DIST / 'SHA256SUMS').write_text(checksum + '  CLibArchive.xcframework.zip\n')
    provenance = {'sources': LOCK, 'xcode': output('xcodebuild', '-version'),
                  'sdk': output('xcrun', '--sdk', 'macosx', '--show-sdk-version'),
                  'clang': output('xcrun', 'clang', '--version'), 'cmake': LOCK['cmake'],
                  'sha256': checksum}
    (DIST / 'build-info.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Built universal XCFramework:', checksum)

if __name__ == '__main__':
    main()
