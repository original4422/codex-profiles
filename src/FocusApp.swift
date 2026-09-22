import AppKit

guard CommandLine.arguments.count == 2,
      let pid = Int32(CommandLine.arguments[1]),
      let app = NSRunningApplication(processIdentifier: pid), !app.isTerminated else {
    exit(1)
}
app.unhide()
exit(app.activate(options: [.activateAllWindows, .activateIgnoringOtherApps]) ? 0 : 1)
