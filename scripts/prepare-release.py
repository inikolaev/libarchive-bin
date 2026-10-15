#!/usr/bin/env python3
"""Replace the manifest only with the checksum of the tested release asset."""
import hashlib
import json
import re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
lock = json.loads((root/'sources.lock.json').read_text())
version = lock['packageVersion']
assert re.fullmatch(re.escape(lock['sources']['libarchive']['version']) + r'-[1-9][0-9]*', version)
checksum = hashlib.sha256((root/'dist/CLibArchive.xcframework.zip').read_bytes()).hexdigest()
assert (root/'dist/SHA256SUMS').read_text() == checksum + '  CLibArchive.xcframework.zip\n'
(root/'Package.swift').write_text(f'''// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "libarchive-bin",
    platforms: [.macOS(.v13)],
    products: [.library(name: "CLibArchive", targets: ["CLibArchive"])],
    targets: [
        .binaryTarget(
            name: "CLibArchive",
            url: "https://github.com/inikolaev/libarchive-bin/releases/download/{version}/CLibArchive.xcframework.zip",
            checksum: "{checksum}"
        )
    ]
)
''')
print(version)
