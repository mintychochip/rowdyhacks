use std::collections::HashMap;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct EnvFile {
    pub entries: Vec<(String, String)>,
    pub path: PathBuf,
}

impl EnvFile {
    pub fn load(path: &Path) -> std::io::Result<Self> {
        let mut entries = Vec::new();
        if path.exists() {
            let contents = std::fs::read_to_string(path)?;
            for line in contents.lines() {
                let trimmed = line.trim();
                if trimmed.is_empty() || trimmed.starts_with('#') {
                    continue;
                }
                if let Some(pos) = trimmed.find('=') {
                    let key = trimmed[..pos].trim().to_string();
                    let value = trimmed[pos + 1..].trim().to_string();
                    entries.push((key, value));
                }
            }
        }
        Ok(Self {
            entries,
            path: path.to_path_buf(),
        })
    }

    pub fn save(&self) -> std::io::Result<()> {
        let mut contents = String::new();
        for (key, value) in &self.entries {
            contents.push_str(&format!("{}={}\n", key, value));
        }
        std::fs::write(&self.path, contents)
    }

    pub fn set(&mut self, key: &str, value: &str) {
        if let Some(idx) = self.entries.iter().position(|(k, _)| k == key) {
            self.entries[idx].1 = value.to_string();
        } else {
            self.entries.push((key.to_string(), value.to_string()));
        }
    }

    pub fn from_map(path: &Path, map: HashMap<String, String>) -> Self {
        let entries: Vec<(String, String)> = map.into_iter().collect();
        Self {
            entries,
            path: path.to_path_buf(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_load_env() {
        let mut tmp = tempfile::NamedTempFile::new().unwrap();
        write!(
            tmp,
            "FOO=bar\n# comment\nBAZ=qux\n\nEMPTY=\n"
        )
        .unwrap();
        let env = EnvFile::load(tmp.path()).unwrap();
        assert_eq!(env.entries.len(), 3);
        assert_eq!(env.entries[0], ("FOO".into(), "bar".into()));
        assert_eq!(env.entries[1], ("BAZ".into(), "qux".into()));
        assert_eq!(env.entries[2], ("EMPTY".into(), "".into()));
    }

    #[test]
    fn test_save_env_roundtrip() {
        let tmp = tempfile::NamedTempFile::new().unwrap();
        let mut env = EnvFile::load(tmp.path()).unwrap();
        env.set("KEY1", "value1");
        env.set("KEY2", "value2");
        env.save().unwrap();

        let loaded = EnvFile::load(tmp.path()).unwrap();
        assert_eq!(loaded.entries.len(), 2);
        assert_eq!(loaded.entries[0], ("KEY1".into(), "value1".into()));
        assert_eq!(loaded.entries[1], ("KEY2".into(), "value2".into()));
    }

    #[test]
    fn test_set_overwrite() {
        let tmp = tempfile::NamedTempFile::new().unwrap();
        let mut env = EnvFile::load(tmp.path()).unwrap();
        env.set("X", "first");
        env.set("X", "second");
        assert_eq!(env.entries.len(), 1);
        assert_eq!(env.entries[0].1, "second");
    }

    #[test]
    fn test_set_new_key() {
        let tmp = tempfile::NamedTempFile::new().unwrap();
        let mut env = EnvFile::load(tmp.path()).unwrap();
        env.set("A", "1");
        env.set("B", "2");
        assert_eq!(env.entries.len(), 2);
    }
}
