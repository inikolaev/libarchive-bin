// swift-tools-version: 6.0
import PackageDescription

// Development checkout: build first. Release tags use a URL and verified checksum.
let package = Package(
    name: "libarchive-bin",
    platforms: [.macOS(.v13)],
    products: [.library(name: "CLibArchive", targets: ["CLibArchive"])],
    targets: [.binaryTarget(name: "CLibArchive", path: "dist/CLibArchive.xcframework")]
)
