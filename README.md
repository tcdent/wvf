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

### Key Concepts

- **Concepts**: Subjects of belief (e.g., Trust, Power, Human-nature)
- **Facets**: Aspects or dimensions (e.g., .formation, .erosion)
- **Claims**: Assertions about a facet
- **Conditions**: When/if the claim applies (prefix: `|`)
- **Sources**: Basis for belief (prefix: `@`)
- **References**: Links to other concepts (prefix: `&`)

### Brief Form Operators

| Symbol | Meaning |
|--------|---------|
| `=>` | causes, leads to |
| `<=` | caused by |
| `<>` | mutual, bidirectional |
| `><` | tension, conflicts with |
| `~` | similar to |
| `!` | emphatic, strong |
| `?` | uncertain |
| `^` | increasing |
| `v` | decreasing |

<!-- BEGIN GENERATED SYNTAX DIAGRAMS -->
## Syntax Diagrams

### Document

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 168 60" width="168" height="60">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">document</text>
  <circle cx="20" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><line x1="28" y1="35" x2="40" y2="35" stroke="#333" stroke-width="2"/><rect x="40" y="20" width="83" height="30" rx="0" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="81" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">concept</text><path d="M123,35 Q138,35 138,55 L25,55 Q25,35 40,35" fill="none" stroke="#333" stroke-width="2" marker-start="url(#arrow)"/><line x1="123" y1="35" x2="138" y2="35" stroke="#333" stroke-width="2"/><circle cx="146" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><circle cx="146" cy="35" r="4" fill="#333"/>
</svg>


### Concept

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 293 60" width="293" height="60">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">concept</text>
  <circle cx="20" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><line x1="28" y1="35" x2="40" y2="35" stroke="#333" stroke-width="2"/><rect x="40" y="20" width="128" height="30" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="104" y="40" text-anchor="middle" font-family="sans-serif" font-size="14" font-style="italic" fill="#333">concept_name</text><line x1="168" y1="35" x2="183" y2="35" stroke="#333" stroke-width="2"/><rect x="183" y="20" width="65" height="30" rx="0" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="215" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">facet</text><path d="M248,35 Q263,35 263,55 L168,55 Q168,35 183,35" fill="none" stroke="#333" stroke-width="2" marker-start="url(#arrow)"/><line x1="248" y1="35" x2="263" y2="35" stroke="#333" stroke-width="2"/><circle cx="271" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><circle cx="271" cy="35" r="4" fill="#333"/>
</svg>


### Facet

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 337 60" width="337" height="60">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">facet</text>
  <circle cx="20" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><line x1="28" y1="35" x2="40" y2="35" stroke="#333" stroke-width="2"/><rect x="40" y="20" width="47" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="63" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">  .</text><line x1="87" y1="35" x2="102" y2="35" stroke="#333" stroke-width="2"/><rect x="102" y="20" width="110" height="30" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="157" y="40" text-anchor="middle" font-family="sans-serif" font-size="14" font-style="italic" fill="#333">facet_name</text><line x1="212" y1="35" x2="227" y2="35" stroke="#333" stroke-width="2"/><rect x="227" y="20" width="65" height="30" rx="0" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="259" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">claim</text><path d="M292,35 Q307,35 307,55 L212,55 Q212,35 227,35" fill="none" stroke="#333" stroke-width="2" marker-start="url(#arrow)"/><line x1="292" y1="35" x2="307" y2="35" stroke="#333" stroke-width="2"/><circle cx="315" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><circle cx="315" cy="35" r="4" fill="#333"/>
</svg>


### Claim

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 692 60" width="692" height="60">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">claim</text>
  <circle cx="20" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><line x1="28" y1="35" x2="40" y2="35" stroke="#333" stroke-width="2"/><rect x="40" y="20" width="65" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="72" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">    -</text><line x1="105" y1="35" x2="120" y2="35" stroke="#333" stroke-width="2"/><rect x="120" y="20" width="110" height="30" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="175" y="40" text-anchor="middle" font-family="sans-serif" font-size="14" font-style="italic" fill="#333">claim_body</text><line x1="230" y1="35" x2="245" y2="35" stroke="#333" stroke-width="2"/><path d="M245,35 Q245,10 265,10 L364,10 Q384,10 384,35" fill="none" stroke="#333" stroke-width="2"/><rect x="245" y="20" width="119" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="304" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">| condition</text><line x1="384" y1="35" x2="399" y2="35" stroke="#333" stroke-width="2"/><path d="M399,35 Q399,10 419,10 L482,10 Q502,10 502,35" fill="none" stroke="#333" stroke-width="2"/><rect x="399" y="20" width="83" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="440" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">@source</text><line x1="502" y1="35" x2="517" y2="35" stroke="#333" stroke-width="2"/><path d="M517,35 Q517,10 537,10 L627,10 Q647,10 647,35" fill="none" stroke="#333" stroke-width="2"/><rect x="517" y="20" width="110" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="572" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">&amp;reference</text><line x1="647" y1="35" x2="662" y2="35" stroke="#333" stroke-width="2"/><circle cx="670" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><circle cx="670" cy="35" r="4" fill="#333"/>
</svg>


### Brief Form

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 369 160" width="369" height="160">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">brief_form</text>
  <circle cx="20" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><line x1="28" y1="35" x2="40" y2="35" stroke="#333" stroke-width="2"/><rect x="40" y="20" width="83" height="30" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="81" y="40" text-anchor="middle" font-family="sans-serif" font-size="14" font-style="italic" fill="#333">operand</text><line x1="123" y1="35" x2="138" y2="35" stroke="#333" stroke-width="2"/><path d="M138,35 Q148,-25 158,-25" fill="none" stroke="#333" stroke-width="2"/><rect x="158" y="-40" width="38" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="177" y="-20" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">=&gt;</text><path d="M196,-25 Q206,-25 216,35" fill="none" stroke="#333" stroke-width="2"/><path d="M138,35 Q148,5 158,5" fill="none" stroke="#333" stroke-width="2"/><rect x="158" y="-10" width="38" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="177" y="10" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">&lt;=</text><path d="M196,5 Q206,5 216,35" fill="none" stroke="#333" stroke-width="2"/><rect x="158" y="20" width="38" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="177" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">&lt;&gt;</text><path d="M138,35 Q148,65 158,65" fill="none" stroke="#333" stroke-width="2"/><rect x="158" y="50" width="38" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="177" y="70" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">&gt;&lt;</text><path d="M196,65 Q206,65 216,35" fill="none" stroke="#333" stroke-width="2"/><line x1="226" y1="35" x2="241" y2="35" stroke="#333" stroke-width="2"/><rect x="241" y="20" width="83" height="30" fill="#fff4e8" stroke="#333" stroke-width="2"/><text x="282" y="40" text-anchor="middle" font-family="sans-serif" font-size="14" font-style="italic" fill="#333">operand</text><line x1="324" y1="35" x2="339" y2="35" stroke="#333" stroke-width="2"/><circle cx="347" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><circle cx="347" cy="35" r="4" fill="#333"/>
</svg>


### Modifier

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 164 190" width="164" height="190">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
  <text x="10" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#666">modifier</text>
  <circle cx="20" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><line x1="28" y1="35" x2="40" y2="35" stroke="#333" stroke-width="2"/><path d="M40,35 Q50,-25 60,-25" fill="none" stroke="#333" stroke-width="2"/><rect x="60" y="-40" width="29" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="74" y="-20" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">^</text><path d="M89,-25 Q99,-25 109,35" fill="none" stroke="#333" stroke-width="2"/><path d="M40,35 Q50,5 60,5" fill="none" stroke="#333" stroke-width="2"/><rect x="60" y="-10" width="29" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="74" y="10" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">v</text><path d="M89,5 Q99,5 109,35" fill="none" stroke="#333" stroke-width="2"/><rect x="60" y="20" width="29" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="74" y="40" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">!</text><path d="M40,35 Q50,65 60,65" fill="none" stroke="#333" stroke-width="2"/><rect x="60" y="50" width="29" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="74" y="70" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">?</text><path d="M89,65 Q99,65 109,35" fill="none" stroke="#333" stroke-width="2"/><path d="M40,35 Q50,95 60,95" fill="none" stroke="#333" stroke-width="2"/><rect x="60" y="80" width="29" height="30" rx="15" fill="#e8f4e8" stroke="#333" stroke-width="2"/><text x="74" y="100" text-anchor="middle" font-family="monospace" font-size="14" fill="#333">*</text><path d="M89,95 Q99,95 109,35" fill="none" stroke="#333" stroke-width="2"/><line x1="119" y1="35" x2="134" y2="35" stroke="#333" stroke-width="2"/><circle cx="142" cy="35" r="8" fill="none" stroke="#333" stroke-width="2"/><circle cx="142" cy="35" r="4" fill="#333"/>
</svg>


<!-- END GENERATED SYNTAX DIAGRAMS -->

## Tools

This repository includes a complete toolchain for working with Worldview documents:

### Validator (`worldview-validate`)

Validates `.wvf` files for syntactic correctness.

```bash
# Validate a file
worldview-validate example.wvf

# Validate from stdin
cat example.wvf | worldview-validate --stdin
```

### Agent CLI (`worldview`)

An AI-powered tool that converts plain-text statements into proper Worldview notation.

```bash
# Add a fact to a Worldview file
worldview "Trust is built slowly through consistent actions" --file worldview.wvf

# Use a specific model
worldview "Power corrupts when unchecked" --model claude-opus-4-5-20251101
```

The agent understands the full Worldview specification and will:
1. Read existing content to understand structure
2. Determine appropriate concept/facet placement
3. Format statements using proper notation
4. Validate before writing

### Evaluation Framework

A Python framework for testing how well LLMs can leverage Worldview-encoded beliefs.

```bash
# Install dependencies
pip install -r evals/requirements.txt

# Run evaluations
python -m evals run --models claude-sonnet gpt-5.2

# Run specific difficulty
python -m evals run --difficulty extreme

# List available models and test cases
python -m evals list-models
python -m evals list-cases
```

## Project Structure

```
worldview/
├── agent/                 # Rust agent CLI
│   └── src/main.rs        # Agent implementation with embedded spec
├── validator/             # Rust validator
│   ├── src/lib.rs         # Validation library
│   └── src/main.rs        # CLI tool
├── evals/                 # Python evaluation framework
│   ├── cli.py             # Evaluation CLI
│   ├── runner.py          # Test orchestration
│   ├── evaluator.py       # Response scoring
│   ├── test_cases.py      # Test case definitions
│   ├── worldview_prompt.py # System prompts
│   └── llm_clients.py     # LLM provider clients
├── SPEC.md                # Full format specification
├── system.md              # Condensed system prompt
└── example.wvf            # Example document
```

## Building

### Prerequisites

- Rust 1.70+
- Python 3.11+

### Build Tools

```bash
# Build validator
cd validator && cargo build --release

# Build agent (requires setup for vendored dependencies)
cd agent && ./setup.sh && cargo build --release
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
