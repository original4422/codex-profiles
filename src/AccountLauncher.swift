import AppKit

// The launcher stays in the Dock; the unmodified official app is a separate process.
final class Launcher: NSObject, NSApplicationDelegate {
    private var running: Process?
    private let info = Bundle.main.infoDictionary ?? [:]
    private var profile: String { info["AccountProfile"] as? String ?? "" }
    private var displayName: String { info["CFBundleName"] as? String ?? "Codex Account" }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let main = NSMenu()
        let item = NSMenuItem()
        main.addItem(item)
        let menu = NSMenu(title: displayName)
        item.submenu = menu
        menu.addItem(
            withTitle: "Open \(displayName) Desktop", action: #selector(openDesktop),
            keyEquivalent: "o"
        ).target = self
        menu.addItem(
            withTitle: "Open Account CLI", action: #selector(openTerminal), keyEquivalent: "t"
        ).target = self
        menu.addItem(NSMenuItem.separator())
        menu.addItem(
            withTitle: "Quit Launcher", action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q")
        NSApp.mainMenu = main
        run("desktop")
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool)
        -> Bool
    {
        run("desktop")
        return false
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    func applicationDockMenu(_ sender: NSApplication) -> NSMenu? {
        let menu = NSMenu()
        menu.addItem(
            withTitle: "Open \(displayName) Desktop", action: #selector(openDesktop),
            keyEquivalent: ""
        ).target = self
        menu.addItem(
            withTitle: "Open Account CLI", action: #selector(openTerminal), keyEquivalent: ""
        ).target = self
        return menu
    }

    @objc private func openDesktop() { run("desktop") }
    @objc private func openTerminal() { run("terminal") }

    private func run(_ command: String) {
        guard running == nil else { return }
        guard let python = info["AccountPython"] as? String,
            let engine = info["AccountEngine"] as? String,
            let root = info["AccountRoot"] as? String, !profile.isEmpty
        else {
            showError("Launcher configuration is incomplete. Run the installer again.")
            return
        }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: python)
        task.arguments = [engine, "--root", root, command, profile]
        task.currentDirectoryURL = FileManager.default.homeDirectoryForCurrentUser
        let errors = Pipe()
        task.standardError = errors
        task.standardOutput = FileHandle.nullDevice
        running = task
        task.terminationHandler = { [weak self] process in
            let message =
                String(data: errors.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)
                ?? ""
            DispatchQueue.main.async {
                self?.running = nil
                if process.terminationStatus != 0 { self?.showError(message) }
            }
        }
        do { try task.run() } catch {
            running = nil
            showError(error.localizedDescription)
        }
    }

    private func showError(_ message: String) {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = "Unable to open \(displayName)"
        alert.informativeText = message
        alert.runModal()
    }
}

let delegate = Launcher()
let app = NSApplication.shared
app.setActivationPolicy(.regular)
app.delegate = delegate
app.run()
