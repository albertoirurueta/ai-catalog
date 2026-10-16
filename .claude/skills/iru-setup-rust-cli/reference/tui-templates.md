# Terminal UI templates (`ui: tui` only)

The `browse` command and the Ratatui picker. State and key handling are pure (`tui/app.rs`), drawing is a function of
the state (`tui/ui.rs`), and the event loop takes the terminal and the event source as parameters (`tui/mod.rs`) —
so all of it is unit-tested with `TestBackend` and scripted events. Only `browse::run` (raw mode on the real
terminal) is left to the PTY smoke check in SKILL.md Step 7.

Conditional markers (`// >>> <condition>` … `// <<< <condition>` in Rust, `# >>> …` in TOML) and the `__Token__`
placeholders work as described in SKILL.md's "Reference files" section; the marker lines themselves are never
written. A heading suffixed `(condition)` is written only when the condition holds. Every file below was rendered
and verified on 2026-10-16 for `ui: none` and `ui: tui` (Rust 1.99.1; MSRV toolchains 1.85.0 for `ui: none`, 1.88.0 for `ui: tui`) — see SKILL.md
"Verification notes".

### `src/commands/browse.rs` (ui: tui)

```rust
//! `browse [NAMES]...` — a full-screen picker for people. Agents and scripts use `greet NAME --json`.

use std::time::Duration;

use clap::Args;
use ratatui::crossterm::event::{self, Event, KeyCode, KeyEvent, KeyModifiers};

use crate::commands::greet::{greeting, write_greeting};
use crate::error::CliError;
use crate::exit::Exit;
use crate::tui::{App, Outcome, run_app};
use crate::{BIN_NAME, Context, Session};

/// Arguments of `browse`.
#[derive(Debug, Args)]
pub struct BrowseArgs {
    /// Names to choose from.
    #[arg(value_name = "NAMES", default_values = ["Ada", "Grace", "Linus", "Margaret"])]
    pub names: Vec<String>,
}

/// Checks everything `browse` needs before taking over the terminal.
///
/// # Errors
///
/// Exit 2 when stdin/stdout aren't terminals or prompts are disabled; exit 3 for an invalid name.
pub fn preflight(args: &BrowseArgs, ctx: &Context<'_>, session: &Session) -> Result<App, CliError> {
    if !(ctx.terminal.stdin && ctx.terminal.stdout) || session.settings.no_input {
        return Err(CliError::usage(
            "browse needs an interactive terminal (stdin and stdout) and input enabled.",
            format!("Use `{BIN_NAME} greet NAME --json` instead."),
        ));
    }
    for name in &args.names {
        greeting(name)?;
    }
    Ok(App::new(args.names.clone()))
}

/// Runs `browse`: the picker on the real terminal, then the chosen greeting on stdout.
///
/// # Errors
///
/// See [`preflight`]; plus exit 130 on Ctrl-C and the I/O error of the terminal or the write.
pub fn run(args: &BrowseArgs, ctx: &mut Context<'_>, session: &Session) -> Result<(), CliError> {
    let mut app = preflight(args, ctx, session)?;
    // SIGTERM/SIGINT must not kill the process while the terminal is in raw mode: defer them, poll for events
    // with a timeout, and turn a recorded signal into the same exit path as Ctrl-C.
    let _deferred = ctx.signals.defer();
    let signals = ctx.signals.clone();
    let next_event = move || {
        loop {
            if signals.received().is_some() {
                return Ok(Event::Key(KeyEvent::new(
                    KeyCode::Char('c'),
                    KeyModifiers::CONTROL,
                )));
            }
            if event::poll(Duration::from_millis(100))? {
                return event::read();
            }
        }
    };
    // `ratatui::run` enters raw mode and the alternate screen and restores both afterwards — also on a panic,
    // through the hook `ratatui::init` installs.
    let outcome = ratatui::run(|terminal| run_app(terminal, &mut app, next_event))?;
    finish(outcome, ctx, session)
}

/// Turns the picker's outcome into output and an exit code.
///
/// # Errors
///
/// Exit 130 for Ctrl-C, or the I/O error of the write.
pub fn finish(outcome: Outcome, ctx: &mut Context<'_>, session: &Session) -> Result<(), CliError> {
    match outcome {
        Outcome::Selected(name) => write_greeting(ctx, session, &greeting(&name)?),
        Outcome::Quit => Ok(()),
        Outcome::Interrupted => Err(CliError::new(Exit::Interrupted, "Interrupted.")),
    }
}
```

### `src/tui/mod.rs` (ui: tui)

```rust
//! The full-screen picker behind `browse`: state ([`app`]), drawing ([`ui`]) and the event loop.
//!
//! The loop takes the terminal and the event source as parameters, so tests drive it with ratatui's
//! `TestBackend` and a scripted list of key events — no real terminal needed.

pub mod app;
pub mod ui;

use std::io;

use ratatui::Terminal;
use ratatui::backend::Backend;
use ratatui::crossterm::event::Event;

pub use app::{App, Outcome};

/// Draws `app` and feeds it events until it produces an [`Outcome`].
///
/// # Errors
///
/// Returns the error of drawing or of reading the next event.
pub fn run_app<B: Backend>(
    terminal: &mut Terminal<B>,
    app: &mut App,
    mut next_event: impl FnMut() -> io::Result<Event>,
) -> io::Result<Outcome> {
    loop {
        terminal
            .draw(|frame| ui::render(frame, app))
            .map_err(|e| io::Error::other(e.to_string()))?;
        if let Event::Key(key) = next_event()?
            && let Some(outcome) = app.handle_key(key)
        {
            return Ok(outcome);
        }
    }
}

#[cfg(test)]
mod tests {
    use std::collections::VecDeque;
    use std::io;

    use ratatui::Terminal;
    use ratatui::backend::TestBackend;
    use ratatui::crossterm::event::{Event, KeyCode, KeyEvent};

    use super::{App, Outcome, run_app};

    fn script(events: Vec<Event>) -> impl FnMut() -> io::Result<Event> {
        let mut queue: VecDeque<Event> = events.into();
        move || {
            queue
                .pop_front()
                .ok_or_else(|| io::Error::other("no more events"))
        }
    }

    #[test]
    fn moving_down_and_pressing_enter_selects_the_second_name() {
        let mut terminal = Terminal::new(TestBackend::new(40, 10)).expect("terminal");
        let mut app = App::new(vec!["Ada".into(), "Grace".into()]);
        let events = vec![
            Event::FocusGained,
            Event::Key(KeyEvent::from(KeyCode::Down)),
            Event::Key(KeyEvent::from(KeyCode::Enter)),
        ];
        let outcome = run_app(&mut terminal, &mut app, script(events)).expect("run");
        assert_eq!(outcome, Outcome::Selected("Grace".into()));
    }

    #[test]
    fn event_errors_propagate() {
        let mut terminal = Terminal::new(TestBackend::new(40, 10)).expect("terminal");
        let mut app = App::new(vec!["Ada".into()]);
        assert!(run_app(&mut terminal, &mut app, script(Vec::new())).is_err());
    }
}
```

### `src/tui/app.rs` (ui: tui)

```rust
//! Picker state and key handling — pure logic, no terminal.

use ratatui::crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use ratatui::widgets::ListState;

/// How the picker ended.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Outcome {
    /// The user chose this name (Enter).
    Selected(String),
    /// The user left without choosing (`q` or Esc).
    Quit,
    /// The user pressed Ctrl-C (the terminal is in raw mode, so it arrives as a key, not as SIGINT).
    Interrupted,
}

/// The picker's state: the names and the highlighted row.
#[derive(Clone, Debug)]
pub struct App {
    names: Vec<String>,
    state: ListState,
}

impl App {
    /// A picker over `names`, highlighting the first one.
    #[must_use]
    pub fn new(names: Vec<String>) -> Self {
        let selected = if names.is_empty() { None } else { Some(0) };
        Self {
            names,
            state: ListState::default().with_selected(selected),
        }
    }

    /// The names shown.
    #[must_use]
    pub fn names(&self) -> &[String] {
        &self.names
    }

    /// The highlighted name, if any.
    #[must_use]
    pub fn selected(&self) -> Option<&str> {
        self.state
            .selected()
            .and_then(|i| self.names.get(i))
            .map(String::as_str)
    }

    /// The list widget state (scroll offset and selection) for rendering.
    pub fn list_state(&mut self) -> &mut ListState {
        &mut self.state
    }

    /// Applies one key press; returns the outcome when the picker should close.
    pub fn handle_key(&mut self, key: KeyEvent) -> Option<Outcome> {
        if key.kind != KeyEventKind::Press {
            return None;
        }
        match key.code {
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                Some(Outcome::Interrupted)
            }
            KeyCode::Char('q') | KeyCode::Esc => Some(Outcome::Quit),
            KeyCode::Enter => self
                .selected()
                .map(|name| Outcome::Selected(name.to_owned())),
            KeyCode::Down | KeyCode::Char('j') => {
                self.move_by(1);
                None
            }
            KeyCode::Up | KeyCode::Char('k') => {
                self.move_by(-1);
                None
            }
            _ => None,
        }
    }

    fn move_by(&mut self, delta: isize) {
        let Some(last) = self.names.len().checked_sub(1) else {
            return;
        };
        let current = self.state.selected().unwrap_or(0);
        let next = current.saturating_add_signed(delta).min(last);
        self.state.select(Some(next));
    }
}

#[cfg(test)]
mod tests {
    use ratatui::crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyModifiers};

    use super::{App, Outcome};

    fn press(code: KeyCode) -> KeyEvent {
        KeyEvent::from(code)
    }

    #[test]
    fn navigation_stays_in_bounds() {
        let mut app = App::new(vec!["Ada".into(), "Grace".into()]);
        assert_eq!(app.selected(), Some("Ada"));
        assert_eq!(app.handle_key(press(KeyCode::Up)), None);
        assert_eq!(app.selected(), Some("Ada"));
        app.handle_key(press(KeyCode::Char('j')));
        app.handle_key(press(KeyCode::Down));
        assert_eq!(app.selected(), Some("Grace"));
        app.handle_key(press(KeyCode::Char('k')));
        assert_eq!(app.selected(), Some("Ada"));
        assert_eq!(app.handle_key(press(KeyCode::Char('x'))), None);
        assert_eq!(app.names().len(), 2);
    }

    #[test]
    fn enter_quit_and_ctrl_c_close_the_picker() {
        let mut app = App::new(vec!["Ada".into()]);
        assert_eq!(
            app.handle_key(press(KeyCode::Enter)),
            Some(Outcome::Selected("Ada".into()))
        );
        assert_eq!(
            app.handle_key(press(KeyCode::Char('q'))),
            Some(Outcome::Quit)
        );
        assert_eq!(app.handle_key(press(KeyCode::Esc)), Some(Outcome::Quit));
        let ctrl_c = KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL);
        assert_eq!(app.handle_key(ctrl_c), Some(Outcome::Interrupted));
        let release =
            KeyEvent::new_with_kind(KeyCode::Enter, KeyModifiers::NONE, KeyEventKind::Release);
        assert_eq!(app.handle_key(release), None);
    }

    #[test]
    fn an_empty_list_selects_nothing() {
        let mut app = App::new(Vec::new());
        app.handle_key(press(KeyCode::Down));
        assert_eq!(app.selected(), None);
        assert_eq!(app.handle_key(press(KeyCode::Enter)), None);
    }
}
```

### `src/tui/ui.rs` (ui: tui)

```rust
//! Drawing the picker: a bordered list and a one-line key help.

use ratatui::Frame;
use ratatui::layout::{Constraint, Layout};
use ratatui::style::{Modifier, Style};
use ratatui::widgets::{Block, List, Paragraph};

use super::App;

/// Renders `app` into the whole frame.
pub fn render(frame: &mut Frame, app: &mut App) {
    let [list_area, help_area] =
        Layout::vertical([Constraint::Min(1), Constraint::Length(1)]).areas(frame.area());
    let list = List::new(app.names().to_vec())
        .block(Block::bordered().title(" Pick a name "))
        .highlight_style(Style::new().add_modifier(Modifier::REVERSED))
        .highlight_symbol("> ");
    frame.render_stateful_widget(list, list_area, app.list_state());
    frame.render_widget(
        Paragraph::new("Up/Down move  Enter select  q quit"),
        help_area,
    );
}

#[cfg(test)]
mod tests {
    use ratatui::Terminal;
    use ratatui::backend::TestBackend;

    use super::render;
    use crate::tui::App;

    #[test]
    fn draws_the_list_with_the_selection_marked() {
        let mut terminal = Terminal::new(TestBackend::new(30, 6)).expect("terminal");
        let mut app = App::new(vec!["Ada".into(), "Grace".into()]);
        terminal
            .draw(|frame| render(frame, &mut app))
            .expect("draw");
        let text: String = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(ratatui::buffer::Cell::symbol)
            .collect();
        assert!(text.contains("Pick a name"));
        assert!(text.contains("> Ada"));
        assert!(text.contains("  Grace"));
        assert!(text.contains("Enter select"));
    }
}
```
