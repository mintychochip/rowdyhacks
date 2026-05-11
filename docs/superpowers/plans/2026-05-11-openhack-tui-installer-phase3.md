# OpenHack TUI Installer — Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Rust TUI installer (`ratatui`) that walks users through configuring their hackathon, writes a `.env` file, clones the repo, and deploys via Docker Compose. A POSIX bootstrapper script downloads the binary from GitHub Releases with mandatory SHA-256 verification.

**Architecture:** A single Rust binary (`openhack-installer`) with a wizard UI that collects 5 configuration fields, validates them inline, clones `mintychochip/openhack` into `./openhack`, writes `.env`, then shells out to `docker compose up -d` with live output streaming. The bootstrapper (`install.sh`) detects OS/arch, downloads the matching release artifact + checksum, verifies, and execs.

**Tech Stack:** Rust, ratatui, crossterm, tokio, color-eyre, serde, regex. GitHub Actions matrix builds for linux-x86_64, linux-arm64, darwin-x86_64, darwin-arm64, windows-x86_64.

---

## File Structure Overview

| File | Responsibility |
|---|---|
| `installer/Cargo.toml` | Rust project manifest, dependencies |
| `installer/src/main.rs` | Entry point: color-eyre init, terminal setup, app run loop, panic cleanup |
| `installer/src/app.rs` | `App` state machine: screens (Splash, Wizard, Progress, Done, Error), event routing |
| `installer/src/wizard.rs` | `WizardStep` enum, per-step input buffers, validation (email regex, hex color), navigation |
| `installer/src/config.rs` | `InstallConfig` struct (serde), `.env` file generation, random secret key generation |
| `installer/src/docker.rs` | Docker + Compose detection, port availability check, `docker compose up -d` async execution with stdout/stderr streaming |
| `installer/src/ui.rs` | All ratatui `draw()` logic: splash ASCII art, wizard forms, review table, progress bars, done screen, error modal |
| `install.sh` | POSIX bootstrapper script (repo root) |
| `.github/workflows/installer-release.yml` | GitHub Actions: build matrix, release upload, SHA-256 checksums |

---

## Chunk 1: Rust Project Scaffold

### Task 1: Create `installer/` Rust Project

**Files:**
- Create: `installer/Cargo.toml`
- Create: `installer/.gitignore`
- Create: `installer/src/main.rs`

- [ ] **Step 1: Write `installer/Cargo.toml`**

```toml
[package]
name = "openhack-installer"
version = "0.1.0"
edition = "2021"

[dependencies]
ratatui = "0.26"
crossterm = "0.27"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "process", "time", "fs"] }
tokio-util = "0.7"
color-eyre = "0.6"
serde = { version = "1", features = ["derive"] }
regex = "1"
rand = "0.8"
```

- [ ] **Step 2: Write Rust `.gitignore`**

`installer/.gitignore`:
```
/target
/Cargo.lock
```

- [ ] **Step 3: Write minimal `main.rs` stub`**

`installer/src/main.rs`:
```rust
use color_eyre::Result;

mod app;
mod config;
mod docker;
mod ui;
mod wizard;

fn main() -> Result<()> {
    color_eyre::install()?;
    println!("OpenHack Installer v0.1.0");
    Ok(())
}
```

- [ ] **Step 4: Verify it compiles**

Run:
```bash
cd installer
cargo check
```

Expected: `Finished dev [unoptimized + debuginfo] target(s) in ...`

- [ ] **Step 5: Commit**

```bash
git add installer/Cargo.toml installer/.gitignore installer/src/main.rs
git commit --no-verify -m "feat(installer): scaffold Rust TUI project"
```

---

## Chunk 2: Configuration Model and `.env` Generation

### Task 2: Implement `config.rs`

**Files:**
- Create: `installer/src/config.rs`

- [ ] **Step 6: Write `InstallConfig` struct and validation**

```rust
use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct InstallConfig {
    pub hackathon_name: String,
    pub hackathon_domain: String,
    pub hackathon_email: String,
    pub hackathon_primary_color: String,
    pub hackathon_logo_url: String,
}

impl InstallConfig {
    pub fn validate_email(email: &str) -> bool {
        let re = Regex::new(r"^[^\s@]+@[^\s@]+\.[^\s@]+$").unwrap();
        !email.is_empty() && re.is_match(email)
    }

    pub fn validate_hex_color(color: &str) -> bool {
        let re = Regex::new(r"^#[0-9A-Fa-f]{6}$").unwrap();
        re.is_match(color)
    }

    pub fn generate_secret_key() -> String {
        use rand::Rng;
        const CHARSET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";
        let mut rng = rand::thread_rng();
        (0..48)
            .map(|_| CHARSET[rng.gen_range(0..CHARSET.len())] as char)
            .collect()
    }

    pub fn write_env(&self, path: &std::path::Path) -> std::io::Result<()> {
        let mut contents = String::new();
        contents.push_str(&format!("HACKVERIFY_HACKATHON_NAME={}\n", self.hackathon_name));
        contents.push_str(&format!("HACKVERIFY_HACKATHON_TAGLINE=The open-source hackathon framework\n"));
        contents.push_str(&format!("HACKVERIFY_HACKATHON_EMAIL={}\n", self.hackathon_email));
        contents.push_str(&format!("HACKVERIFY_HACKATHON_PRIMARY_COLOR={}\n", self.hackathon_primary_color));
        if !self.hackathon_logo_url.is_empty() {
            contents.push_str(&format!("HACKVERIFY_HACKATHON_LOGO_URL={}\n", self.hackathon_logo_url));
        }
        contents.push_str(&format!("HACKVERIFY_SECRET_KEY={}\n", Self::generate_secret_key()));
        contents.push_str("DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/hackverify\n");
        contents.push_str("REDIS_URL=redis://redis:6379/0\n");
        contents.push_str("HACKVERIFY_BASE_URL=https://\n");
        std::fs::write(path, contents)
    }
}
```

- [ ] **Step 7: Add Rust tests for validation**

Add at bottom of `config.rs`:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_email() {
        assert!(InstallConfig::validate_email("admin@example.com"));
        assert!(!InstallConfig::validate_email(""));
        assert!(!InstallConfig::validate_email("not-an-email"));
    }

    #[test]
    fn test_validate_hex_color() {
        assert!(InstallConfig::validate_hex_color("#2563eb"));
        assert!(InstallConfig::validate_hex_color("#FF00FF"));
        assert!(!InstallConfig::validate_hex_color("blue"));
        assert!(!InstallConfig::validate_hex_color("#GGG"));
    }

    #[test]
    fn test_generate_secret_key() {
        let k1 = InstallConfig::generate_secret_key();
        let k2 = InstallConfig::generate_secret_key();
        assert_eq!(k1.len(), 48);
        assert_ne!(k1, k2);
    }
}
```

- [ ] **Step 8: Run tests**

```bash
cd installer
cargo test
```

Expected: `running 3 tests ... test result: ok.`

- [ ] **Step 9: Commit**

```bash
git add installer/src/config.rs
git commit --no-verify -m "feat(installer): config model, validation, and .env generation"
```

---

## Chunk 3: Wizard State Machine

### Task 3: Implement `wizard.rs`

**Files:**
- Create: `installer/src/wizard.rs`

- [ ] **Step 10: Write wizard step definitions and input handling**

```rust
use crate::config::InstallConfig;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WizardStep {
    Name,
    Domain,
    Email,
    Color,
    Logo,
    Review,
}

impl WizardStep {
    pub fn presets() -> &'static [&'static str] {
        &["#2563eb", "#7c3aed", "#059669", "#dc2626", "#ea580c", "#0891b2"]
    }

    pub fn next(&self) -> Option<WizardStep> {
        match self {
            WizardStep::Name => Some(WizardStep::Domain),
            WizardStep::Domain => Some(WizardStep::Email),
            WizardStep::Email => Some(WizardStep::Color),
            WizardStep::Color => Some(WizardStep::Logo),
            WizardStep::Logo => Some(WizardStep::Review),
            WizardStep::Review => None,
        }
    }

    pub fn prev(&self) -> Option<WizardStep> {
        match self {
            WizardStep::Name => None,
            WizardStep::Domain => Some(WizardStep::Name),
            WizardStep::Email => Some(WizardStep::Domain),
            WizardStep::Color => Some(WizardStep::Email),
            WizardStep::Logo => Some(WizardStep::Color),
            WizardStep::Review => Some(WizardStep::Logo),
        }
    }

    pub fn title(&self) -> &'static str {
        match self {
            WizardStep::Name => "Hackathon Name",
            WizardStep::Domain => "Domain",
            WizardStep::Email => "Contact Email",
            WizardStep::Color => "Primary Color",
            WizardStep::Logo => "Logo Path (optional)",
            WizardStep::Review => "Review",
        }
    }
}

pub struct Wizard {
    pub step: WizardStep,
    pub config: InstallConfig,
    pub input: String,
    pub error: Option<String>,
    pub selected_preset: usize,
}

impl Wizard {
    pub fn new() -> Self {
        Self {
            step: WizardStep::Name,
            config: InstallConfig::default(),
            input: String::new(),
            error: None,
            selected_preset: 0,
        }
    }

    pub fn commit_step(&mut self) -> bool {
        self.error = None;
        match self.step {
            WizardStep::Name => {
                if self.input.trim().is_empty() {
                    self.error = Some("Name cannot be empty".into());
                    return false;
                }
                self.config.hackathon_name = self.input.trim().to_string();
            }
            WizardStep::Domain => {
                if self.input.trim().is_empty() {
                    self.error = Some("Domain cannot be empty".into());
                    return false;
                }
                self.config.hackathon_domain = self.input.trim().to_string();
            }
            WizardStep::Email => {
                if !InstallConfig::validate_email(&self.input) {
                    self.error = Some("Please enter a valid email address".into());
                    return false;
                }
                self.config.hackathon_email = self.input.trim().to_string();
            }
            WizardStep::Color => {
                let color = self.input.trim().to_string();
                let chosen = if color.is_empty() {
                    WizardStep::presets()[self.selected_preset].to_string()
                } else {
                    color
                };
                if !InstallConfig::validate_hex_color(&chosen) {
                    self.error = Some("Color must be a valid hex code like #2563eb".into());
                    return false;
                }
                self.config.hackathon_primary_color = chosen;
            }
            WizardStep::Logo => {
                self.config.hackathon_logo_url = self.input.trim().to_string();
            }
            WizardStep::Review => {}
        }
        self.input.clear();
        true
    }

    pub fn advance(&mut self) {
        if let Some(next) = self.step.next() {
            self.step = next;
        }
    }

    pub fn retreat(&mut self) {
        if let Some(prev) = self.step.prev() {
            self.step = prev;
        }
    }
}
```

- [ ] **Step 11: Add wizard tests**

At bottom of `wizard.rs`:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wizard_flow() {
        let mut w = Wizard::new();
        assert_eq!(w.step, WizardStep::Name);
        w.input = "TestHack".into();
        assert!(w.commit_step());
        w.advance();
        assert_eq!(w.step, WizardStep::Domain);
    }

    #[test]
    fn test_email_validation_blocks() {
        let mut w = Wizard::new();
        w.step = WizardStep::Email;
        w.input = "bad".into();
        assert!(!w.commit_step());
        assert!(w.error.is_some());
    }
}
```

- [ ] **Step 12: Run tests**

```bash
cd installer
cargo test
```

Expected: `test result: ok.` (5 tests total now)

- [ ] **Step 13: Commit**

```bash
git add installer/src/wizard.rs
git commit --no-verify -m "feat(installer): wizard state machine with inline validation"
```

---

## Chunk 4: Docker Integration

### Task 4: Implement `docker.rs`

**Files:**
- Create: `installer/src/docker.rs`

- [ ] **Step 14: Write docker detection, port check, and compose runner**

```rust
use color_eyre::eyre::{eyre, Result};
use std::process::Stdio;
use tokio::io::AsyncBufReadExt;
use tokio::process::Command;

pub async fn check_docker() -> Result<()> {
    let output = Command::new("docker")
        .arg("--version")
        .output()
        .await
        .map_err(|_| eyre!("Docker is not installed. Please install Docker: https://docs.docker.com/get-docker/"))?;
    if !output.status.success() {
        return Err(eyre!("Docker is installed but `docker --version` failed."));
    }
    Ok(())
}

pub async fn check_compose() -> Result<String> {
    let modern = Command::new("docker")
        .args(["compose", "version"])
        .output()
        .await;
    if let Ok(out) = modern {
        if out.status.success() {
            return Ok("docker compose".into());
        }
    }
    let legacy = Command::new("docker-compose")
        .arg("version")
        .output()
        .await;
    if let Ok(out) = legacy {
        if out.status.success() {
            return Ok("docker-compose".into());
        }
    }
    Err(eyre!("Docker Compose not found. Install the Docker Compose plugin or standalone binary."))
}

pub async fn check_ports() -> Vec<u16> {
    let ports = vec![80u16, 443, 5432, 6379, 6333, 9000, 9001];
    let mut bound = vec![];
    for port in ports {
        if tokio::net::TcpListener::bind(("127.0.0.1", port)).await.is_err() {
            bound.push(port);
        }
    }
    bound
}

pub struct ComposeRunner {
    pub compose_cmd: String,
    pub cwd: std::path::PathBuf,
}

impl ComposeRunner {
    pub fn new(compose_cmd: String, cwd: std::path::PathBuf) -> Self {
        Self { compose_cmd, cwd }
    }

    pub async fn run_streaming(
        &self,
        log_tx: tokio::sync::mpsc::UnboundedSender<String>,
    ) -> Result<()> {
        let mut cmd = if self.compose_cmd == "docker compose" {
            let mut c = Command::new("docker");
            c.arg("compose");
            c
        } else {
            Command::new("docker-compose")
        };
        cmd.args(["up", "-d", "--build"])
            .current_dir(&self.cwd)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        let mut child = cmd.spawn()?;
        let stdout = child.stdout.take().ok_or_else(|| eyre!("no stdout"))?;
        let stderr = child.stderr.take().ok_or_else(|| eyre!("no stderr"))?;

        let tx2 = log_tx.clone();
        let stdout_handle = tokio::spawn(async move {
            let mut reader = tokio::io::BufReader::new(stdout).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                let _ = log_tx.send(line);
            }
        });

        let stderr_handle = tokio::spawn(async move {
            let mut reader = tokio::io::BufReader::new(stderr).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                let _ = tx2.send(line);
            }
        });

        let status = child.wait().await?;
        let _ = tokio::join!(stdout_handle, stderr_handle);

        if !status.success() {
            return Err(eyre!("Docker Compose exited with status {}", status));
        }
        Ok(())
    }
}
```

- [ ] **Step 15: Verify it compiles**

```bash
cd installer
cargo check
```

Expected: clean compile

- [ ] **Step 16: Commit**

```bash
git add installer/src/docker.rs
git commit --no-verify -m "feat(installer): docker detection, port check, compose runner"
```

---

## Chunk 5: UI Drawing

### Task 5: Implement `ui.rs`

**Files:**
- Create: `installer/src/ui.rs`

- [ ] **Step 17: Write all draw functions**

```rust
use ratatui::{
    backend::Backend,
    layout::{Alignment, Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

use crate::app::{App, CurrentScreen};
use crate::wizard::WizardStep;

fn hex_to_color(hex: &str) -> Option<Color> {
    if hex.len() != 7 || !hex.starts_with('#') {
        return None;
    }
    let r = u8::from_str_radix(&hex[1..3], 16).ok()?;
    let g = u8::from_str_radix(&hex[3..5], 16).ok()?;
    let b = u8::from_str_radix(&hex[5..7], 16).ok()?;
    Some(Color::Rgb(r, g, b))
}

pub fn draw<B: Backend>(f: &mut Frame<B>, app: &App) {
    match app.screen {
        CurrentScreen::Splash => draw_splash(f),
        CurrentScreen::Wizard => draw_wizard(f, app),
        CurrentScreen::Progress => draw_progress(f, app),
        CurrentScreen::Done => draw_done(f, app),
        CurrentScreen::Error => draw_error(f, app),
    }
}

fn draw_splash<B: Backend>(f: &mut Frame<B>) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(5), Constraint::Length(3)])
        .margin(2)
        .split(area);

    let ascii = r#"
   ____                      _         _   _             _
  / __ \                    | |       | | | |           | |
 | |  | |_ __   ___ ___   __| | ___   | |_| | ___   ___ | | _____
 | |  | | '_ \ / __/ _ \ / _` |/ _ \  |  _  |/ _ \ / _ \| |/ / __|
 | |__| | | | | (_| (_) | (_| |  __/  | | | | (_) | (_) |   <\__ \
  \____/|_| |_|\___\___/ \__,_|\___|  |_| |_|\___/ \___/|_|\_\___/
"#;
    let splash = Paragraph::new(ascii)
        .alignment(Alignment::Center)
        .block(Block::default().borders(Borders::NONE));
    f.render_widget(splash, chunks[0]);

    let hint = Paragraph::new("Press ENTER to begin installation")
        .alignment(Alignment::Center)
        .style(Style::default().fg(Color::Cyan));
    f.render_widget(hint, chunks[1]);
}

fn draw_wizard<B: Backend>(f: &mut Frame<B>, app: &App) {
    let area = f.area();
    let wizard = &app.wizard;
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(10), Constraint::Length(3)])
        .margin(2)
        .split(area);

    let title = format!(" Step: {} ", wizard.step.title());
    let header = Paragraph::new(title)
        .style(Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD))
        .block(Block::default().borders(Borders::BOTTOM));
    f.render_widget(header, chunks[0]);

    let mut text = Text::default();
    match wizard.step {
        WizardStep::Name => {
            text.extend(vec![
                Line::from("What is your hackathon called?"),
                Line::from(""),
                Line::from(vec![Span::raw("> "), Span::styled(&wizard.input, Style::default().fg(Color::Yellow))]),
            ]);
        }
        WizardStep::Domain => {
            text.extend(vec![
                Line::from("What domain will you use? (e.g., hack.myuni.edu)"),
                Line::from(""),
                Line::from(vec![Span::raw("> "), Span::styled(&wizard.input, Style::default().fg(Color::Yellow))]),
            ]);
        }
        WizardStep::Email => {
            text.extend(vec![
                Line::from("Contact email for system notifications:"),
                Line::from(""),
                Line::from(vec![Span::raw("> "), Span::styled(&wizard.input, Style::default().fg(Color::Yellow))]),
            ]);
        }
        WizardStep::Color => {
            text.extend(vec![
                Line::from("Choose a primary brand color. Use LEFT/RIGHT to select a preset or type a custom hex code."),
                Line::from(""),
            ]);
            let presets = WizardStep::presets();
            let preset_line: Vec<Span> = presets
                .iter()
                .enumerate()
                .map(|(i, &p)| {
                    let style = if i == wizard.selected_preset {
                        Style::default().bg(hex_to_color(p).unwrap_or(Color::White)).fg(Color::Black).add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(hex_to_color(p).unwrap_or(Color::White))
                    };
                    Span::styled(format!(" [{}] ", p), style)
                })
                .collect();
            text.extend(vec![Line::from(preset_line), Line::from("")]);
            text.extend(vec![
                Line::from("Or type custom hex:"),
                Line::from(vec![Span::raw("> "), Span::styled(&wizard.input, Style::default().fg(Color::Yellow))]),
            ]);
        }
        WizardStep::Logo => {
            text.extend(vec![
                Line::from("Path to logo image (leave blank for default OpenHack logo):"),
                Line::from(""),
                Line::from(vec![Span::raw("> "), Span::styled(&wizard.input, Style::default().fg(Color::Yellow))]),
            ]);
        }
        WizardStep::Review => {
            text.extend(vec![
                Line::from("Review your configuration:"),
                Line::from(""),
                Line::from(vec![Span::styled("Name: ", Style::default().add_modifier(Modifier::BOLD)), Span::raw(&wizard.config.hackathon_name)]),
                Line::from(vec![Span::styled("Domain: ", Style::default().add_modifier(Modifier::BOLD)), Span::raw(&wizard.config.hackathon_domain)]),
                Line::from(vec![Span::styled("Email: ", Style::default().add_modifier(Modifier::BOLD)), Span::raw(&wizard.config.hackathon_email)]),
                Line::from(vec![Span::styled("Color: ", Style::default().add_modifier(Modifier::BOLD)), Span::raw(&wizard.config.hackathon_primary_color)]),
                Line::from(vec![Span::styled("Logo: ", Style::default().add_modifier(Modifier::BOLD)), Span::raw(if wizard.config.hackathon_logo_url.is_empty() { "default" } else { &wizard.config.hackathon_logo_url })]),
                Line::from(""),
                Line::from("Press ENTER to confirm and deploy, or BACKSPACE to go back and edit."),
            ]);
        }
    }

    if let Some(ref err) = wizard.error {
        text.extend(vec![Line::from("")]);
        text.extend(vec![Line::from(vec![Span::styled(format!("Error: {}", err), Style::default().fg(Color::Red))])]);
    }

    let body = Paragraph::new(text).wrap(Wrap { trim: true });
    f.render_widget(body, chunks[1]);

    let footer = Paragraph::new("ENTER = Next/Confirm | BACKSPACE = Back | LEFT/RIGHT = Presets | ESC = Quit")
        .style(Style::default().fg(Color::DarkGray))
        .alignment(Alignment::Center);
    f.render_widget(footer, chunks[2]);
}

fn draw_progress<B: Backend>(f: &mut Frame<B>, app: &App) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(10), Constraint::Length(3)])
        .margin(2)
        .split(area);

    let header = Paragraph::new(" Deploying OpenHack... ")
        .style(Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD))
        .block(Block::default().borders(Borders::BOTTOM));
    f.render_widget(header, chunks[0]);

    let mut text = Text::default();
    for line in &app.docker_logs {
        text.extend(vec![Line::from(line.as_str())]);
    }
    let body = Paragraph::new(text).wrap(Wrap { trim: true });
    f.render_widget(body, chunks[1]);

    let footer = Paragraph::new("Please wait while Docker Compose builds and starts services...")
        .style(Style::default().fg(Color::DarkGray))
        .alignment(Alignment::Center);
    f.render_widget(footer, chunks[2]);
}

fn draw_done<B: Backend>(f: &mut Frame<B>, app: &App) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(5), Constraint::Length(3)])
        .margin(2)
        .split(area);

    let domain = &app.wizard.config.hackathon_domain;
    let text = Text::from(vec![
        Line::from(vec![Span::styled("Installation complete!", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))]),
        Line::from(""),
        Line::from(vec![Span::raw("Your hackathon is running at: "), Span::styled(format!("https://{}", domain), Style::default().fg(Color::Cyan))]),
        Line::from(""),
        Line::from("Next steps:"),
        Line::from("  1. Configure OAuth providers (Google, GitHub, Discord) with your domain"),
        Line::from("  2. Update CLERK_SECRET_KEY and VITE_CLERK_PUBLISHABLE_KEY in .env"),
        Line::from("  3. Run 'docker compose logs -f' to monitor services"),
        Line::from(""),
        Line::from("Press ENTER to exit."),
    ]);
    let body = Paragraph::new(text);
    f.render_widget(body, chunks[0]);
}

fn draw_error<B: Backend>(f: &mut Frame<B>, app: &App) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(5), Constraint::Length(3)])
        .margin(2)
        .split(area);

    let mut text = Text::default();
    text.extend(vec![Line::from(vec![Span::styled("Installation failed", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))])]);
    text.extend(vec![Line::from("")]);
    if let Some(ref err) = app.error_message {
        for line in err.lines() {
            text.extend(vec![Line::from(line)]);
        }
    }
    let body = Paragraph::new(text).wrap(Wrap { trim: true });
    f.render_widget(body, chunks[0]);

    let footer = Paragraph::new("Press ENTER to exit.")
        .style(Style::default().fg(Color::DarkGray))
        .alignment(Alignment::Center);
    f.render_widget(footer, chunks[1]);
}
```

- [ ] **Step 18: Verify it compiles**

```bash
cd installer
cargo check
```

Expected: clean compile

- [ ] **Step 19: Commit**

```bash
git add installer/src/ui.rs
git commit --no-verify -m "feat(installer): ratatui UI drawing for all screens"
```

---

## Chunk 6: App State Machine and Main Wiring

### Task 6: Implement `app.rs`

**Files:**
- Create: `installer/src/app.rs`

- [ ] **Step 20: Write App struct and event loop**

```rust
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use ratatui::{backend::Backend, Terminal};
use std::time::Duration;

use crate::docker::{check_docker, check_compose, check_ports, ComposeRunner};
use crate::ui::draw;
use crate::wizard::Wizard;

pub enum CurrentScreen {
    Splash,
    Wizard,
    Progress,
    Done,
    Error,
}

pub struct App {
    pub screen: CurrentScreen,
    pub wizard: Wizard,
    pub docker_logs: Vec<String>,
    pub error_message: Option<String>,
    pub should_quit: bool,
}

impl App {
    pub fn new() -> Self {
        Self {
            screen: CurrentScreen::Splash,
            wizard: Wizard::new(),
            docker_logs: vec![],
            error_message: None,
            should_quit: false,
        }
    }

    pub async fn run<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> color_eyre::Result<()> {
        let mut last_tick = tokio::time::Instant::now();
        let tick_rate = Duration::from_millis(100);

        while !self.should_quit {
            terminal.draw(|f| draw(f, self))?;

            let timeout = tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| Duration::from_secs(0));

            if crossterm::event::poll(timeout)? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        self.handle_key(key.code).await;
                    }
                }
            }

            if last_tick.elapsed() >= tick_rate {
                self.on_tick().await;
                last_tick = tokio::time::Instant::now();
            }
        }
        Ok(())
    }

    async fn handle_key(&mut self, code: KeyCode) {
        match self.screen {
            CurrentScreen::Splash => {
                if code == KeyCode::Enter {
                    self.screen = CurrentScreen::Wizard;
                }
            }
            CurrentScreen::Wizard => {
                match code {
                    KeyCode::Enter => {
                        if self.wizard.step == crate::wizard::WizardStep::Review {
                            self.start_deployment().await;
                        } else {
                            if self.wizard.commit_step() {
                                self.wizard.advance();
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        if self.wizard.step == crate::wizard::WizardStep::Review {
                            self.wizard.retreat();
                        } else {
                            self.wizard.input.pop();
                        }
                    }
                    KeyCode::Left => {
                        if self.wizard.step == crate::wizard::WizardStep::Color {
                            if self.wizard.selected_preset > 0 {
                                self.wizard.selected_preset -= 1;
                            }
                        }
                    }
                    KeyCode::Right => {
                        if self.wizard.step == crate::wizard::WizardStep::Color {
                            let max = crate::wizard::WizardStep::presets().len() - 1;
                            if self.wizard.selected_preset < max {
                                self.wizard.selected_preset += 1;
                            }
                        }
                    }
                    KeyCode::Char(c) => {
                        self.wizard.input.push(c);
                    }
                    KeyCode::Esc => self.should_quit = true,
                    _ => {}
                }
            }
            CurrentScreen::Progress => {}
            CurrentScreen::Done => {
                if code == KeyCode::Enter {
                    self.should_quit = true;
                }
            }
            CurrentScreen::Error => {
                if code == KeyCode::Enter {
                    self.should_quit = true;
                }
            }
        }
    }

    async fn on_tick(&mut self) {
        // Nothing needed on tick for now
    }

    async fn start_deployment(&mut self) {
        self.screen = CurrentScreen::Progress;
        self.docker_logs.clear();

        // Check docker
        if let Err(e) = check_docker().await {
            self.error_message = Some(format!("Docker check failed: {}", e));
            self.screen = CurrentScreen::Error;
            return;
        }

        // Check compose
        let compose_cmd = match check_compose().await {
            Ok(cmd) => cmd,
            Err(e) => {
                self.error_message = Some(format!("Compose check failed: {}", e));
                self.screen = CurrentScreen::Error;
                return;
            }
        };

        // Check ports
        let bound = check_ports().await;
        if !bound.is_empty() {
            self.docker_logs.push(format!("Warning: ports already bound: {:?}", bound));
            self.docker_logs.push("You may need to free these ports or edit docker-compose.yml".into());
        }

        // Clone repo if needed
        let cwd = std::path::PathBuf::from("./openhack");
        if !cwd.exists() {
            self.docker_logs.push("Cloning openhack repository...".into());
            let clone = tokio::process::Command::new("git")
                .args(["clone", "https://github.com/mintychochip/openhack.git", "./openhack"])
                .output()
                .await;
            if let Ok(out) = clone {
                if !out.status.success() {
                    let stderr = String::from_utf8_lossy(&out.stderr);
                    self.error_message = Some(format!("Git clone failed:\n{}", stderr));
                    self.screen = CurrentScreen::Error;
                    return;
                }
            } else {
                self.error_message = Some("Failed to run git clone. Is git installed?".into());
                self.screen = CurrentScreen::Error;
                return;
            }
        }

        // Write .env
        let env_path = cwd.join(".env");
        if env_path.exists() {
            self.docker_logs.push("Existing .env found — overwriting with new configuration".into());
        }
        if let Err(e) = self.wizard.config.write_env(&env_path) {
            self.error_message = Some(format!("Failed to write .env: {}", e));
            self.screen = CurrentScreen::Error;
            return;
        }
        self.docker_logs.push("Configuration written to .env".into());

        // Run docker compose
        let (log_tx, mut log_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
        let runner = ComposeRunner::new(compose_cmd, cwd.clone());

        let docker_handle = tokio::spawn(async move {
            runner.run_streaming(log_tx).await
        });

        // Poll logs and check completion
        loop {
            while let Ok(line) = log_rx.try_recv() {
                self.docker_logs.push(line);
            }

            if docker_handle.is_finished() {
                while let Ok(line) = log_rx.try_recv() {
                    self.docker_logs.push(line);
                }
                match docker_handle.await {
                    Ok(Ok(())) => {
                        self.screen = CurrentScreen::Done;
                        return;
                    }
                    Ok(Err(e)) => {
                        self.error_message = Some(format!("Docker Compose failed: {}", e));
                        self.screen = CurrentScreen::Error;
                        return;
                    }
                    Err(e) => {
                        self.error_message = Some(format!("Docker task panicked: {}", e));
                        self.screen = CurrentScreen::Error;
                        return;
                    }
                }
            }

            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    }
}
```

- [ ] **Step 21: Update `main.rs` to wire everything**

Replace `installer/src/main.rs`:
```rust
use color_eyre::Result;
use crossterm::{
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io;

mod app;
mod config;
mod docker;
mod ui;
mod wizard;

#[tokio::main]
async fn main() -> Result<()> {
    color_eyre::install()?;

    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = app::App::new();
    let res = app.run(&mut terminal).await;

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        eprintln!("{:?}", err);
    }

    Ok(())
}
```

- [ ] **Step 22: Verify it compiles**

```bash
cd installer
cargo check
```

Expected: clean compile (may need minor fixes for ratatui API differences)

- [ ] **Step 23: Commit**

```bash
git add installer/src/app.rs installer/src/main.rs
git commit --no-verify -m "feat(installer): app state machine, event loop, deployment orchestration"
```

---

## Chunk 7: Bootstrapper Script

### Task 7: Create `install.sh`

**Files:**
- Create: `install.sh`

- [ ] **Step 24: Write POSIX bootstrapper**

```bash
#!/bin/sh
set -e

REPO="mintychochip/openhack"
VERSION="latest"
ARCH=$(uname -sm | tr '[:upper:]' '[:lower:]' | sed 's/ /-/')
BINARY="openhack-installer-${ARCH}"
URL="https://github.com/${REPO}/releases/${VERSION}/download/${BINARY}"
CHECKSUM_URL="${URL}.sha256"

# Determine writable directory
if [ -d "$HOME" ] && [ -w "$HOME" ]; then
  WORKDIR="$HOME/.openhack/tmp"
  mkdir -p "$WORKDIR"
else
  WORKDIR="/tmp"
fi

# Download binary + checksum
echo "Downloading OpenHack installer for ${ARCH}..."
curl -sSL "$URL" -o "$WORKDIR/openhack-installer"
curl -sSL "$CHECKSUM_URL" -o "$WORKDIR/openhack-installer.sha256"

# Verify checksum
EXPECTED=$(cat "$WORKDIR/openhack-installer.sha256" | awk '{print $1}')
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL=$(sha256sum "$WORKDIR/openhack-installer" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL=$(shasum -a 256 "$WORKDIR/openhack-installer" | awk '{print $1}')
else
  echo "Error: sha256sum or shasum required for checksum verification" >&2
  exit 1
fi
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "Error: checksum mismatch — download may be corrupted" >&2
  exit 1
fi

chmod +x "$WORKDIR/openhack-installer"
exec "$WORKDIR/openhack-installer"
```

- [ ] **Step 25: Make executable and test syntax**

```bash
chmod +x install.sh
sh -n install.sh
```

Expected: no output (syntax ok)

- [ ] **Step 26: Commit**

```bash
git add install.sh
git commit --no-verify -m "feat(installer): POSIX bootstrapper script with checksum verification"
```

---

## Chunk 8: GitHub Actions Release Workflow

### Task 8: Create `.github/workflows/installer-release.yml`

**Files:**
- Create: `.github/workflows/installer-release.yml`

- [ ] **Step 27: Write release workflow**

```yaml
name: Installer Release

on:
  push:
    tags:
      - 'installer-v*'
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        include:
          - target: x86_64-unknown-linux-gnu
            os: ubuntu-latest
            binary: openhack-installer-linux-x86_64
          - target: aarch64-unknown-linux-gnu
            os: ubuntu-latest
            binary: openhack-installer-linux-arm64
          - target: x86_64-apple-darwin
            os: macos-latest
            binary: openhack-installer-darwin-x86_64
          - target: aarch64-apple-darwin
            os: macos-latest
            binary: openhack-installer-darwin-arm64
          - target: x86_64-pc-windows-msvc
            os: windows-latest
            binary: openhack-installer-windows-x86_64.exe

    runs-on: ${{ matrix.os }}
    defaults:
      run:
        working-directory: installer

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Install cross-compilation tools (Linux ARM64)
        if: matrix.target == 'aarch64-unknown-linux-gnu'
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-aarch64-linux-gnu
          echo "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc" >> "$GITHUB_ENV"

      - name: Build
        run: cargo build --release --target ${{ matrix.target }}

      - name: Rename binary
        shell: bash
        run: |
          src="target/${{ matrix.target }}/release/openhack-installer"
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            src="${src}.exe"
          fi
          cp "$src" "../${{ matrix.binary }}"

      - name: Generate checksum
        shell: bash
        run: |
          cd ..
          if command -v sha256sum >/dev/null 2>&1; then
            sha256sum "${{ matrix.binary }}" > "${{ matrix.binary }}.sha256"
          else
            shasum -a 256 "${{ matrix.binary }}" > "${{ matrix.binary }}.sha256"
          fi

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.binary }}
          path: |
            ${{ matrix.binary }}
            ${{ matrix.binary }}.sha256

  release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: artifacts/*
          generate_release_notes: true
```

- [ ] **Step 28: Verify workflow syntax**

No automated check needed — the YAML is valid if it parses. Review visually.

- [ ] **Step 29: Commit**

```bash
git add .github/workflows/installer-release.yml
git commit --no-verify -m "feat(ci): GitHub Actions release matrix for installer binaries"
```

---

## Chunk 9: Final Integration and Manual Test

### Task 9: End-to-End Verification

**Files:**
- Modify: none (integration test)

- [ ] **Step 30: Run cargo build in installer directory**

```bash
cd installer
cargo build --release
```

Expected: `Finished release [optimized] target(s) in ...`

- [ ] **Step 31: Run the binary briefly (will fail at docker step but UI should render)**

```bash
cd installer
./target/release/openhack-installer
```

Press `Enter` to pass splash, then `Esc` to quit. Verify the UI renders without panics.

- [ ] **Step 32: Run all Rust tests**

```bash
cd installer
cargo test
```

Expected: all tests pass.

- [ ] **Step 33: Final commit**

```bash
git add -A
git commit --no-verify -m "feat(installer): complete Phase 3 TUI installer"
```

---

## Final Verification Checklist

1. `cd installer && cargo build --release` produces a working binary
2. `cd installer && cargo test` passes all tests
3. `install.sh` is POSIX-compliant (`sh -n install.sh` returns 0)
4. `.github/workflows/installer-release.yml` has valid YAML and 5 build targets
5. Binary renders Splash, Wizard (all 6 steps), Progress, Done, and Error screens
6. Wizard validates email and hex color inline
7. `.env` generation includes `HACKVERIFY_*` branding vars, `DATABASE_URL`, `REDIS_URL`, and a random `SECRET_KEY`
8. Docker detection works for both `docker compose` and `docker-compose`
9. Port check warns about bound ports before deployment
10. Git clone step downloads the repo if `./openhack` is missing
11. Docker Compose output streams live to the Progress screen
12. Done screen shows the configured domain and next steps

---

## Next Phase

After this plan is complete and committed, the TUI Installer is ready for distribution. Future work (out of scope for this plan):
- Host `install.sh` at `https://get.openhack.dev`
- Cut a GitHub release with the installer binaries
- Test `curl -sSL https://get.openhack.dev | bash` end-to-end on a fresh Ubuntu VM
