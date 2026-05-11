use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct InstallConfig {
    pub hackathon_name: String,
    pub hackathon_domain: String,
    pub hackathon_email: String,
    pub hackathon_primary_color: String,
    pub hackathon_logo_url: String,
    pub discord_bot_token: String,
    pub discord_channel_id: String,
    pub discord_webhook_url: String,
    pub discord_client_id: String,
    pub discord_client_secret: String,
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
        const CHARSET: &[u8] =
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";
        let mut rng = rand::thread_rng();
        (0..48)
            .map(|_| CHARSET[rng.gen_range(0..CHARSET.len())] as char)
            .collect()
    }

    pub fn write_env(&self, path: &Path) -> std::io::Result<()> {
        let mut contents = String::new();
        contents.push_str(&format!(
            "HACKVERIFY_HACKATHON_NAME={}\n",
            self.hackathon_name
        ));
        contents.push_str(&format!(
            "HACKVERIFY_HACKATHON_TAGLINE=The open-source hackathon framework\n"
        ));
        contents.push_str(&format!(
            "HACKVERIFY_HACKATHON_DOMAIN={}\n",
            self.hackathon_domain
        ));
        contents.push_str(&format!(
            "HACKVERIFY_HACKATHON_EMAIL={}\n",
            self.hackathon_email
        ));
        contents.push_str(&format!(
            "HACKVERIFY_HACKATHON_PRIMARY_COLOR={}\n",
            self.hackathon_primary_color
        ));
        if !self.hackathon_logo_url.is_empty() {
            contents.push_str(&format!(
                "HACKVERIFY_HACKATHON_LOGO_URL={}\n",
                self.hackathon_logo_url
            ));
        }
        if !self.discord_bot_token.is_empty() {
            contents.push_str(&format!("DISCORD_BOT_TOKEN={}\n", self.discord_bot_token));
        }
        if !self.discord_channel_id.is_empty() {
            contents.push_str(&format!("DISCORD_CHANNEL_ID={}\n", self.discord_channel_id));
        }
        if !self.discord_webhook_url.is_empty() {
            contents.push_str(&format!(
                "DISCORD_WEBHOOK_URL={}\n",
                self.discord_webhook_url
            ));
        }
        if !self.discord_client_id.is_empty() {
            contents.push_str(&format!("DISCORD_CLIENT_ID={}\n", self.discord_client_id));
        }
        if !self.discord_client_secret.is_empty() {
            contents.push_str(&format!(
                "DISCORD_CLIENT_SECRET={}\n",
                self.discord_client_secret
            ));
        }
        contents.push_str(&format!("HACKVERIFY_SECRET_KEY={}\n", Self::generate_secret_key()));
        contents.push_str("DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/hackverify\n");
        contents.push_str("REDIS_URL=redis://redis:6379/0\n");
        contents.push_str("HACKVERIFY_BASE_URL=https://\n");
        std::fs::write(path, contents)
    }

    pub fn read_env(path: &Path) -> std::io::Result<Self> {
        let mut config = Self::default();
        if !path.exists() {
            return Ok(config);
        }
        let contents = std::fs::read_to_string(path)?;
        let mut map = HashMap::new();
        for line in contents.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            if let Some(pos) = trimmed.find('=') {
                let key = trimmed[..pos].trim().to_string();
                let value = trimmed[pos + 1..].trim().to_string();
                map.insert(key, value);
            }
        }

        if let Some(v) = map.get("HACKVERIFY_HACKATHON_NAME") {
            config.hackathon_name = v.clone();
        }
        if let Some(v) = map.get("HACKVERIFY_HACKATHON_DOMAIN") {
            config.hackathon_domain = v.clone();
        }
        if let Some(v) = map.get("HACKVERIFY_HACKATHON_EMAIL") {
            config.hackathon_email = v.clone();
        }
        if let Some(v) = map.get("HACKVERIFY_HACKATHON_PRIMARY_COLOR") {
            config.hackathon_primary_color = v.clone();
        }
        if let Some(v) = map.get("HACKVERIFY_HACKATHON_LOGO_URL") {
            config.hackathon_logo_url = v.clone();
        }
        if let Some(v) = map.get("DISCORD_BOT_TOKEN") {
            config.discord_bot_token = v.clone();
        }
        if let Some(v) = map.get("DISCORD_CHANNEL_ID") {
            config.discord_channel_id = v.clone();
        }
        if let Some(v) = map.get("DISCORD_WEBHOOK_URL") {
            config.discord_webhook_url = v.clone();
        }
        if let Some(v) = map.get("DISCORD_CLIENT_ID") {
            config.discord_client_id = v.clone();
        }
        if let Some(v) = map.get("DISCORD_CLIENT_SECRET") {
            config.discord_client_secret = v.clone();
        }

        Ok(config)
    }
}

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

    #[test]
    fn test_read_write_env_roundtrip() {
        use tempfile::NamedTempFile;
        let tmp = NamedTempFile::new().unwrap();
        let config = InstallConfig {
            hackathon_name: "TestHack".into(),
            hackathon_domain: "test.example.com".into(),
            hackathon_email: "test@example.com".into(),
            hackathon_primary_color: "#2563eb".into(),
            hackathon_logo_url: "".into(),
            discord_bot_token: "bot_token_123".into(),
            discord_channel_id: "123456".into(),
            discord_webhook_url: "".into(),
            discord_client_id: "".into(),
            discord_client_secret: "".into(),
        };
        config.write_env(tmp.path()).unwrap();
        let loaded = InstallConfig::read_env(tmp.path()).unwrap();
        assert_eq!(loaded.hackathon_name, "TestHack");
        assert_eq!(loaded.hackathon_domain, "test.example.com");
        assert_eq!(loaded.hackathon_email, "test@example.com");
        assert_eq!(loaded.hackathon_primary_color, "#2563eb");
        assert_eq!(loaded.discord_bot_token, "bot_token_123");
        assert_eq!(loaded.discord_channel_id, "123456");
    }
}
