//! Build script for worldview-validator
//! Generates token definitions from spec/tokens.yaml at compile time.

use serde::Deserialize;
use std::env;
use std::fs;
use std::path::Path;

#[derive(Deserialize)]
struct TokenSpec {
    brief_forms: Vec<BriefForm>,
    modifiers: Vec<Modifier>,
}

#[derive(Deserialize)]
struct BriefForm {
    symbol: String,
    meaning: String,
}

#[derive(Deserialize)]
struct Modifier {
    symbol: String,
    meaning: String,
}

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
    let spec: TokenSpec = serde_yaml::from_str(&tokens_yaml).expect("Failed to parse tokens.yaml");

    let rust_code = generate_tokens_rs(&spec);
    fs::write(&dest_path, rust_code).unwrap();
}

fn generate_tokens_rs(spec: &TokenSpec) -> String {
    let mut output = String::from("// Auto-generated from spec/tokens.yaml at compile time\n\n");

    // Generate BRIEF_FORMS
    output.push_str("/// Brief form operators defined in the Worldview spec\n");
    output.push_str("pub const BRIEF_FORMS: &[(&str, &str)] = &[\n");
    for bf in &spec.brief_forms {
        output.push_str(&format!("    (\"{}\", \"{}\"),\n", bf.symbol, bf.meaning));
    }
    output.push_str("];\n\n");

    // Generate MODIFIERS
    output.push_str("/// Modifier symbols defined in the Worldview spec\n");
    output.push_str("pub const MODIFIERS: &[(&str, &str)] = &[\n");
    for m in &spec.modifiers {
        output.push_str(&format!("    (\"{}\", \"{}\"),\n", m.symbol, m.meaning));
    }
    output.push_str("];\n");

    output
}
