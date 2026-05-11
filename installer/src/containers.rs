use color_eyre::Result;
use std::path::PathBuf;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::sync::mpsc::UnboundedSender;

#[derive(Debug, Clone, Default)]
pub struct ContainerInfo {
    pub name: String,
    pub image: String,
    pub status: String,
    pub cpu_perc: String,
    pub mem_usage: String,
    pub mem_perc: String,
}

pub async fn list_containers() -> Result<Vec<ContainerInfo>> {
    let mut containers = Vec::new();

    let ps_output = Command::new("docker")
        .args(["ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}"])
        .output()
        .await?;

    let ps_str = String::from_utf8_lossy(&ps_output.stdout);
    for line in ps_str.lines() {
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() >= 3 {
            containers.push(ContainerInfo {
                name: parts[0].to_string(),
                image: parts[1].to_string(),
                status: parts[2].to_string(),
                ..Default::default()
            });
        }
    }

    let stats_output = Command::new("docker")
        .args([
            "stats",
            "--no-stream",
            "--format",
            "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}",
        ])
        .output()
        .await?;

    let stats_str = String::from_utf8_lossy(&stats_output.stdout);
    for line in stats_str.lines() {
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() >= 4 {
            let name = parts[0];
            if let Some(c) = containers.iter_mut().find(|c| c.name == name) {
                c.cpu_perc = parts[1].to_string();
                c.mem_usage = parts[2].to_string();
                c.mem_perc = parts[3].to_string();
            }
        }
    }

    Ok(containers)
}

pub async fn container_logs(
    name: &str,
    lines: usize,
    log_tx: UnboundedSender<String>,
) -> Result<()> {
    let mut child = Command::new("docker")
        .args(["logs", "--tail", &lines.to_string(), "-f", name])
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().expect("stdout pipe");
    let stderr = child.stderr.take().expect("stderr pipe");

    let tx_out = log_tx.clone();
    let handle_out = tokio::spawn(async move {
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_out.send(line);
        }
    });

    let tx_err = log_tx;
    let handle_err = tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_err.send(line);
        }
    });

    let _ = tokio::join!(handle_out, handle_err);
    Ok(())
}

pub async fn compose_up(log_tx: UnboundedSender<String>, cwd: PathBuf) -> Result<()> {
    let mut child = Command::new("docker")
        .args(["compose", "up", "-d", "--build"])
        .current_dir(&cwd)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().expect("stdout pipe");
    let stderr = child.stderr.take().expect("stderr pipe");

    let tx_out = log_tx.clone();
    let handle_out = tokio::spawn(async move {
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_out.send(line);
        }
    });

    let tx_err = log_tx;
    let handle_err = tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_err.send(line);
        }
    });

    let _ = tokio::join!(handle_out, handle_err);
    Ok(())
}

pub async fn compose_down(log_tx: UnboundedSender<String>, cwd: PathBuf) -> Result<()> {
    let mut child = Command::new("docker")
        .args(["compose", "down"])
        .current_dir(&cwd)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().expect("stdout pipe");
    let stderr = child.stderr.take().expect("stderr pipe");

    let tx_out = log_tx.clone();
    let handle_out = tokio::spawn(async move {
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_out.send(line);
        }
    });

    let tx_err = log_tx;
    let handle_err = tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_err.send(line);
        }
    });

    let _ = tokio::join!(handle_out, handle_err);
    Ok(())
}

pub async fn compose_restart(
    log_tx: UnboundedSender<String>,
    cwd: PathBuf,
    service: Option<&str>,
) -> Result<()> {
    let mut args = vec!["compose", "restart"];
    if let Some(s) = service {
        args.push(s);
    }

    let mut child = Command::new("docker")
        .args(&args)
        .current_dir(&cwd)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().expect("stdout pipe");
    let stderr = child.stderr.take().expect("stderr pipe");

    let tx_out = log_tx.clone();
    let handle_out = tokio::spawn(async move {
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_out.send(line);
        }
    });

    let tx_err = log_tx;
    let handle_err = tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = tx_err.send(line);
        }
    });

    let _ = tokio::join!(handle_out, handle_err);
    Ok(())
}
