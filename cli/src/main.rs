//! Worldview CLI - Tools for working with Worldview format files
//!
//! Commands:
//!   validate  - Validate .wvf files for syntax errors
//!   add       - Add facts to a Worldview file using an AI agent

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;

mod add;
mod validate;

/// CLI for working with Worldview format files
#[derive(Parser, Debug)]
#[command(name = "worldview")]
#[command(about = "Tools for working with Worldview format files")]
#[command(version)]
#[command(after_long_help = include_str!("../../system.md"))]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Validate Worldview files for syntax errors (also runs automatically on `add`)
    Validate {
        /// Files to validate
        #[arg(required_unless_present = "stdin")]
        files: Vec<PathBuf>,

        /// Read from stdin instead of files
        #[arg(long)]
        stdin: bool,
    },

    /// Add a fact to a Worldview file using an AI agent
    Add {
        /// The fact or statement to add
        #[arg(required = true)]
        fact: String,

        /// Path to the Worldview file to modify
        #[arg(short, long, default_value = "worldview.wvf")]
        file: PathBuf,

        /// Model to use
        #[arg(short, long, default_value = "claude-sonnet-4-20250514")]
        model: String,

        /// Enable verbose output
        #[arg(short, long)]
        verbose: bool,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Validate { files, stdin } => validate::run(files, stdin),
        Commands::Add { fact, file, model, verbose } => add::run(fact, file, model, verbose).await,
    }
}
