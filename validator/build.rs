//! Build script for worldview-validator
//! Generates token definitions from spec/tokens.yaml at compile time.

use std::env;
use std::fs;
use std::path::Path;

fn main() {
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("tokens.rs");

    // Read tokens.yaml from spec directory
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let tokens_path = Path::new(&manifest_dir)
        .parent()
        .unwrap()
        .join("spec/tokens.yaml");

    println!("cargo:rerun-if-changed={}", tokens_path.display());

    let tokens_yaml = fs::read_to_string(&tokens_path).expect("Failed to read spec/tokens.yaml");

    // Parse YAML manually (avoiding serde dependency in build script)
    let rust_code = generate_tokens_rs(&tokens_yaml);

    fs::write(&dest_path, rust_code).unwrap();
}

fn generate_tokens_rs(yaml: &str) -> String {
    let mut output = String::from("// Auto-generated from spec/tokens.yaml at compile time\n\n");

    // Parse brief_forms
    let mut brief_forms = Vec::new();
    let mut in_brief_forms = false;
    let mut current_symbol = String::new();
    let mut current_meaning = String::new();

    for line in yaml.lines() {
        let trimmed = line.trim();

        if trimmed == "brief_forms:" {
            in_brief_forms = true;
            continue;
        }

        if in_brief_forms {
            if trimmed.starts_with("- symbol:") {
                if !current_symbol.is_empty() {
                    brief_forms.push((current_symbol.clone(), current_meaning.clone()));
                }
                current_symbol = trimmed
                    .trim_start_matches("- symbol:")
                    .trim()
                    .trim_matches('"')
                    .to_string();
                current_meaning.clear();
            } else if trimmed.starts_with("meaning:") {
                current_meaning = trimmed
                    .trim_start_matches("meaning:")
                    .trim()
                    .trim_matches('"')
                    .to_string();
            } else if trimmed.starts_with("modifiers:") {
                if !current_symbol.is_empty() {
                    brief_forms.push((current_symbol.clone(), current_meaning.clone()));
                }
                break;
            }
        }
    }

    // Generate BRIEF_FORMS
    output.push_str("/// Brief form operators defined in the Worldview spec\n");
    output.push_str("pub const BRIEF_FORMS: &[(&str, &str)] = &[\n");
    for (sym, meaning) in &brief_forms {
        output.push_str(&format!("    (\"{}\", \"{}\"),\n", sym, meaning));
    }
    output.push_str("];\n\n");

    // Parse modifiers
    let mut modifiers = Vec::new();
    let mut in_modifiers = false;
    current_symbol.clear();
    current_meaning.clear();

    for line in yaml.lines() {
        let trimmed = line.trim();

        if trimmed == "modifiers:" {
            in_modifiers = true;
            continue;
        }

        if in_modifiers {
            if trimmed.starts_with("- symbol:") {
                if !current_symbol.is_empty() {
                    modifiers.push((current_symbol.clone(), current_meaning.clone()));
                }
                current_symbol = trimmed
                    .trim_start_matches("- symbol:")
                    .trim()
                    .trim_matches('"')
                    .to_string();
                current_meaning.clear();
            } else if trimmed.starts_with("meaning:") {
                current_meaning = trimmed
                    .trim_start_matches("meaning:")
                    .trim()
                    .trim_matches('"')
                    .to_string();
            } else if trimmed.starts_with("evolution:") || trimmed.starts_with("claim_order:") {
                if !current_symbol.is_empty() {
                    modifiers.push((current_symbol.clone(), current_meaning.clone()));
                }
                break;
            }
        }
    }

    // Generate MODIFIERS
    output.push_str("/// Modifier symbols defined in the Worldview spec\n");
    output.push_str("pub const MODIFIERS: &[(&str, &str)] = &[\n");
    for (sym, meaning) in &modifiers {
        output.push_str(&format!("    (\"{}\", \"{}\"),\n", sym, meaning));
    }
    output.push_str("];\n");

    output
}
