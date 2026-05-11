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
