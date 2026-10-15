Universal static CLibArchive for macOS 13+: arm64 and x86_64.

Includes libarchive 3.8.10, zlib 1.3.2, bzip2 1.0.8, XZ/liblzma 5.8.4,
and Zstandard 1.5.7. Provides the SwiftPM product and C module `CLibArchive`.

The ZIP includes third-party licenses. SHA256SUMS is the SwiftPM artifact
checksum; build-info.json records source pins and the build toolchain.

Validated with ZIP, 7z, tar, gzip, bzip2, xz, zstd, malformed-input tests,
SwiftPM imports, runtime dependency checks and native tests on both CPUs.
