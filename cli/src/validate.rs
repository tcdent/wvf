//! Validate subcommand - validates .wvf files for syntax errors

use anyhow::Result;
use std::io::{self, Read};
use std::path::PathBuf;

pub fn run(files: Vec<PathBuf>, stdin: bool) -> Result<()> {
    let mut all_valid = true;

    if stdin {
        // Read from stdin
        let mut content = String::new();
        io::stdin().read_to_string(&mut content)?;
        let result = worldview_validator::validate(&content);
        print!("{}", result);
        if !result.is_valid() {
            all_valid = false;
        }
    } else {
        // Validate each file
        for path in &files {
            if files.len() > 1 {
                println!("{}:", path.display());
            }

            match worldview_validator::validate_file(path) {
                Ok(result) => {
                    println!("{}", result);
                    if !result.is_valid() {
                        all_valid = false;
                    }
                }
                Err(e) => {
                    eprintln!("Error reading {}: {}", path.display(), e);
                    all_valid = false;
                }
            }

            if files.len() > 1 {
                println!();
            }
        }
    }

    if all_valid {
        Ok(())
    } else {
        std::process::exit(1);
    }
}
