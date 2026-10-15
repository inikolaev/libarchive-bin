// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "libarchive-bin",
    platforms: [.macOS(.v13)],
    products: [.library(name: "CLibArchive", targets: ["CLibArchive"])],
    targets: [
        .binaryTarget(
            name: "CLibArchive",
            url: "https://github.com/inikolaev/libarchive-bin/releases/download/3.8.10-1/CLibArchive.xcframework.zip",
            checksum: "bb978072f487c0d8478052f124408d334866e60dff46d67eee576fcffc0c587d"
        )
    ]
)
