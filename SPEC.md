# Worldview Format

**Specification v0.1 — Draft**

---

## Abstract

The Worldview format is a constrained notation for encoding conceptual worldviews. Its primary purpose is to provide a rigid structure that enforces what can and cannot be stored—the syntax itself prevents drift into inappropriate content types.

The format is not optimized for token efficiency as a primary goal; density is a *consequence* of the constraints. By requiring that all content fit into a strict hierarchy of Concepts, Facets, and Claims, the format naturally excludes narratives, logs, predictions, and other content that doesn't belong in a worldview document.

---

## Motivation

The problem Worldview solves is not context length—it's content discipline.

When beliefs and stances are stored in unstructured formats like Markdown, documents tend to grow with repetitious statements, narrative tangents, and content that strays from the intended purpose. There is no enforcement of what belongs versus what doesn't.

The Worldview format solves this through structural constraint:

1. **Every piece of information has a designated place** — Concepts organize by subject, Facets organize by aspect, Claims make assertions. If something doesn't fit this hierarchy, it doesn't belong.

2. **The syntax prevents duplication** — Because content is categorized into a clear hierarchy, there's always one canonical location for any given belief. Adding a duplicate requires navigating to the same place, making redundancy obvious.

3. **Inappropriate content is structurally excluded** — Predictions, evaluations, event logs, and narratives cannot be encoded in the Concept → Facet → Claim structure. The format only accepts statements of understanding.

Token efficiency is a side effect: when you can only store structured beliefs, documents stay focused and compact.

---

## Design Principles

**Structure as enforcement**
The rigid hierarchy of Concept → Facet → Claim is the primary mechanism for keeping documents focused. If content doesn't fit this structure, it doesn't belong.

**State over narrative**
The format captures what is believed, not the story of how it came to be believed. History is preserved compactly when relevant, but the primary representation is current state.

**Conflict tolerance**
Real worldviews contain tensions and contradictions. The format holds conflicting claims without forcing resolution.

**Minimal notation**
Symbols are used sparingly—only where they are universally intuitive (`=>`, `~`, `=`, `vs`). Less common relationships use natural language within claims.

**Freeform vocabulary**
No predefined concept names, facet labels, or claim terms. The notation defines structure; content remains unconstrained.

---

## Inspirations

### Belief Representation
The format draws on concepts from epistemology and knowledge representation:
- Beliefs as claims with conditions (contextualism)
- Sources as grounding for confidence (evidentialism)
- Tolerance of contradiction (paraconsistent approaches)

### Configuration Languages
The hierarchical structure echoes YAML and similar formats, using indentation for nesting while avoiding syntactic overhead like quotes and brackets.

### Constraint-Based Design
The format takes inspiration from systems where limitations enhance focus: structured data schemas, controlled vocabularies, and formats where the inability to express certain things is a feature rather than a limitation.

---

## LLM-Native Tokens

The notation deliberately uses symbols that LLMs already understand intuitively—tokens whose semantics are well-established in training data:

| Symbol | Why It Works |
|--------|--------------|
| `?` | Universally associated with uncertainty and questioning |
| `!` | Strongly associated with emphasis and assertion |
| `=>` | Arrow notation for causation is universal across programming and logic |
| `~` | Mathematical approximation; resemblance |
| `@` | Attribution and source reference (email, social media, programming) |
| `&` | Joining and linking semantics |
| `^` | Upward direction/increase (caret, superscript) |
| `v` | Downward direction/decrease (shaped like down arrow) |

This approach leverages semantic associations that already exist in model weights. When an LLM sees `collapse?`, it understands uncertainty without explicit instruction.

Critically, symbols that lack clear pre-existing semantics are avoided. If a relationship requires explanation to understand, natural language is clearer than a novel symbol. This is why the format uses only four brief form operators (`=>`, `~`, `=`, `vs`) rather than a larger set that would require learning new meanings.

---

## Structure

A Worldview document is a hierarchical collection of beliefs organized as:

```
Document
  └── Concept (one or more)
        └── Facet (one or more per concept)
              └── Claim (one or more per facet)
                    ├── Condition (zero or more)
                    └── Source (zero or more)
```

### Definitions

| Element | Description |
|---------|-------------|
| **Concept** | A subject of belief—a noun in the worldview (e.g., Power, Trust, Human nature) |
| **Facet** | An aspect or dimension of a concept (e.g., formation, erosion, institutional) |
| **Claim** | An assertion about a facet—what is believed to be true |
| **Condition** | Circumstances under which the claim applies |
| **Source** | Basis for the belief (observation, experience, citation, intuition) |

### Constraints

- Every concept must have at least one facet
- Every facet must have at least one claim
- Conditions and sources are optional per claim
- Facet names are freeform (no controlled vocabulary)
- Concepts may reference other concepts, creating a web of related beliefs

---

## Notation

### Hierarchy

| Element | Notation | Indentation |
|---------|----------|-------------|
| Concept | Bare text | None (column 0) |
| Facet | `.` prefix | 2 spaces |
| Claim | `-` prefix | 4 spaces |

### Inline Elements

| Element | Symbol | Position |
|---------|--------|----------|
| Condition | `\|` | After claim |
| Source | `@` | After claim/conditions |
| Reference | `&` | After claim, links to other concept.facet |

### Positional Grammar

Claims follow a consistent order:

```
- [claim] | [condition] | [condition] @[source] @[source] &[reference]
```

Position implies role—no labels needed:
1. Claim text (required)
2. Conditions (zero or more, `|` prefixed)
3. Sources (zero or more, `@` prefixed)
4. References (zero or more, `&` prefixed)

---

## Brief Forms

A minimal set of universally intuitive symbols for common relationships:

| Symbol | Meaning |
|--------|---------|
| `=>` | causes, leads to |
| `~` | similar to, resembles |
| `=` | equivalent to, means |
| `vs` | contrasts with, in tension with |

Less common relationships should use natural language within claims rather than forcing additional symbols.

### Examples

```
- power => corruption | unchecked
- formal-authority ~ informal-influence
- efficiency vs thoroughness
- mutual accountability with trust
```

---

## Modifiers

Suffix markers inflect claim meaning:

| Modifier | Meaning |
|----------|---------|
| `^` | increasing, trending up |
| `v` | decreasing, trending down |
| `!` | strong, emphatic, high confidence |
| `?` | uncertain, contested, tentative |
| `*` | notable, important, flagged |

### Examples

```
- institutional-trust v | recent decades
- free-will? @philosophy
- single violation => collapse !
- paradigm-shift* | in progress
```

---

## Evolution

Beliefs change. The Worldview format represents evolution through:

### Supersession Markers

Prior beliefs can be noted inline with `[<= prior belief]`:

```
- adaptive, context-dependent [<= inherently good]
```

This reads: "Currently believed to be adaptive and context-dependent; this supersedes a prior belief that it was inherently good."

### Implicit Evolution

When claims in the same facet track change over time, newer claims are listed first. The array order itself implies evolution without explicit markers.

---

## References

Claims can reference other concepts using `&Concept.facet`:

```
Trust
  .erosion
    - asymmetric to formation &Trust.formation
    - single violation => collapse &Human-nature.memory

Human-nature
  .memory
    - negative events more salient
    - loss-averse @behavioral-economics
```

References create a graph of related beliefs, enabling the LLM to traverse connections without duplicating content.

---

## Examples

### Minimal Document

```
Power
  .core
    - corrupts | unchecked
    - reveals character
```

### Expanded Document

```
Power
  .nature
    - corrupts | unchecked !
    - reveals character => self-knowledge
    - concentration^ => abuse^ @historical-pattern
  .institutional
    - self-preserving
    - mutual accountability with trust &Trust.institutional
    - diffusion => dilution-of-responsibility

Trust
  .formation
    - slow
    - requires consistency | over time
    - contextual @personal-experience
  .erosion
    - fast !
    - single violation => collapse?
    - asymmetric vs formation &Trust.formation
  .institutional
    - possible | high transparency
    - unlikely | low transparency
    - rational to withhold | unverifiable @game-theory

Human-nature
  .social
    - conformist | formal groups
    - authentic | solitary
    - status-aware @evolutionary-psychology
    - coalition-forming
  .cognition
    - pattern-seeking
    - confirmation-biased @cognitive-science
    - narrative-constructing
    - rationalizes post-hoc [<= rational actor]
  .self-perception
    - overconfident | familiar domains
    - miscalibrated @Dunning-Kruger
    - self-deception => comfort &Human-nature.cognition

Institutions
  .function
    - stabilize !
    - preserve knowledge
    - coordinate action @game-theory
  .dysfunction
    - ossify | over time
    - self-perpetuates despite original purpose
    - capture-by-interests^ @public-choice-theory
```

---

## Non-Goals

The format explicitly does not attempt to:

- **Prove logical consistency** — Contradictions are permitted
- **Enforce ontology** — No required categories or hierarchies beyond structure
- **Replace natural language** — The format is for belief state, not communication
- **Assert objective truth** — Claims represent understanding, not facts
- **Store predictions, evaluations, or identity** — These are derived from beliefs, not stored directly
- **Maximize symbol density** — Notation is minimal; natural language is preferred for uncommon relationships

---

## Intended Use Cases

- **Long-term LLM context anchoring** — Persistent worldview across sessions
- **Belief drift analysis** — Track how understanding evolves
- **Conceptual memory compression** — Dense storage of learned stances
- **Domain modeling** — Capture expert understanding of a field
- **Value alignment documentation** — Record interpretive frameworks

---

## Summary

The Worldview format is a constrained notation for meaning, not conversation. Its rigid structure enforces that only appropriate content is stored—the syntax itself prevents documents from drifting into narratives, logs, or other inappropriate content types.

The format encodes:
- **What** is believed (claims)
- **When** it applies (conditions)
- **Why** it's believed (sources)
- **How** beliefs connect (references)
- **That** beliefs change (evolution markers)

It structurally excludes:
- Narratives and prose
- Event logs and timelines
- Predictions and evaluations
- Duplicate information (hierarchy makes canonical location obvious)

The format's value is constraint: by limiting what can be expressed, it keeps documents focused on their intended purpose—a persistent lens through which all subsequent reasoning is filtered.
