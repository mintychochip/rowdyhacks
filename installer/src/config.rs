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
