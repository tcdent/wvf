#!/usr/bin/env python3
"""
Worldview Format Specification Generator

Generates documentation and code from the canonical tokens.yaml definition.

Usage:
    python generate.py [output_type]

Output types:
    markdown    - Generate markdown tables for documentation
    rust        - Generate Rust constants for validator
    system      - Generate condensed system prompt
    all         - Generate all outputs (default)
"""

import sys
import yaml
from pathlib import Path

SPEC_DIR = Path(__file__).parent
TOKENS_FILE = SPEC_DIR / "tokens.yaml"


def load_tokens() -> dict:
    """Load the canonical token definitions."""
    with open(TOKENS_FILE) as f:
        return yaml.safe_load(f)


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
        prefix = info["prefix"] if info["prefix"] else "Bare text"
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
    output.append("| Symbol | Meaning |")
    output.append("|--------|---------|")
    for bf in tokens["brief_forms"]:
        output.append(f"| `{bf['symbol']}` | {bf['meaning']} |")
    output.append("")

    # Brief forms examples
    output.append("### Examples\n")
    output.append("```")
    for bf in tokens["brief_forms"][:4]:  # First 4 examples
        output.append(f"- {bf['example']}")
    output.append("```")
    output.append("")

    # Modifiers table
    output.append("## Modifiers\n")
    output.append("Suffix markers inflect claim meaning:\n")
    output.append("| Modifier | Meaning |")
    output.append("|----------|---------|")
    for mod in tokens["modifiers"]:
        output.append(f"| `{mod['symbol']}` | {mod['meaning']} |")
    output.append("")

    # Modifier examples
    output.append("### Examples\n")
    output.append("```")
    for mod in tokens["modifiers"]:
        output.append(f"- {mod['example']}")
    output.append("```")
    output.append("")

    return "\n".join(output)


# =============================================================================
# RUST GENERATION
# =============================================================================

def generate_rust_constants(tokens: dict) -> str:
    """Generate Rust constants for the validator."""
    output = []
    output.append("// Auto-generated from spec/tokens.yaml")
    output.append("// Do not edit manually - run `python spec/generate.py rust`")
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
# MAIN
# =============================================================================

def main():
    output_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    tokens = load_tokens()

    if output_type in ("markdown", "all"):
        md = generate_markdown_tables(tokens)
        print("=== MARKDOWN TABLES ===")
        print(md)
        if output_type == "all":
            print()

    if output_type in ("rust", "all"):
        rust = generate_rust_constants(tokens)
        print("=== RUST CONSTANTS ===")
        print(rust)
        # Write to file
        rust_file = SPEC_DIR.parent / "validator" / "src" / "tokens_generated.rs"
        rust_file.write_text(rust + "\n")
        print(f"\nWritten to: {rust_file}")
        if output_type == "all":
            print()

    if output_type in ("system", "all"):
        system = generate_system_prompt(tokens)
        print("=== SYSTEM PROMPT ===")
        print(system)
        # Write to file
        system_file = SPEC_DIR.parent / "system.md"
        system_file.write_text(system)
        print(f"\nWritten to: {system_file}")


if __name__ == "__main__":
    main()
