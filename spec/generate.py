#!/usr/bin/env python3
"""
Worldview Format Specification Generator

Generates documentation and code from canonical definitions.

Usage:
    python generate.py [command]

Commands:
    all         - Generate all outputs (default)
    rust        - Generate Rust constants for validator
    system      - Generate condensed system prompt
    markdown    - Generate markdown tables
    readme      - Update README.md with generated content
"""

import sys
import re
import yaml
from pathlib import Path
from typing import List

SPEC_DIR = Path(__file__).parent
ROOT_DIR = SPEC_DIR.parent
TOKENS_FILE = SPEC_DIR / "tokens.yaml"
GRAMMAR_FILE = SPEC_DIR / "grammar.pest"


def load_tokens() -> dict:
    """Load the canonical token definitions."""
    with open(TOKENS_FILE) as f:
        return yaml.safe_load(f)


# =============================================================================
# LANGUAGE SPECIFICATION GENERATION (for README)
# =============================================================================

def generate_language_spec(tokens: dict) -> str:
    """Generate a language specification section following standard documentation conventions."""
    output = []

    output.append("## Language Specification\n")

    # Grammar (EBNF-style)
    output.append("### Grammar\n")
    output.append("```ebnf")
    output.append("document    = concept+ ;")
    output.append("concept     = concept_name NEWLINE facet+ ;")
    output.append("facet       = INDENT(2) '.' facet_name NEWLINE claim+ ;")
    output.append("claim       = INDENT(4) '-' claim_body [condition*] [source*] [reference*] ;")
    output.append("")
    output.append("condition   = '|' text ;")
    output.append("source      = '@' identifier ;")
    output.append("reference   = '&' concept_name ['.' facet_name] ;")
    output.append("```\n")

    # Structure
    output.append("### Structure\n")
    output.append("```")
    output.append("Concept           (unindented, bare text)")
    output.append("  .facet          (2-space indent, dot prefix)")
    output.append("    - claim       (4-space indent, dash prefix)")
    output.append("```\n")

    # Inline elements
    output.append("### Inline Elements\n")
    output.append("| Symbol | Name | Description |")
    output.append("|--------|------|-------------|")
    for elem in tokens["inline_elements"]:
        output.append(f"| `{elem['symbol']}` | {elem['name']} | {elem['meaning']} |")
    output.append("")

    # Brief forms
    output.append("### Brief Forms\n")
    output.append("Minimal operators for common relationships (less common relationships use natural language):\n")
    output.append("| Symbol | Meaning | Example |")
    output.append("|--------|---------|---------|")
    for bf in tokens["brief_forms"]:
        output.append(f"| `{bf['symbol']}` | {bf['meaning']} | `{bf['example']}` |")
    output.append("")

    # Modifiers
    output.append("### Modifiers\n")
    output.append("Suffix markers that inflect claim meaning:\n")
    output.append("| Symbol | Meaning | Example |")
    output.append("|--------|---------|---------|")
    for mod in tokens["modifiers"]:
        output.append(f"| `{mod['symbol']}` | {mod['meaning']} | `{mod['example']}` |")
    output.append("")

    # Evolution
    output.append("### Evolution\n")
    evo = tokens["evolution"]["supersession"]
    output.append(f"Supersession marker `{evo['syntax']}` indicates a belief that replaces a prior one:\n")
    output.append("```")
    output.append(evo['example'])
    output.append("```\n")

    # Claim order
    output.append("### Claim Syntax\n")
    output.append("Claims follow positional grammar—position implies role:\n")
    output.append("```")
    output.append("- claim_text | condition @source &reference")
    output.append("```")
    output.append("")

    return "\n".join(output)


# =============================================================================
# RUST GENERATION (for build.rs)
# =============================================================================

def generate_rust_constants(tokens: dict) -> str:
    """Generate Rust constants for the validator."""
    output = []
    output.append("// Auto-generated from spec/tokens.yaml")
    output.append("// Do not edit manually - regenerated at build time")
    output.append("")

    # Brief forms
    output.append("/// Brief form operators defined in the Worldview spec")
    output.append("pub const BRIEF_FORMS: &[(&str, &str)] = &[")
    for bf in tokens["brief_forms"]:
        output.append(f'    ("{bf["symbol"]}", "{bf["meaning"]}"),')
    output.append("];")
    output.append("")

    # Modifiers
    output.append("/// Modifier symbols defined in the Worldview spec")
    output.append("pub const MODIFIERS: &[(&str, &str)] = &[")
    for mod in tokens["modifiers"]:
        output.append(f'    ("{mod["symbol"]}", "{mod["meaning"]}"),')
    output.append("];")
    output.append("")

    # Brief form symbols only (for quick lookup)
    output.append("/// Brief form operator symbols (ordered by length for matching)")
    output.append("pub const BRIEF_FORM_SYMBOLS: &[&str] = &[")
    # Sort by length descending for proper matching
    symbols = sorted([bf["symbol"] for bf in tokens["brief_forms"]], key=len, reverse=True)
    for sym in symbols:
        output.append(f'    "{sym}",')
    output.append("];")
    output.append("")

    # Modifier symbols only
    output.append("/// Modifier symbols")
    output.append("pub const MODIFIER_SYMBOLS: &[char] = &[")
    for mod in tokens["modifiers"]:
        output.append(f"    '{mod['symbol']}',")
    output.append("];")
    output.append("")

    # Inline element symbols
    output.append("/// Inline element symbols")
    output.append("pub const CONDITION_SYMBOL: char = '|';")
    output.append("pub const SOURCE_SYMBOL: char = '@';")
    output.append("pub const REFERENCE_SYMBOL: char = '&';")
    output.append("")

    # Indentation levels
    output.append("/// Indentation levels (in spaces)")
    output.append("pub const CONCEPT_INDENT: usize = 0;")
    output.append("pub const FACET_INDENT: usize = 2;")
    output.append("pub const CLAIM_INDENT: usize = 4;")
    output.append("")

    # Prefixes
    output.append("/// Element prefixes")
    output.append("pub const FACET_PREFIX: char = '.';")
    output.append("pub const CLAIM_PREFIX: char = '-';")

    return "\n".join(output)


def generate_build_rs() -> str:
    """Generate build.rs for the validator."""
    return '''//! Build script for worldview-validator
//! Generates token definitions from spec/tokens.yaml at compile time.

use std::env;
use std::fs;
use std::path::Path;

fn main() {
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("tokens.rs");

    // Read tokens.yaml from spec directory
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let tokens_path = Path::new(&manifest_dir).parent().unwrap().join("spec/tokens.yaml");

    println!("cargo:rerun-if-changed={}", tokens_path.display());

    let tokens_yaml = fs::read_to_string(&tokens_path)
        .expect("Failed to read spec/tokens.yaml");

    // Parse YAML manually (avoiding serde dependency in build script)
    let rust_code = generate_tokens_rs(&tokens_yaml);

    fs::write(&dest_path, rust_code).unwrap();
}

fn generate_tokens_rs(yaml: &str) -> String {
    let mut output = String::from("// Auto-generated from spec/tokens.yaml\\n\\n");

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
                current_symbol = trimmed.trim_start_matches("- symbol:").trim().trim_matches(\'"\').to_string();
                current_meaning.clear();
            } else if trimmed.starts_with("meaning:") {
                current_meaning = trimmed.trim_start_matches("meaning:").trim().trim_matches(\'"\').to_string();
            } else if trimmed.starts_with("modifiers:") {
                if !current_symbol.is_empty() {
                    brief_forms.push((current_symbol.clone(), current_meaning.clone()));
                }
                break;
            }
        }
    }

    // Generate BRIEF_FORMS
    output.push_str("pub const BRIEF_FORMS: &[(&str, &str)] = &[\\n");
    for (sym, meaning) in &brief_forms {
        output.push_str(&format!("    (\\"{sym}\\", \\"{meaning}\\"),\\n"));
    }
    output.push_str("];\\n\\n");

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
                current_symbol = trimmed.trim_start_matches("- symbol:").trim().trim_matches(\'"\').to_string();
                current_meaning.clear();
            } else if trimmed.starts_with("meaning:") {
                current_meaning = trimmed.trim_start_matches("meaning:").trim().trim_matches(\'"\').to_string();
            } else if trimmed.starts_with("evolution:") || trimmed.starts_with("claim_order:") {
                if !current_symbol.is_empty() {
                    modifiers.push((current_symbol.clone(), current_meaning.clone()));
                }
                break;
            }
        }
    }

    // Generate MODIFIERS
    output.push_str("pub const MODIFIERS: &[(&str, &str)] = &[\\n");
    for (sym, meaning) in &modifiers {
        output.push_str(&format!("    (\\"{sym}\\", \\"{meaning}\\"),\\n"));
    }
    output.push_str("];\\n\\n");

    // Generate symbol-only arrays
    output.push_str("pub const BRIEF_FORM_SYMBOLS: &[&str] = &[\\n");
    let mut symbols: Vec<_> = brief_forms.iter().map(|(s, _)| s.clone()).collect();
    symbols.sort_by(|a, b| b.len().cmp(&a.len())); // Sort by length descending
    for sym in &symbols {
        output.push_str(&format!("    \\"{sym}\\",\\n"));
    }
    output.push_str("];\\n\\n");

    output.push_str("pub const MODIFIER_SYMBOLS: &[char] = &[\\n");
    for (sym, _) in &modifiers {
        if sym.len() == 1 {
            output.push_str(&format!("    \\'{}\\',\\n", sym.chars().next().unwrap()));
        }
    }
    output.push_str("];\\n\\n");

    // Static constants
    output.push_str("pub const CONDITION_SYMBOL: char = \\'|\\';\\n");
    output.push_str("pub const SOURCE_SYMBOL: char = \\'@\\';\\n");
    output.push_str("pub const REFERENCE_SYMBOL: char = \\'&\\';\\n");
    output.push_str("pub const CONCEPT_INDENT: usize = 0;\\n");
    output.push_str("pub const FACET_INDENT: usize = 2;\\n");
    output.push_str("pub const CLAIM_INDENT: usize = 4;\\n");
    output.push_str("pub const FACET_PREFIX: char = \\'.\\';\\n");
    output.push_str("pub const CLAIM_PREFIX: char = \\'-\\';\\n");

    output
}
'''


# =============================================================================
# MARKDOWN GENERATION
# =============================================================================

def generate_markdown_tables(tokens: dict) -> str:
    """Generate markdown tables for SPEC.md."""
    output = []

    # Structure table
    output.append("### Hierarchy\n")
    output.append("| Element | Notation | Indentation |")
    output.append("|---------|----------|-------------|")
    for name, info in tokens["structure"].items():
        prefix = f"`{info['prefix']}`" if info["prefix"] else "Bare text"
        indent = f"{info['indent']} spaces" if info["indent"] > 0 else "None (column 0)"
        output.append(f"| {name.title()} | {prefix} | {indent} |")
    output.append("")

    # Inline elements table
    output.append("### Inline Elements\n")
    output.append("| Element | Symbol | Position |")
    output.append("|---------|--------|----------|")
    for elem in tokens["inline_elements"]:
        symbol = f"`{elem['symbol']}`"
        output.append(f"| {elem['name'].title()} | {symbol} | {elem['position'].title()} |")
    output.append("")

    # Brief forms table
    output.append("## Brief Forms\n")
    output.append("Minimal operators for common relationships (less common relationships use natural language):\n")
    output.append("| Symbol | Meaning | Example |")
    output.append("|--------|---------|---------|")
    for bf in tokens["brief_forms"]:
        output.append(f"| `{bf['symbol']}` | {bf['meaning']} | `{bf['example']}` |")
    output.append("")

    # Modifiers table
    output.append("## Modifiers\n")
    output.append("Suffix markers inflect claim meaning:\n")
    output.append("| Modifier | Meaning | Example |")
    output.append("|----------|---------|---------|")
    for mod in tokens["modifiers"]:
        output.append(f"| `{mod['symbol']}` | {mod['meaning']} | `{mod['example']}` |")
    output.append("")

    return "\n".join(output)


# =============================================================================
# SYSTEM PROMPT GENERATION
# =============================================================================

def generate_system_prompt(tokens: dict) -> str:
    """Generate a condensed system prompt for LLM context."""
    output = []

    output.append("# Worldview System Prompt")
    output.append("")
    output.append("You maintain a Worldview format document—a compact notation encoding beliefs, stances, and understanding. The entire document is always in context; you update it autonomously as you learn.")
    output.append("")

    # Structure
    output.append("## Structure")
    output.append("")
    output.append("```")
    output.append("Concept           (unindented)")
    output.append("  .facet          (2-space indent, dot prefix)")
    output.append("    - claim       (4-space indent, dash prefix)")
    output.append("```")
    output.append("")
    output.append("Every concept has facets. Every facet has claims. Claims may include conditions, sources, and references.")
    output.append("")

    # Notation table
    output.append("## Notation")
    output.append("")
    output.append("| Symbol | Meaning | Example |")
    output.append("|--------|---------|---------|")

    # Inline elements
    for elem in tokens["inline_elements"]:
        output.append(f"| `{elem['symbol']}` | {elem['name']} ({elem['meaning']}) | `{elem['example']}` |")

    # Brief forms
    for bf in tokens["brief_forms"]:
        output.append(f"| `{bf['symbol']}` | {bf['meaning']} | `{bf['example']}` |")

    # Modifiers
    for mod in tokens["modifiers"]:
        output.append(f"| `{mod['symbol']}` | {mod['meaning']} | `{mod['example']}` |")

    # Evolution
    evo = tokens["evolution"]["supersession"]
    output.append(f"| `[<= prior]` | supersedes | `{evo['example'].split('- ')[1]}` |")
    output.append("")

    # Claim order
    output.append("## Claim Order")
    output.append("")
    output.append("```")
    output.append("- claim | condition @source &reference")
    output.append("```")
    output.append("")
    output.append("Position implies role. No labels needed.")
    output.append("")

    # Maintenance rules
    output.append("## Maintenance Rules")
    output.append("")
    output.append("- **Add** new concepts, facets, or claims as understanding develops")
    output.append("- **Update** claims by replacing or adding supersession markers")
    output.append("- **Reference** related concepts with `&` rather than duplicating")
    output.append("- **Preserve** density—no prose, articles, or filler")
    output.append("- **Tolerate** contradiction—conflicting claims may coexist")
    output.append("")

    # What's stored vs derived
    output.append("## What's Stored vs Derived")
    output.append("")
    output.append("**Stored:** Claims, conditions, sources, references, structure")
    output.append("")
    output.append("**Derived at runtime:** Confidence (from sources/conditions), predictions, evaluations, identity")
    output.append("")

    # Example
    output.append("## Example")
    output.append("")
    output.append("```")
    output.append("Trust")
    output.append("  .formation")
    output.append("    - slow")
    output.append("    - requires consistency | over time")
    output.append("  .erosion")
    output.append("    - fast !")
    output.append("    - asymmetric vs formation &Trust.formation")
    output.append("```")
    output.append("")
    output.append("When you encounter information that refines understanding, update the Worldview document. Carry this worldview forward into all reasoning.")
    output.append("")

    return "\n".join(output)


# =============================================================================
# README UPDATE
# =============================================================================

def update_readme(tokens: dict) -> str:
    """Update README.md with generated language specification section."""
    readme_path = ROOT_DIR / "README.md"
    readme_content = readme_path.read_text()

    # Generate the language specification section
    spec_section = generate_language_spec(tokens)

    # Check for old diagram markers first and replace them
    old_start_marker = "<!-- BEGIN GENERATED SYNTAX DIAGRAMS -->"
    old_end_marker = "<!-- END GENERATED SYNTAX DIAGRAMS -->"

    # New markers
    start_marker = "<!-- BEGIN GENERATED LANGUAGE SPEC -->"
    end_marker = "<!-- END GENERATED LANGUAGE SPEC -->"

    new_section = f"{start_marker}\n{spec_section}\n{end_marker}"

    if old_start_marker in readme_content:
        # Replace old diagram section with new spec section
        pattern = f"{re.escape(old_start_marker)}.*?{re.escape(old_end_marker)}"
        readme_content = re.sub(pattern, new_section, readme_content, flags=re.DOTALL)
    elif start_marker in readme_content:
        # Replace existing spec section
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        readme_content = re.sub(pattern, new_section, readme_content, flags=re.DOTALL)
    else:
        # Insert before "## Tools" section
        tools_marker = "## Tools"
        if tools_marker in readme_content:
            readme_content = readme_content.replace(
                tools_marker,
                f"{new_section}\n\n{tools_marker}"
            )
        else:
            # Append to end
            readme_content += f"\n\n{new_section}\n"

    return readme_content


# =============================================================================
# MAIN
# =============================================================================

def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    tokens = load_tokens()

    if command in ("markdown", "all"):
        md = generate_markdown_tables(tokens)
        print("=== MARKDOWN TABLES ===")
        print(md)
        if command == "all":
            print()

    if command in ("rust", "all"):
        rust = generate_rust_constants(tokens)
        print("=== RUST CONSTANTS ===")
        print(rust)
        # Write to file
        rust_file = ROOT_DIR / "validator" / "src" / "tokens_generated.rs"
        rust_file.write_text(rust + "\n")
        print(f"\nWritten to: {rust_file}")
        if command == "all":
            print()

    if command in ("system", "all"):
        system = generate_system_prompt(tokens)
        print("=== SYSTEM PROMPT ===")
        print(system)
        # Write to file
        system_file = ROOT_DIR / "system.md"
        system_file.write_text(system)
        print(f"\nWritten to: {system_file}")
        if command == "all":
            print()

    if command in ("readme", "all"):
        readme = update_readme(tokens)
        readme_path = ROOT_DIR / "README.md"
        readme_path.write_text(readme)
        print(f"=== README UPDATED ===")
        print(f"Written to: {readme_path}")

    if command == "build-rs":
        # Special command: generate build.rs content
        print(generate_build_rs())


if __name__ == "__main__":
    main()
