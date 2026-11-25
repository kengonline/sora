"""Temporary native-input instrumentation for the diagnostic fork branch only."""
from pathlib import Path

path = Path('Sora/Terminal/GhosttySurfaceView.swift')
text = path.read_text()
text = text.replace('private var isShellPromptReady = false', 'private var isShellPromptReady = false\n    private var didProbeCompletion = false')
text = text.replace('            createSurfaceIfNeeded()', r'''            createSurfaceIfNeeded()
            DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
                guard let self else { return }
                print("PROBE startup: surface=\(self.surface != nil) foreground=\(self.foregroundExecutable ?? "nil") ready=\(self.isShellPromptReady) line=\(String(reflecting: self.shellEditLine))")
                fflush(stdout)
            }
''')
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
            print("PROBE \(label): line=\(String(reflecting: shellEditLine)) cursor=\(shellCursorOffset) tracked=\(completion.buffer.isTracking) buffer=\(String(reflecting: completion.buffer.text)) history=\(commandHistory.isPresented) selected=\(String(reflecting: commandHistory.selected?.command)) focused=\(window?.firstResponder === self)")
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
            try runtime.history.record(run, tabID: tabID)
            log("initial")
            // A prior probe may have checkpointed its unsent draft. Start at
            // a genuinely empty shell prompt, as in the reported reproduction.
            cancelPromptLine()
            completion.reset()
            try await Task.sleep(for: .seconds(1))
            window?.makeFirstResponder(self)
            for character in "clear" { key(0, String(character)) }
            try await Task.sleep(for: .seconds(1))
            log("before clear")
            guard shellEditLine == "clear" else {
                print("PROBE SETUP FAILED: shell did not receive the clear command")
                fflush(stdout)
                exit(2)
            }
            key(PromptEvent.returnKey, "\r")
            try await Task.sleep(for: .seconds(2))
            log("after clear")
            window?.makeKeyAndOrderFront(nil)
            window?.makeFirstResponder(self)
            key(PromptEvent.upArrow, "\u{f700}")
            try await Task.sleep(for: .seconds(1))
            if commandHistory.selected?.command == "clear" {
                key(PromptEvent.upArrow, "\u{f700}")
            }
            try await Task.sleep(for: .seconds(1))
            log("recalled command")
            guard commandHistory.isPresented,
                  commandHistory.selected?.command == "docker start postgres17.5" else {
                print("PROBE SETUP FAILED: expected history command was not selected")
                fflush(stdout)
                exit(2)
            }
            key(PromptEvent.delete, "\u{7f}")
            try await Task.sleep(for: .seconds(1))
            log("first Backspace")
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

configuration = Path('Sora/Resources/sora.ghostty')
config = configuration.read_text()
if '# Native completion probe shell' not in config:
    configuration.write_text(config + '\n# Native completion probe shell\ncommand = /bin/zsh\n')

bootstrap = Path('Sora/Resources/zsh/zshenv')
startup = bootstrap.read_text()
marker = '# Reproduce the reported cached-completion shortcut conflict.'
if marker not in startup:
    bootstrap.write_text(startup + '\n' + marker + '''
if [[ -o interactive ]]; then
  autoload -Uz _read_comp
  zle -C _read_comp .complete-word _read_comp
  for keymap in emacs viins vicmd; do
    bindkey -M "$keymap" '^X^R' _read_comp
  done
fi
''')
