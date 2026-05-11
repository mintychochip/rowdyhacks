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
