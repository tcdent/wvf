#!/usr/bin/env python3
"""
Worldview Format Specification Generator

Generates documentation, code, and diagrams from canonical definitions.

Usage:
    python generate.py [command]

Commands:
    all         - Generate all outputs (default)
    rust        - Generate Rust constants for validator
    system      - Generate condensed system prompt
    markdown    - Generate markdown tables
    diagrams    - Generate railroad syntax diagrams (SVG)
    readme      - Update README.md with generated content
"""

import sys
import re
import yaml
from pathlib import Path
from typing import List, Tuple

SPEC_DIR = Path(__file__).parent
ROOT_DIR = SPEC_DIR.parent
TOKENS_FILE = SPEC_DIR / "tokens.yaml"
GRAMMAR_FILE = SPEC_DIR / "grammar.pest"


def load_tokens() -> dict:
    """Load the canonical token definitions."""
    with open(TOKENS_FILE) as f:
        return yaml.safe_load(f)


# =============================================================================
# RAILROAD DIAGRAM GENERATION
# =============================================================================

class RailroadDiagram:
    """Simple SVG railroad diagram generator."""

    def __init__(self, title: str):
        self.title = title
        self.elements: List[Tuple[str, str]] = []  # (type, content)

    def terminal(self, text: str):
        """Add a terminal (literal text)."""
        self.elements.append(("terminal", text))
        return self

    def nonterminal(self, text: str):
        """Add a non-terminal (reference to another rule)."""
        self.elements.append(("nonterminal", text))
        return self

    def choice(self, *options: str):
        """Add a choice between options."""
        self.elements.append(("choice", options))
        return self

    def optional(self, text: str, is_terminal: bool = True):
        """Add an optional element."""
        self.elements.append(("optional", (text, is_terminal)))
        return self

    def repeat(self, text: str, is_terminal: bool = False):
        """Add a repeating element."""
        self.elements.append(("repeat", (text, is_terminal)))
        return self

    def to_svg(self) -> str:
        """Generate SVG representation."""
        # Calculate dimensions
        x = 20
        y = 35
        height = 60
        elements_svg = []

        # Start circle
        elements_svg.append(f'<circle cx="{x}" cy="{y}" r="8" fill="none" stroke="#333" stroke-width="2"/>')
        x += 20

        # Draw line
        elements_svg.append(f'<line x1="{x-12}" y1="{y}" x2="{x}" y2="{y}" stroke="#333" stroke-width="2"/>')

        for elem_type, content in self.elements:
            if elem_type == "terminal":
                # Rounded rectangle with text
                text_width = len(content) * 9 + 20
                elements_svg.append(
                    f'<rect x="{x}" y="{y-15}" width="{text_width}" height="30" '
                    f'rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/>'
                )
                elements_svg.append(
                    f'<text x="{x + text_width//2}" y="{y+5}" text-anchor="middle" '
                    f'font-family="monospace" font-size="14" fill="#333">{self._escape(content)}</text>'
                )
                x += text_width

            elif elem_type == "nonterminal":
                # Rectangle with text
                text_width = len(content) * 9 + 20
                elements_svg.append(
                    f'<rect x="{x}" y="{y-15}" width="{text_width}" height="30" '
                    f'fill="#fff4e8" stroke="#333" stroke-width="2"/>'
                )
                elements_svg.append(
                    f'<text x="{x + text_width//2}" y="{y+5}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="14" font-style="italic" fill="#333">{content}</text>'
                )
                x += text_width

            elif elem_type == "choice":
                # Multiple paths
                options = content
                max_width = max(len(opt) * 9 + 20 for opt in options)
                branch_height = 30
                total_height = len(options) * branch_height
                start_x = x

                for i, opt in enumerate(options):
                    opt_y = y + (i - len(options)//2) * branch_height
                    text_width = len(opt) * 9 + 20

                    # Draw branch line
                    if i != len(options)//2:
                        elements_svg.append(
                            f'<path d="M{start_x},{y} Q{start_x+10},{opt_y} {start_x+20},{opt_y}" '
                            f'fill="none" stroke="#333" stroke-width="2"/>'
                        )

                    # Draw terminal
                    elements_svg.append(
                        f'<rect x="{start_x+20}" y="{opt_y-15}" width="{text_width}" height="30" '
                        f'rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/>'
                    )
                    elements_svg.append(
                        f'<text x="{start_x+20 + text_width//2}" y="{opt_y+5}" text-anchor="middle" '
                        f'font-family="monospace" font-size="14" fill="#333">{self._escape(opt)}</text>'
                    )

                    # Join back
                    if i != len(options)//2:
                        elements_svg.append(
                            f'<path d="M{start_x+20+text_width},{opt_y} Q{start_x+30+max_width},{opt_y} {start_x+40+max_width},{y}" '
                            f'fill="none" stroke="#333" stroke-width="2"/>'
                        )

                x += max_width + 50
                height = max(height, total_height + 40)

            elif elem_type == "optional":
                text, is_term = content
                text_width = len(text) * 9 + 20

                # Bypass arc (top)
                elements_svg.append(
                    f'<path d="M{x},{y} Q{x},{y-25} {x+20},{y-25} L{x+text_width},{y-25} '
                    f'Q{x+text_width+20},{y-25} {x+text_width+20},{y}" '
                    f'fill="none" stroke="#333" stroke-width="2"/>'
                )

                # Main path with element
                fill = "#e8f4e8" if is_term else "#fff4e8"
                rx = "15" if is_term else "0"
                elements_svg.append(
                    f'<rect x="{x}" y="{y-15}" width="{text_width}" height="30" '
                    f'rx="{rx}" fill="{fill}" stroke="#333" stroke-width="2"/>'
                )
                elements_svg.append(
                    f'<text x="{x + text_width//2}" y="{y+5}" text-anchor="middle" '
                    f'font-family="monospace" font-size="14" fill="#333">{self._escape(text)}</text>'
                )
                x += text_width + 20

            elif elem_type == "repeat":
                text, is_term = content
                text_width = len(text) * 9 + 20

                # Main element
                fill = "#e8f4e8" if is_term else "#fff4e8"
                rx = "15" if is_term else "0"
                elements_svg.append(
                    f'<rect x="{x}" y="{y-15}" width="{text_width}" height="30" '
                    f'rx="{rx}" fill="{fill}" stroke="#333" stroke-width="2"/>'
                )
                elements_svg.append(
                    f'<text x="{x + text_width//2}" y="{y+5}" text-anchor="middle" '
                    f'font-family="monospace" font-size="14" fill="#333">{self._escape(text)}</text>'
                )

                # Loop back arrow
                elements_svg.append(
                    f'<path d="M{x+text_width},{y} Q{x+text_width+15},{y} {x+text_width+15},{y+20} '
                    f'L{x-15},{y+20} Q{x-15},{y} {x},{y}" '
                    f'fill="none" stroke="#333" stroke-width="2" marker-start="url(#arrow)"/>'
                )
                x += text_width

            # Connecting line
            elements_svg.append(f'<line x1="{x}" y1="{y}" x2="{x+15}" y2="{y}" stroke="#333" stroke-width="2"/>')
            x += 15

        # End circle (double)
        elements_svg.append(f'<circle cx="{x+8}" cy="{y}" r="8" fill="none" stroke="#333" stroke-width="2"/>')
        elements_svg.append(f'<circle cx="{x+8}" cy="{y}" r="4" fill="#333"/>')

        width = x + 30

        # Build SVG
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">{self.title}</text>
  {"".join(elements_svg)}
</svg>'''
        return svg

    def _escape(self, text: str) -> str:
        """Escape special XML characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_railroad_diagrams(tokens: dict) -> dict:
    """Generate railroad diagram SVGs for key syntax elements."""
    diagrams = {}

    # Document structure
    doc = RailroadDiagram("document")
    doc.repeat("concept", False)
    diagrams["document"] = doc.to_svg()

    # Concept
    concept = RailroadDiagram("concept")
    concept.nonterminal("concept_name").repeat("facet", False)
    diagrams["concept"] = concept.to_svg()

    # Facet
    facet = RailroadDiagram("facet")
    facet.terminal("  .").nonterminal("facet_name").repeat("claim", False)
    diagrams["facet"] = facet.to_svg()

    # Claim (simplified)
    claim = RailroadDiagram("claim")
    claim.terminal("    -").nonterminal("claim_body")
    claim.optional("| condition").optional("@source").optional("&reference")
    diagrams["claim"] = claim.to_svg()

    # Brief forms
    bf_symbols = [bf["symbol"] for bf in tokens["brief_forms"]]
    brief = RailroadDiagram("brief_form")
    brief.nonterminal("operand").choice(*bf_symbols[:4]).nonterminal("operand")
    diagrams["brief_form"] = brief.to_svg()

    # Modifiers
    mod_symbols = [m["symbol"] for m in tokens["modifiers"]]
    modifier = RailroadDiagram("modifier")
    modifier.choice(*mod_symbols)
    diagrams["modifier"] = modifier.to_svg()

    return diagrams


def generate_diagrams_markdown(tokens: dict) -> str:
    """Generate markdown with embedded SVG diagrams."""
    diagrams = generate_railroad_diagrams(tokens)

    output = ["## Syntax Diagrams\n"]

    for name, svg in diagrams.items():
        output.append(f"### {name.replace('_', ' ').title()}\n")
        output.append(svg)
        output.append("\n")

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
    output.append("Common relationships use compact symbols:\n")
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
    """Update README.md with generated syntax diagrams section."""
    readme_path = ROOT_DIR / "README.md"
    readme_content = readme_path.read_text()

    # Generate the syntax diagrams section
    diagrams_section = generate_diagrams_markdown(tokens)

    # Check if section already exists
    start_marker = "<!-- BEGIN GENERATED SYNTAX DIAGRAMS -->"
    end_marker = "<!-- END GENERATED SYNTAX DIAGRAMS -->"

    new_section = f"{start_marker}\n{diagrams_section}\n{end_marker}"

    if start_marker in readme_content:
        # Replace existing section
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

    if command in ("diagrams", "all"):
        diagrams = generate_railroad_diagrams(tokens)
        print("=== RAILROAD DIAGRAMS ===")
        # Save diagrams to spec/diagrams/
        diagrams_dir = SPEC_DIR / "diagrams"
        diagrams_dir.mkdir(exist_ok=True)
        for name, svg in diagrams.items():
            svg_path = diagrams_dir / f"{name}.svg"
            svg_path.write_text(svg)
            print(f"Written: {svg_path}")
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
