use ratatui::{
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

pub fn draw(f: &mut Frame, app: &App) {
    match app.screen {
        CurrentScreen::Splash => draw_splash(f),
        CurrentScreen::Wizard => draw_wizard(f, app),
        CurrentScreen::Progress => draw_progress(f, app),
        CurrentScreen::Done => draw_done(f, app),
        CurrentScreen::Error => draw_error(f, app),
    }
}

fn draw_splash(f: &mut Frame) {
    let area = f.size();
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

fn draw_wizard(f: &mut Frame, app: &App) {
    let area = f.size();
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

fn draw_progress(f: &mut Frame, app: &App) {
    let area = f.size();
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

fn draw_done(f: &mut Frame, app: &App) {
    let area = f.size();
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

fn draw_error(f: &mut Frame, app: &App) {
    let area = f.size();
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
