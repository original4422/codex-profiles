import AppKit

let target = CommandLine.arguments[1]
let badge = CommandLine.arguments[2]
let side = 1024
let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: side, pixelsHigh: side,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
    isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
NSColor.clear.setFill()
NSRect(x: 0, y: 0, width: side, height: side).fill()
let rect = NSRect(x: 56, y: 56, width: 912, height: 912)
NSColor(calibratedRed: 0.12, green: 0.25, blue: 0.78, alpha: 1).setFill()
NSBezierPath(roundedRect: rect, xRadius: 215, yRadius: 215).fill()
let style = NSMutableParagraphStyle()
style.alignment = .center
var fontSize: CGFloat = 510
let naturalWidth = (badge as NSString).size(withAttributes: [
    .font: NSFont.systemFont(ofSize: fontSize, weight: .bold)
]).width
if naturalWidth > 780 { fontSize *= 780 / naturalWidth }
let number: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: fontSize, weight: .bold),
    .foregroundColor: NSColor.white, .paragraphStyle: style,
]
let textHeight = (badge as NSString).size(withAttributes: number).height
(badge as NSString).draw(
    in: NSRect(x: 80, y: 530 - textHeight / 2, width: 864, height: textHeight),
    withAttributes: number)
let label: [NSAttributedString.Key: Any] = [
    .font: NSFont.monospacedSystemFont(ofSize: 105, weight: .semibold),
    .foregroundColor: NSColor.white.withAlphaComponent(0.9), .paragraphStyle: style,
]
("CODEX" as NSString).draw(
    in: NSRect(x: 80, y: 170, width: 864, height: 140), withAttributes: label)
NSGraphicsContext.restoreGraphicsState()
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: target))
