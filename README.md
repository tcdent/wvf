# Worldview

A compact notation format for encoding and maintaining conceptual worldviews over time, designed for LLM context persistence.

## Overview

The **Worldview format** (file extension: `.wvf`) is a declarative notation for storing beliefs, stances, and understanding about concepts. Unlike retrieval-augmented generation (RAG) which selectively includes information, Worldview documents are designed to remain *entirely in context* across all LLM interactions.

This solves a fundamental problem: LLMs have foundational beliefs and stances that should inform all reasoning, not just topically-matched queries. The Worldview format is dense enough that an entire belief system can remain in context permanently.

## Quick Start

### Example Document

```wvf
Trust
  .formation
    - slow
    - requires consistency | over time
    - contextual @personal-experience
  .erosion
    - fast !
    - single violation => collapse?
    - asymmetric vs formation &Trust.formation
```

<!-- BEGIN GENERATED LANGUAGE SPEC -->
## Language Specification

### Grammar

```ebnf
document    = concept+ ;
concept     = concept_name NEWLINE facet+ ;
facet       = INDENT(2) '.' facet_name NEWLINE claim+ ;
claim       = INDENT(4) '-' claim_body [condition*] [source*] [reference*] ;

condition   = '|' text ;
source      = '@' identifier ;
reference   = '&' concept_name ['.' facet_name] ;
```

### Structure

```
Concept           (unindented, bare text)
  .facet          (2-space indent, dot prefix)
    - claim       (4-space indent, dash prefix)
```

### Inline Elements

| Symbol | Name | Description |
|--------|------|-------------|
| `|` | condition | when/if applies |
| `@` | source | basis for belief |
| `&` | reference | links to other concept.facet |

### Brief Forms

Compact operators for common relationships:

| Symbol | Meaning | Example |
|--------|---------|---------|
| `=>` | causes, leads to | `power => corruption` |
| `<=` | caused by, results from | `trust <= consistency` |
| `<>` | mutual, bidirectional | `accountability <> trust` |
| `><` | tension, conflicts with | `efficiency >< thoroughness` |
| `~` | similar to, resembles | `authority ~ influence` |
| `=` | equivalent to, means | `formal = official` |
| `vs` | in contrast to | `asymmetric vs formation` |
| `//` | regardless of | `self-perpetuate // original purpose` |

### Modifiers

Suffix markers that inflect claim meaning:

| Symbol | Meaning | Example |
|--------|---------|---------|
| `^` | increasing, trending up | `concentration^` |
| `v` | decreasing, trending down | `trust v` |
| `!` | strong, emphatic, high confidence | `fast !` |
| `?` | uncertain, contested, tentative | `free-will?` |
| `*` | notable, important, flagged | `paradigm-shift*` |

### Evolution

Supersession marker `[<= prior belief]` indicates a belief that replaces a prior one:

```
- adaptive [<= inherently good]
```

### Claim Syntax

Claims follow positional grammar—position implies role:

```
- claim_text | condition @source &reference
```

<!-- END GENERATED LANGUAGE SPEC -->

## Tools

This repository includes a complete toolchain for working with Worldview documents:

### CLI (`worldview`)

A unified command-line tool for working with Worldview files.

```bash
# Validate a file
worldview validate example.wvf

# Validate from stdin
cat example.wvf | worldview validate --stdin

# Add a fact using AI agent
worldview add "Trust is built slowly through consistent actions" --file worldview.wvf

# Use a specific model
worldview add "Power corrupts when unchecked" --model claude-opus-4-5-20251101

# View format specification
worldview --help
```

The `add` command uses an AI agent that:
1. Reads existing content to understand structure
2. Determines appropriate concept/facet placement
3. Formats statements using proper notation
4. Validates before writing (validation runs automatically)

### Evaluation Framework

A Python framework for testing how well LLMs can leverage Worldview-encoded beliefs.

```bash
# Install dependencies
uv sync

# Run evaluations
uv run python -m evals run --models claude-sonnet gpt-5.2

# Run specific difficulty
uv run python -m evals run --difficulty extreme

# List available models and test cases
uv run python -m evals list-models
uv run python -m evals list-cases
```

## Project Structure

```
wvf/
├── spec/                    # Canonical specification
│   ├── tokens.yaml          # Token definitions (source of truth)
│   ├── grammar.pest         # PEG grammar
│   └── generate.py          # Generates docs and code from tokens.yaml
├── validator/               # Rust validation library
│   ├── src/lib.rs           # Validation logic
│   └── build.rs             # Generates tokens from spec at compile time
├── cli/                     # Rust CLI (unified binary)
│   ├── src/main.rs          # Subcommand dispatch
│   ├── src/validate.rs      # Validate subcommand
│   └── src/add.rs           # Add subcommand (AI agent)
├── evals/                   # Python evaluation framework
│   ├── cli.py               # Evaluation CLI
│   ├── read_eval/           # Read comprehension tests
│   └── write_eval/          # Write/generation tests
├── SPEC.md                  # Full format specification
├── system.md                # Condensed system prompt (generated)
└── example.wvf              # Example document
```

## Building

### Prerequisites

- Rust 1.70+
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)

### Build CLI

```bash
# Setup vendored dependencies and build
cd cli && ./setup.sh && cargo build --release

# Binary will be at cli/target/release/worldview
```

### Run Evaluations

```bash
# From project root
uv sync
uv run python -m evals --help
```

## Design Principles

The Worldview format follows five core principles:

1. **State over narrative**: Capture what is believed, not how it came to be believed
2. **Predictability allows omission**: If structure makes something inferable, don't write it
3. **Conflict tolerance**: Real worldviews contain tensions—hold them without forcing resolution
4. **Freeform vocabulary**: Structure is defined; content remains unconstrained
5. **LLM-native, human-inspectable**: Optimized for machine parsing while remaining readable

## Why "Worldview"?

The name emphasizes the core use case: encoding *how concepts are understood* rather than just storing facts. This is different from:

- **Knowledge bases**: Store facts, not interpretations
- **RAG systems**: Retrieve relevant content per query
- **Memory systems**: Log events chronologically

Worldview documents capture the *lens* through which all subsequent reasoning should be filtered.

## File Extension

- **Extension**: `.wvf` (Worldview Format)
- **MIME type**: `text/x-worldview` (proposed)

## License

MIT

## Specification

See [SPEC.md](SPEC.md) for the complete format specification.
