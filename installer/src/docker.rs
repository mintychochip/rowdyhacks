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
