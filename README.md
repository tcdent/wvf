# Worldview

A constrained notation format for encoding conceptual worldviews, where the structure itself enforces what can and cannot be stored.

## Overview

The **Worldview format** (file extension: `.wvf`) is a declarative notation for storing beliefs, stances, and understanding about concepts. Its primary value is structural constraint—the rigid hierarchy of Concepts, Facets, and Claims makes it impossible to encode inappropriate content types.

This solves a fundamental problem: when beliefs are stored in unstructured formats like Markdown, documents grow with repetitious statements, narrative tangents, and content that strays from the intended purpose. The Worldview format prevents this by requiring that every piece of information fit into a strict hierarchy—if something doesn't fit the structure, it doesn't belong.

Token efficiency is a consequence, not the goal: when you can only store structured beliefs, documents stay focused and compact.

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

Minimal operators for common relationships (less common relationships use natural language):

| Symbol | Meaning | Example |
|--------|---------|---------|
| `=>` | causes, leads to | `power => corruption` |
| `~` | similar to, resembles | `authority ~ influence` |
| `=` | equivalent to, means | `formal = official` |
| `vs` | contrasts with, in tension with | `efficiency vs thoroughness` |

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

1. **Structure as enforcement**: The rigid hierarchy prevents inappropriate content—if it doesn't fit, it doesn't belong
2. **State over narrative**: Capture what is believed, not how it came to be believed
3. **Conflict tolerance**: Real worldviews contain tensions—hold them without forcing resolution
4. **Minimal notation**: Only universally intuitive symbols; natural language for uncommon relationships
5. **Freeform vocabulary**: Structure is defined; content remains unconstrained

## LLM-Native Tokens

The notation uses symbols that LLMs already understand intuitively—tokens whose semantics are well-established in training data:

- `?` for uncertainty — LLMs reliably interpret `?` as questioning or tentative
- `!` for emphasis — strongly associated with assertion and importance
- `=>` for causation — arrow notation for "leads to" is universal
- `~` for similarity — mathematical approximation notation
- `@` for attribution — familiar from email and social media
- `&` for reference — established linking/joining semantics

This isn't arbitrary shorthand—it's leveraging semantic associations that already exist in model weights. When an LLM sees `collapse?`, it understands uncertainty without needing explicit instruction.

Symbols that *don't* have clear pre-existing semantics (like `><` for tension or `//` for "regardless") are avoided. If a relationship requires explanation to understand, natural language is clearer than a novel symbol.

## Why "Worldview"?

The name emphasizes the core use case: encoding *how concepts are understood* rather than just storing facts. This is different from:

- **Markdown files**: No structural constraints; content drifts and duplicates
- **Knowledge bases**: Store facts, not interpretations
- **RAG systems**: Retrieve relevant content per query
- **Memory systems**: Log events chronologically

Worldview documents capture the *lens* through which all subsequent reasoning should be filtered—and the format's constraints ensure documents stay focused on that purpose.

## File Extension

- **Extension**: `.wvf` (Worldview Format)
- **MIME type**: `text/x-worldview` (proposed)

## License

MIT

## Specification

See [SPEC.md](SPEC.md) for the complete format specification.
