//! WSL Validator CLI
//!
//! A command-line tool for validating Worldview State Language (WSL) files.

use std::env;
use std::path::Path;
use std::process::ExitCode;
use wsl_validator::{validate, validate_file};

fn print_usage(program: &str) {
    eprintln!("Usage: {} <file.wsl>", program);
    eprintln!("       {} --stdin", program);
    eprintln!();
    eprintln!("Validates a WSL (Worldview State Language) file for syntactic correctness.");
    eprintln!();
    eprintln!("Options:");
    eprintln!("  --stdin    Read from standard input instead of a file");
    eprintln!("  --help     Show this help message");
    eprintln!("  --version  Show version information");
}

fn print_version() {
    eprintln!("wsl-validate {}", env!("CARGO_PKG_VERSION"));
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    let program = &args[0];

    if args.len() < 2 {
        print_usage(program);
        return ExitCode::from(1);
    }

    let arg = &args[1];

    if arg == "--help" || arg == "-h" {
        print_usage(program);
        return ExitCode::SUCCESS;
    }

    if arg == "--version" || arg == "-V" {
        print_version();
        return ExitCode::SUCCESS;
    }

    let result = if arg == "--stdin" {
        // Read from stdin
        let mut input = String::new();
        if let Err(e) = std::io::Read::read_to_string(&mut std::io::stdin(), &mut input) {
            eprintln!("Error reading from stdin: {}", e);
            return ExitCode::from(1);
        }
        validate(&input)
    } else {
        // Read from file
        let path = Path::new(arg);

        if !path.exists() {
            eprintln!("Error: File '{}' not found", arg);
            return ExitCode::from(1);
        }

        // Check file extension
        if let Some(ext) = path.extension() {
            if ext.to_ascii_lowercase() != "wsl" {
                eprintln!("Warning: File does not have .wsl extension");
            }
        }

        match validate_file(path) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("Error reading file '{}': {}", arg, e);
                return ExitCode::from(1);
            }
        }
    };

    if result.is_valid() {
        println!("Valid WSL document");
        ExitCode::SUCCESS
    } else {
        eprintln!("Invalid WSL document ({} error(s)):", result.errors.len());
        for error in &result.errors {
            eprintln!("  {}", error);
        }
        ExitCode::from(1)
    }
}
