# TUI templates — `ui: tui` only

A Bubble Tea v2 (`charm.land/bubbletea/v2`) full-screen list behind the `browse` subcommand, styled with Lip Gloss v2
(`charm.land/lipgloss/v2`). The model's `Update`/`View` are pure and unit-tested; the full program is tested with
teatest v2 (`github.com/charmbracelet/x/exp/teatest/v2`). `browse` starts only when stdin and stdout are terminals and
the output format is text; otherwise it exits 2 and points at `greet NAME --json` — the TUI is an addition for
people, never the only way to do something. Every file below is written only for `ui: tui`.

Conditional markers and `__TOKEN__` placeholders work as described in SKILL.md's "Reference files" section. Verified
on 2026-10-16 with Bubble Tea v2.1.0, Lip Gloss v2.0.6 and teatest v2 (pseudo-version
`v2.0.0-20261012121918-43427fdbad12`) — see SKILL.md "Verification notes".

### `internal/tui/model.go` (ui: tui)

```go
// Package tui is the full-screen terminal interface of `__BIN__ browse`: a
// list of names to pick one to greet. The model is pure (Update and View
// have no side effects), so it is tested without a terminal; Run starts the
// Bubble Tea program on the streams it is given.
package tui

import (
	"context"
	"io"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

var (
	titleStyle    = lipgloss.NewStyle().Bold(true)
	selectedStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("6"))
	helpStyle     = lipgloss.NewStyle().Faint(true)
)

// Model is the state of the browse list.
type Model struct {
	names       []string
	cursor      int
	chosen      string
	interrupted bool
}

// New returns a model listing names with the cursor on the first one.
func New(names []string) Model {
	return Model{names: names}
}

// DemoNames returns the sample names browse lists.
func DemoNames() []string {
	return []string{"Ada", "Grace", "Linus", "Margaret"}
}

// Init starts the program with no command.
func (m Model) Init() tea.Cmd { return nil }

// Update moves the cursor (up/down, k/j), chooses the name under it (enter),
// quits without choosing (q, esc) or interrupts (ctrl+c).
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyPressMsg)
	if !ok {
		return m, nil
	}
	switch key.String() {
	case "ctrl+c":
		m.interrupted = true
		return m, tea.Interrupt
	case "q", "esc":
		return m, tea.Quit
	case "up", "k":
		if m.cursor > 0 {
			m.cursor--
		}
	case "down", "j":
		if m.cursor < len(m.names)-1 {
			m.cursor++
		}
	case "enter":
		if len(m.names) > 0 {
			m.chosen = m.names[m.cursor]
		}
		return m, tea.Quit
	}
	return m, nil
}

// View renders the list in the alternate screen.
func (m Model) View() tea.View {
	var b strings.Builder
	b.WriteString(titleStyle.Render("Who should we greet?") + "\n\n")
	for i, name := range m.names {
		if i == m.cursor {
			b.WriteString(selectedStyle.Render("> "+name) + "\n")
			continue
		}
		b.WriteString("  " + name + "\n")
	}
	b.WriteString("\n" + helpStyle.Render("up/down or k/j to move, enter to greet, q to quit") + "\n")
	v := tea.NewView(b.String())
	v.AltScreen = true
	return v
}

// Chosen returns the name picked with enter, or "" when the user quit.
func (m Model) Chosen() string { return m.chosen }

// Interrupted reports whether the user pressed ctrl+c.
func (m Model) Interrupted() bool { return m.interrupted }

// Run shows the list on in/out until the user chooses a name or quits, and
// returns the chosen name ("" when none). Bubble Tea restores the terminal
// before Run returns; ctrl+c returns tea.ErrInterrupted.
func Run(ctx context.Context, in io.Reader, out io.Writer, names []string) (string, error) {
	final, err := tea.NewProgram(New(names), tea.WithContext(ctx), tea.WithInput(in), tea.WithOutput(out)).Run()
	if err != nil {
		return "", err
	}
	return final.(Model).Chosen(), nil
}
```

### `internal/tui/model_test.go` (ui: tui)

```go
package tui

import (
	"bytes"
	"context"
	"errors"
	"io"
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/exp/teatest/v2"
)

func press(m tea.Model, keys ...tea.KeyPressMsg) (Model, tea.Cmd) {
	var cmd tea.Cmd
	for _, k := range keys {
		m, cmd = m.Update(k)
	}
	return m.(Model), cmd
}

var (
	down  = tea.KeyPressMsg{Code: tea.KeyDown}
	up    = tea.KeyPressMsg{Code: tea.KeyUp}
	enter = tea.KeyPressMsg{Code: tea.KeyEnter}
)

func TestCursorStaysInBounds(t *testing.T) {
	m, _ := press(New(DemoNames()), up, down, down, down, down, down)
	if m.cursor != len(DemoNames())-1 {
		t.Fatalf("cursor = %d, want last", m.cursor)
	}
	m, _ = press(m, tea.KeyPressMsg{Code: 'k', Text: "k"}, up, up, up, up)
	if m.cursor != 0 {
		t.Fatalf("cursor = %d, want 0", m.cursor)
	}
}

func TestEnterChoosesAndQuits(t *testing.T) {
	m, cmd := press(New(DemoNames()), tea.KeyPressMsg{Code: 'j', Text: "j"}, enter)
	if m.Chosen() != "Grace" {
		t.Fatalf("Chosen() = %q, want Grace", m.Chosen())
	}
	if _, ok := cmd().(tea.QuitMsg); !ok {
		t.Fatal("enter did not quit")
	}
}

func TestQuitAndInterrupt(t *testing.T) {
	m, cmd := press(New(DemoNames()), tea.KeyPressMsg{Code: 'q', Text: "q"})
	if m.Chosen() != "" || m.Interrupted() {
		t.Fatalf("q chose %q / interrupted %v", m.Chosen(), m.Interrupted())
	}
	if _, ok := cmd().(tea.QuitMsg); !ok {
		t.Fatal("q did not quit")
	}
	m, cmd = press(New(DemoNames()), tea.KeyPressMsg{Code: 'c', Mod: tea.ModCtrl})
	if !m.Interrupted() {
		t.Fatal("ctrl+c did not interrupt")
	}
	if _, ok := cmd().(tea.InterruptMsg); !ok {
		t.Fatal("ctrl+c did not send InterruptMsg")
	}
}

func TestEmptyListAndOtherMessages(t *testing.T) {
	m, _ := press(New(nil), down, enter)
	if m.Chosen() != "" {
		t.Fatalf("Chosen() = %q on an empty list", m.Chosen())
	}
	next, cmd := New(DemoNames()).Update(tea.WindowSizeMsg{Width: 80, Height: 24})
	if cmd != nil || next.(Model).cursor != 0 {
		t.Fatal("a non-key message changed the model")
	}
	if New(nil).Init() != nil {
		t.Fatal("Init returned a command")
	}
}

func TestViewMarksTheCursor(t *testing.T) {
	m, _ := press(New(DemoNames()), down)
	v := m.View()
	if !v.AltScreen {
		t.Fatal("view is not in the alternate screen")
	}
	if !strings.Contains(v.Content, "> Grace") || !strings.Contains(v.Content, "  Ada") {
		t.Fatalf("unexpected view:\n%s", v.Content)
	}
}

func TestProgramWithTeatest(t *testing.T) {
	tm := teatest.NewTestModel(t, New(DemoNames()), teatest.WithInitialTermSize(80, 24))
	teatest.WaitFor(t, tm.Output(), func(b []byte) bool { return bytes.Contains(b, []byte("Ada")) },
		teatest.WithDuration(5*time.Second))
	tm.Send(down)
	tm.Send(down)
	tm.Send(enter)
	final := tm.FinalModel(t, teatest.WithFinalTimeout(5*time.Second)).(Model)
	if final.Chosen() != "Linus" {
		t.Fatalf("Chosen() = %q, want Linus", final.Chosen())
	}
}

func TestRunReturnsTheChoice(t *testing.T) {
	name, err := Run(context.Background(), strings.NewReader("j\r"), io.Discard, DemoNames())
	if err != nil || name != "Grace" {
		t.Fatalf("Run() = %q, %v; want Grace", name, err)
	}
}

func TestRunStopsWhenTheContextIsCanceled(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	reader, writer := io.Pipe()
	defer func() { _ = writer.Close() }()
	if _, err := Run(ctx, reader, io.Discard, DemoNames()); !errors.Is(err, tea.ErrProgramKilled) {
		t.Fatalf("Run() error = %v, want ErrProgramKilled", err)
	}
}
```

### `internal/cli/browse.go` (ui: tui)

```go
package cli

import (
	"errors"

	tea "charm.land/bubbletea/v2"
	"github.com/spf13/cobra"

	"__MODULE__/internal/tui"
)

func newBrowseCommand(a *App) *cobra.Command {
	return &cobra.Command{
		Use:   "browse",
		Short: "Pick a name from a full-screen list and greet it (interactive)",
		Long: "Use browse at a terminal to pick a name interactively. It needs a terminal on stdin and stdout and " +
			"exits with code 2 otherwise; scripts and agents use `__BIN__ greet NAME --json` instead, which does the " +
			"same without a terminal.",
		Example:     "  __BIN__ browse",
		Args:        cobra.NoArgs,
		Annotations: safety(true, false, true),
		RunE: func(cmd *cobra.Command, _ []string) error {
			if !a.IsTerminal(a.In) || !a.IsTerminal(a.Out) || a.format().Machine() {
				return NewError(ExitUsage, "TTY_REQUIRED",
					"browse needs an interactive terminal on stdin and stdout and text output.",
					"Use `__BIN__ greet NAME --json` instead.")
			}
			name, err := a.runTUI(cmd.Context(), a.In, a.Out, tui.DemoNames())
			switch {
			case errors.Is(err, tea.ErrInterrupted):
				return NewError(ExitInterrupted, "", "Interrupted (ctrl+c).", "")
			case err != nil:
				return err
			case name == "":
				return nil
			}
			greeting, err := Greet(name)
			if err != nil {
				return err
			}
			return a.emit("Hello, "+paint(a.stdoutColor(), sgrBold, greeting.Name)+"!", greeting)
		},
	}
}
```

### `internal/cli/browse_test.go` (ui: tui)

```go
package cli

import (
	"context"
	"errors"
	"io"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
)

func TestBrowseRefusesWithoutATerminal(t *testing.T) {
	app, out, errOut := newTestApp(nil)
	if code := app.Run(context.Background(), []string{"browse"}); code != ExitUsage {
		t.Fatalf("exit code = %d, want 2", code)
	}
	if out.Len() != 0 || !strings.Contains(errOut.String(), "greet NAME --json") {
		t.Fatalf("stdout %q, stderr %q", out, errOut)
	}
}

func TestBrowseGreetsTheChosenName(t *testing.T) {
	tests := []struct {
		name   string
		chosen string
		err    error
		code   ExitCode
		stdout string
	}{
		{"chosen", "Grace", nil, ExitOK, "Hello, Grace!\n"},
		{"quit", "", nil, ExitOK, ""},
		{"ctrl+c", "", tea.ErrInterrupted, ExitInterrupted, ""},
		{"program error", "", errors.New("boom"), ExitInternal, ""},
		{"invalid name", strings.Repeat("x", MaxNameLength+1), nil, ExitValidation, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			app, out, _ := newTestApp(nil)
			app.IsTerminal = func(any) bool { return true }
			app.runTUI = func(context.Context, io.Reader, io.Writer, []string) (string, error) { return tt.chosen, tt.err }
			if code := app.Run(context.Background(), []string{"browse", "--no-color"}); code != tt.code {
				t.Fatalf("exit code = %d, want %d", code, tt.code)
			}
			if out.String() != tt.stdout {
				t.Fatalf("stdout = %q, want %q", out, tt.stdout)
			}
		})
	}
}
```

### `testdata/script/browse.txtar` (ui: tui)

```text
# browse is TTY-gated: without a terminal it exits 2 and points at the
# non-interactive equivalent; stdout stays empty.
status 2 exec __BIN__ browse
! stdout .
stderr 'browse needs an interactive terminal'
stderr 'greet NAME --json'

# JSON mode reports the same as an envelope.
status 2 exec __BIN__ browse --json
stderr '"code":"TTY_REQUIRED"'
```
