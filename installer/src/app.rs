use crate::wizard::Wizard;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
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
