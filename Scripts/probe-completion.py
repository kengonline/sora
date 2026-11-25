"""Temporary native-input instrumentation for the diagnostic fork branch only."""
from pathlib import Path

path = Path('Sora/Terminal/GhosttySurfaceView.swift')
text = path.read_text()
text = text.replace('private var isShellPromptReady = false', 'private var isShellPromptReady = false\n    private var didProbeCompletion = false')
text = text.replace('private func finishStartupInput() {', '''private func finishStartupInput() {
        if !didProbeCompletion, isShellPromptReady, shellEditLine != nil,
           ProcessInfo.processInfo.environment["SORA_COMPLETION_PROBE"] == "1" {
            didProbeCompletion = true
            Task { @MainActor in await probeCompletion() }
        }
''')
text += r'''

extension GhosttySurfaceView {
    private func probeCompletion() async {
        func log(_ label: String) {
            print("PROBE \(label): line=\(String(reflecting: shellEditLine)) cursor=\(shellCursorOffset) tracked=\(completion.buffer.isTracking) buffer=\(String(reflecting: completion.buffer.text)) suggestion=\(String(reflecting: completion.suggestion))")
            fflush(stdout)
        }
        func key(_ code: UInt16, _ text: String) {
            let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window?.windowNumber ?? 0,
                context: nil, characters: text, charactersIgnoringModifiers: text, isARepeat: false, keyCode: code)!
            keyDown(with: event)
            let release = NSEvent.keyEvent(with: .keyUp, location: .zero, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window?.windowNumber ?? 0,
                context: nil, characters: text, charactersIgnoringModifiers: text, isARepeat: false, keyCode: code)!
            keyUp(with: release)
        }
        do {
            try await Task.sleep(for: .seconds(1))
            window?.makeFirstResponder(self)
            let cwd = lastWorkingDirectory ?? initialWorkingDirectory ?? FileManager.default.homeDirectoryForCurrentUser
            let run = CommandRunFactory.make(command: "docker start postgres17.5", cwd: cwd, exitCode: 0, durationNanos: 1)!
            try runtime.history.record(run)
            log("initial")
            for character in "docker sta" { key(character == " " ? 49 : 0, String(character)) }
            try await Task.sleep(for: .seconds(2))
            log("typed prefix")
            key(PromptEvent.tab, "\t")
            try await Task.sleep(for: .seconds(1))
            log("accepted Tab")
            key(PromptEvent.delete, "\u{7f}")
            key(PromptEvent.delete, "\u{7f}")
            try await Task.sleep(for: .seconds(1))
            log("deleted .5")
            key(47, ".")
            key(22, "6")
            try await Task.sleep(for: .seconds(1))
            log("replaced with .6")
            let passed = shellEditLine == "docker start postgres17.6"
            print("PROBE RESULT: \(passed ? "PASS" : "FAIL")")
            fflush(stdout)
            exit(passed ? 0 : 1)
        } catch {
            print("PROBE ERROR: \(error)")
            fflush(stdout)
            exit(2)
        }
    }
}
'''
path.write_text(text)
