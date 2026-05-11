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
        &[
            "#2563eb",
            "#7c3aed",
            "#059669",
            "#dc2626",
            "#ea580c",
            "#0891b2",
        ]
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
    pub visible_steps: Vec<WizardStep>,
    pub current_step_index: usize,
    pub config: InstallConfig,
    pub input: String,
    pub error: Option<String>,
    pub selected_preset: usize,
}

impl Wizard {
    pub fn new() -> Self {
        Self::new_full_setup()
    }

    pub fn new_full_setup() -> Self {
        Self {
            visible_steps: vec![
                WizardStep::Name,
                WizardStep::Domain,
                WizardStep::Email,
                WizardStep::Color,
                WizardStep::Logo,
                WizardStep::Review,
            ],
            current_step_index: 0,
            config: InstallConfig::default(),
            input: String::new(),
            error: None,
            selected_preset: 0,
        }
    }

    #[allow(dead_code)]
    pub fn new_quick_start() -> Self {
        Self {
            visible_steps: vec![
                WizardStep::Name,
                WizardStep::Domain,
                WizardStep::Email,
                WizardStep::Color,
                WizardStep::Review,
            ],
            current_step_index: 0,
            config: InstallConfig::default(),
            input: String::new(),
            error: None,
            selected_preset: 0,
        }
    }

    pub fn step(&self) -> WizardStep {
        self.visible_steps[self.current_step_index]
    }

    pub fn commit_step(&mut self) -> bool {
        self.error = None;
        match self.step() {
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
        if self.current_step_index + 1 < self.visible_steps.len() {
            self.current_step_index += 1;
        }
    }

    pub fn retreat(&mut self) {
        if self.current_step_index > 0 {
            self.current_step_index -= 1;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wizard_flow() {
        let mut w = Wizard::new();
        assert_eq!(w.step(), WizardStep::Name);
        w.input = "TestHack".into();
        assert!(w.commit_step());
        w.advance();
        assert_eq!(w.step(), WizardStep::Domain);
    }

    #[test]
    fn test_email_validation_blocks() {
        let mut w = Wizard::new();
        w.visible_steps = vec![WizardStep::Email];
        w.current_step_index = 0;
        w.input = "bad".into();
        assert!(!w.commit_step());
        assert!(w.error.is_some());
    }

    #[test]
    fn test_quick_start_skips_logo() {
        let w = Wizard::new_quick_start();
        let has_logo = w.visible_steps.iter().any(|s| *s == WizardStep::Logo);
        assert!(!has_logo);
    }
}
