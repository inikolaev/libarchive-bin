# libarchive-bin

Pinned, universal **static** libarchive for macOS 13 and later, packaged as an
XCFramework and the SwiftPM binary target/product `CLibArchive`. This is an
independent binary distribution, not the upstream libarchive project or a Swift
wrapper. Commander owns its higher-level archive API and filesystem integration.

## Use a published release

```swift
.package(url: "https://github.com/inikolaev/libarchive-bin.git", exact: "3.8.10-1")
```

Add `.product(name: "CLibArchive", package: "libarchive-bin")` to your target's
dependencies, then `import CLibArchive`. No Homebrew installation is required.
The package uses Swift tools 6.0 and works with Commander's Swift 6.2 manifest.
Only use a version after its GitHub release is promoted from prerelease.

Version `3.8.10-1` means libarchive 3.8.10, packaging revision 1. The `-1` is a
SemVer prerelease component, so use an **exact** dependency rather than a range.
Never move tags or replace assets; increment the revision for any build change.

## Contents

| Library | Version | Purpose |
|---|---|---|
| libarchive | 3.8.10 | Archive formats and C API |
| zlib | 1.3.2 | ZIP deflate and gzip |
| bzip2 | 1.0.8 | bzip2 |
| XZ/liblzma | 5.8.4 | XZ, LZMA and 7z compression |
| Zstandard | 1.5.7 | zstd |

The macOS slice contains arm64 and x86_64. All five libraries are merged into
`libCLibArchive.a`. The module map supplies the system iconv link requirement;
CommonCrypto and the normal C runtime come from macOS. No system libarchive or
system compression library is linked. Optional LZ4, LZO, libb2, OpenSSL, external
XML and PCRE libraries are disabled. No command-line tools are shipped.

Smoke-tested formats: ZIP, 7z, plain tar, tar.gz, tar.bz2, tar.xz and tar.zst.
Other upstream formats (including RAR readers) may be available but are not
certified by these smoke tests. Password-protected archives are outside the
current supported/tested scope. Unsupported filters can still invoke external
programs through upstream APIs; callers should select supported filters and
handle libarchive warnings/errors rather than assume every format is bundled.

## Build and test

Install full Xcode, select it, then from the repository root:

```sh
python3 -m venv .tooling
.tooling/bin/pip install cmake==3.31.6
export PATH="$PWD/.tooling/bin:$PATH"
python3 scripts/build.py
python3 scripts/test.py
```

Canonical CI uses Xcode 16.4 (16F6), macOS SDK 15.5 and CMake 3.31.6. Other Xcode
versions can build locally, but their binary checksums are expected to differ.
`build-info.json` records the actual compiler, SDK, Xcode, source lock and asset
checksum. Source URLs, versions and SHA-256 digests are pinned in
`sources.lock.json`; downloads are verified on every invocation, including cache
hits. Updating a version also requires reviewing its source checksum and copying
its license notices into `LICENSES/`.

The build starts each architecture from clean build directories, suppresses
archive timestamps, maps build paths, and creates a sorted ZIP with fixed
metadata. CI performs two clean builds and requires identical ZIP checksums.
This verifies repeatability on the selected runner/toolchain; hosted runner
images themselves are mutable, so bit-for-bit identity across arbitrary Xcode,
SDK or runner-image changes is not promised. Source download caching is an
optimization only and never substitutes for checksum verification.

Tests inspect the XCFramework, link both CPUs, run archive/codec round trips,
reject malformed input, exercise SwiftPM imports and audit dynamic dependencies.
CI executes the same artifact on native Apple Silicon and Intel runners. macOS
13 is the deployment target; CI runtime tests currently run on macOS 15.

## Release

1. Update `sources.lock.json`, licenses, documentation and `RELEASE_NOTES.md`.
2. Merge the changes into `main`; ordinary push/PR builds never publish releases.
3. Run **Build and release** manually on `main` with **publish** enabled.
4. The workflow rebuilds twice, verifies checksums and passes both native test
   jobs before generating the URL/checksum manifest and pushing its commit/tag.
5. It uploads the exact tested ZIP, `SHA256SUMS` and `build-info.json`, publishes
   a prerelease, then resolves and runs fresh SwiftPM consumers on both CPUs from the public
   URL. Only success promotes the release to latest/stable.

The initial development manifest references a local build. Published manifests
always contain an immutable release URL and the real SwiftPM SHA-256 checksum.
After the first release, main points at that release until the next one is made;
local binary tests explicitly use the newly built XCFramework.

A failure after tag publication leaves that version reserved. If the binary or
manifest needs correction, retain the prerelease and publish a new packaging
revision; never overwrite an asset or move a tag. For a transient runner failure,
run **Verify published release** on main with **promote** enabled: it downloads
the existing asset and independently runs public SwiftPM consumers on both CPUs,
then promotes only after both pass. It never rebuilds or changes release bytes. Branch protection
that forbids workflow commits will stop publication before a tag or release is
created. Build/test jobs have read-only permissions; only the manual release job
gets repository write access. Actions are pinned by commit SHA.

## Commander integration

Commander should add the exact package dependency and attach `CLibArchive` to
its `ArchiveCore` target once that target exists and a valid release is available.
The binary build, release assets and dependency upgrades belong exclusively in
this repository. No Commander release workflow needs to compile libarchive.

## Licenses

Packaging scripts are MIT licensed. Upstream licenses are preserved separately
under `LICENSES/` and inside every XCFramework ZIP. libarchive's `COPYING` includes
its component notices; zlib uses the zlib license, bzip2 its BSD-style license,
liblzma uses 0BSD, and zstd is distributed here under its BSD license option.
Applications redistributing the static binary must carry these third-party
notices, for example in their About/license acknowledgements.
