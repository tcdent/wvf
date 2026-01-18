//! WSL Validator - A validator for Worldview State Language files
//!
//! This crate provides validation for `.wsl` files according to the WSL specification.
//! It checks structural correctness (hierarchy, indentation) and claim syntax.

use std::fmt;
use thiserror::Error;

/// Errors that can occur during WSL validation
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum ValidationError {
    #[error("line {line}: invalid indentation (expected {expected} spaces, found {found})")]
    InvalidIndentation {
        line: usize,
        expected: &'static str,
        found: usize,
    },

    #[error("line {line}: facet must have '.' prefix")]
    MissingFacetPrefix { line: usize },

    #[error("line {line}: claim must have '-' prefix")]
    MissingClaimPrefix { line: usize },

    #[error("line {line}: concept '{concept}' has no facets")]
    ConceptWithoutFacets { line: usize, concept: String },

    #[error("line {line}: facet '{facet}' has no claims")]
    FacetWithoutClaims { line: usize, facet: String },

    #[error("line {line}: orphan facet (no preceding concept)")]
    OrphanFacet { line: usize },

    #[error("line {line}: orphan claim (no preceding facet)")]
    OrphanClaim { line: usize },

    #[error("line {line}: empty claim text")]
    EmptyClaimText { line: usize },

    #[error("line {line}: invalid claim syntax - conditions must come before sources")]
    ConditionAfterSource { line: usize },

    #[error("line {line}: invalid claim syntax - conditions must come before references")]
    ConditionAfterReference { line: usize },

    #[error("line {line}: invalid claim syntax - sources must come before references")]
    SourceAfterReference { line: usize },

    #[error("line {line}: invalid reference format '{reference}' (expected &Concept.facet)")]
    InvalidReferenceFormat { line: usize, reference: String },

    #[error("line {line}: empty condition (standalone '|')")]
    EmptyCondition { line: usize },

    #[error("line {line}: empty source (standalone '@')")]
    EmptySource { line: usize },

    #[error("line {line}: empty reference (standalone '&')")]
    EmptyReference { line: usize },

    #[error("line {line}: unexpected indentation level ({found} spaces)")]
    UnexpectedIndentation { line: usize, found: usize },

    #[error("line {line}: concept name cannot be empty")]
    EmptyConceptName { line: usize },

    #[error("line {line}: facet name cannot be empty")]
    EmptyFacetName { line: usize },
}

/// The type of a parsed line
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LineType {
    /// Empty line or whitespace only
    Blank,
    /// A concept (unindented text)
    Concept(String),
    /// A facet (2-space indent, '.' prefix)
    Facet(String),
    /// A claim (4-space indent, '-' prefix)
    Claim(ClaimData),
}

/// Parsed claim data
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimData {
    pub text: String,
    pub conditions: Vec<String>,
    pub sources: Vec<String>,
    pub references: Vec<String>,
}

/// A parsed line with its metadata
#[derive(Debug, Clone)]
pub struct ParsedLine {
    pub line_number: usize,
    pub line_type: LineType,
    pub raw: String,
}

/// Result of validation
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub errors: Vec<ValidationError>,
    pub lines: Vec<ParsedLine>,
}

impl ValidationResult {
    pub fn is_valid(&self) -> bool {
        self.errors.is_empty()
    }
}

impl fmt::Display for ValidationResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.is_valid() {
            write!(f, "Valid WSL document")
        } else {
            writeln!(f, "Invalid WSL document ({} errors):", self.errors.len())?;
            for error in &self.errors {
                writeln!(f, "  {}", error)?;
            }
            Ok(())
        }
    }
}

/// Validates a WSL document
pub fn validate(input: &str) -> ValidationResult {
    let mut errors = Vec::new();
    let mut lines = Vec::new();

    // First pass: tokenize lines
    for (idx, raw_line) in input.lines().enumerate() {
        let line_number = idx + 1;
        let parsed = tokenize_line(raw_line, line_number, &mut errors);
        lines.push(ParsedLine {
            line_number,
            line_type: parsed,
            raw: raw_line.to_string(),
        });
    }

    // Second pass: validate structure
    validate_structure(&lines, &mut errors);

    // Third pass: validate claim syntax
    for line in &lines {
        if let LineType::Claim(claim) = &line.line_type {
            validate_claim_syntax(line.line_number, claim, &mut errors);
        }
    }

    ValidationResult { errors, lines }
}

/// Count leading spaces
fn count_leading_spaces(line: &str) -> usize {
    line.chars().take_while(|c| *c == ' ').count()
}

/// Tokenize a single line
fn tokenize_line(line: &str, line_number: usize, errors: &mut Vec<ValidationError>) -> LineType {
    // Blank lines
    if line.trim().is_empty() {
        return LineType::Blank;
    }

    let indent = count_leading_spaces(line);
    let content = line.trim();

    match indent {
        0 => {
            // Concept: no indent, bare text
            if content.is_empty() {
                errors.push(ValidationError::EmptyConceptName { line: line_number });
                LineType::Blank
            } else {
                LineType::Concept(content.to_string())
            }
        }
        2 => {
            // Facet: 2-space indent, '.' prefix
            if !content.starts_with('.') {
                errors.push(ValidationError::MissingFacetPrefix { line: line_number });
                LineType::Blank
            } else {
                let name = content[1..].trim();
                if name.is_empty() {
                    errors.push(ValidationError::EmptyFacetName { line: line_number });
                }
                LineType::Facet(name.to_string())
            }
        }
        4 => {
            // Claim: 4-space indent, '-' prefix
            if !content.starts_with('-') {
                errors.push(ValidationError::MissingClaimPrefix { line: line_number });
                LineType::Blank
            } else {
                let claim_text = content[1..].trim();
                let claim_data = parse_claim(claim_text);
                LineType::Claim(claim_data)
            }
        }
        _ => {
            // Invalid indentation
            if indent == 1 || indent == 3 {
                errors.push(ValidationError::InvalidIndentation {
                    line: line_number,
                    expected: "0, 2, or 4",
                    found: indent,
                });
            } else {
                errors.push(ValidationError::UnexpectedIndentation {
                    line: line_number,
                    found: indent,
                });
            }
            LineType::Blank
        }
    }
}

/// Parse claim content into structured data
fn parse_claim(text: &str) -> ClaimData {
    let mut claim_text = String::new();
    let mut conditions = Vec::new();
    let mut sources = Vec::new();
    let mut references = Vec::new();

    // Split by spaces while preserving quoted segments and special markers
    let mut current_segment = String::new();
    let mut in_claim = true;
    let mut chars = text.chars().peekable();

    while let Some(c) = chars.next() {
        match c {
            '|' if in_claim || !current_segment.trim().is_empty() => {
                // Condition marker
                if in_claim {
                    claim_text = current_segment.trim().to_string();
                    in_claim = false;
                } else if !current_segment.trim().is_empty() {
                    // Previous segment was a condition
                    conditions.push(current_segment.trim().to_string());
                }
                current_segment = String::new();
            }
            '@' => {
                // Source marker
                if in_claim {
                    claim_text = current_segment.trim().to_string();
                    in_claim = false;
                } else if !current_segment.trim().is_empty() {
                    // Check if we're in middle of collecting conditions or sources
                    if conditions.is_empty() && sources.is_empty() && references.is_empty() {
                        // This is a condition that wasn't captured
                        conditions.push(current_segment.trim().to_string());
                    } else if !references.is_empty() {
                        // Already collecting references, this is wrong order
                        references.push(current_segment.trim().to_string());
                    } else if !sources.is_empty() {
                        sources.push(current_segment.trim().to_string());
                    } else {
                        conditions.push(current_segment.trim().to_string());
                    }
                }
                current_segment = String::new();
                // Collect source name
                while let Some(&next) = chars.peek() {
                    if next == ' ' || next == '|' || next == '@' || next == '&' {
                        break;
                    }
                    current_segment.push(chars.next().unwrap());
                }
                if !current_segment.trim().is_empty() {
                    sources.push(current_segment.trim().to_string());
                }
                current_segment = String::new();
            }
            '&' => {
                // Reference marker
                if in_claim {
                    claim_text = current_segment.trim().to_string();
                    in_claim = false;
                } else if !current_segment.trim().is_empty() {
                    if conditions.is_empty() && sources.is_empty() && references.is_empty() {
                        conditions.push(current_segment.trim().to_string());
                    } else if !sources.is_empty() {
                        // last source segment
                    } else {
                        conditions.push(current_segment.trim().to_string());
                    }
                }
                current_segment = String::new();
                // Collect reference
                while let Some(&next) = chars.peek() {
                    if next == ' ' || next == '|' || next == '@' || next == '&' {
                        break;
                    }
                    current_segment.push(chars.next().unwrap());
                }
                if !current_segment.trim().is_empty() {
                    references.push(current_segment.trim().to_string());
                }
                current_segment = String::new();
            }
            _ => {
                current_segment.push(c);
            }
        }
    }

    // Handle remaining segment
    if !current_segment.trim().is_empty() {
        if in_claim {
            claim_text = current_segment.trim().to_string();
        } else if !references.is_empty() {
            // Trailing text after reference
        } else if !sources.is_empty() {
            // Trailing text after source
        } else {
            conditions.push(current_segment.trim().to_string());
        }
    }

    ClaimData {
        text: claim_text,
        conditions,
        sources,
        references,
    }
}

/// Validate document structure
fn validate_structure(lines: &[ParsedLine], errors: &mut Vec<ValidationError>) {
    let mut current_concept: Option<(usize, String)> = None;
    let mut current_facet: Option<(usize, String)> = None;
    let mut concept_has_facet = false;
    let mut facet_has_claim = false;

    for line in lines {
        match &line.line_type {
            LineType::Blank => continue,
            LineType::Concept(name) => {
                // Check previous concept had facets
                if let Some((concept_line, concept_name)) = current_concept.take() {
                    if !concept_has_facet {
                        errors.push(ValidationError::ConceptWithoutFacets {
                            line: concept_line,
                            concept: concept_name,
                        });
                    }
                }
                // Check previous facet had claims
                if let Some((facet_line, facet_name)) = current_facet.take() {
                    if !facet_has_claim {
                        errors.push(ValidationError::FacetWithoutClaims {
                            line: facet_line,
                            facet: facet_name,
                        });
                    }
                }
                current_concept = Some((line.line_number, name.clone()));
                current_facet = None;
                concept_has_facet = false;
                facet_has_claim = false;
            }
            LineType::Facet(name) => {
                if current_concept.is_none() {
                    errors.push(ValidationError::OrphanFacet {
                        line: line.line_number,
                    });
                } else {
                    concept_has_facet = true;
                }
                // Check previous facet had claims
                if let Some((facet_line, facet_name)) = current_facet.take() {
                    if !facet_has_claim {
                        errors.push(ValidationError::FacetWithoutClaims {
                            line: facet_line,
                            facet: facet_name,
                        });
                    }
                }
                current_facet = Some((line.line_number, name.clone()));
                facet_has_claim = false;
            }
            LineType::Claim(_) => {
                if current_facet.is_none() {
                    errors.push(ValidationError::OrphanClaim {
                        line: line.line_number,
                    });
                } else {
                    facet_has_claim = true;
                }
            }
        }
    }

    // Check final concept and facet
    if let Some((concept_line, concept_name)) = current_concept {
        if !concept_has_facet {
            errors.push(ValidationError::ConceptWithoutFacets {
                line: concept_line,
                concept: concept_name,
            });
        }
    }
    if let Some((facet_line, facet_name)) = current_facet {
        if !facet_has_claim {
            errors.push(ValidationError::FacetWithoutClaims {
                line: facet_line,
                facet: facet_name,
            });
        }
    }
}

/// Validate claim syntax
fn validate_claim_syntax(line_number: usize, claim: &ClaimData, errors: &mut Vec<ValidationError>) {
    // Check for empty claim text
    if claim.text.is_empty() {
        errors.push(ValidationError::EmptyClaimText { line: line_number });
    }

    // Check for empty conditions
    for cond in &claim.conditions {
        if cond.is_empty() {
            errors.push(ValidationError::EmptyCondition { line: line_number });
        }
    }

    // Check for empty sources
    for src in &claim.sources {
        if src.is_empty() {
            errors.push(ValidationError::EmptySource { line: line_number });
        }
    }

    // Check for empty references
    for reference in &claim.references {
        if reference.is_empty() {
            errors.push(ValidationError::EmptyReference { line: line_number });
        }
    }

    // Validate reference format (should be Concept.facet)
    for reference in &claim.references {
        if !reference.is_empty() && !reference.contains('.') {
            errors.push(ValidationError::InvalidReferenceFormat {
                line: line_number,
                reference: reference.clone(),
            });
        }
    }
}

/// Validate a file by path
pub fn validate_file(path: &std::path::Path) -> Result<ValidationResult, std::io::Error> {
    let content = std::fs::read_to_string(path)?;
    Ok(validate(&content))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_minimal_document() {
        let input = r#"Power
  .core
    - corrupts | unchecked
    - reveals character"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid document: {:?}", result.errors);
    }

    #[test]
    fn test_concept_without_facet() {
        let input = "Power\nTrust";
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::ConceptWithoutFacets { .. })));
    }

    #[test]
    fn test_facet_without_claim() {
        let input = r#"Power
  .core"#;
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::FacetWithoutClaims { .. })));
    }

    #[test]
    fn test_orphan_facet() {
        let input = "  .core";
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::OrphanFacet { .. })));
    }

    #[test]
    fn test_orphan_claim() {
        let input = "    - corrupts";
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::OrphanClaim { .. })));
    }

    #[test]
    fn test_invalid_indentation() {
        let input = r#"Power
 .core"#;
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::InvalidIndentation { .. })));
    }

    #[test]
    fn test_claim_with_conditions_and_sources() {
        let input = r#"Trust
  .formation
    - requires consistency | over time @personal-experience"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                assert_eq!(claim.text, "requires consistency");
                assert!(claim.conditions.contains(&"over time".to_string()));
                assert!(claim.sources.contains(&"personal-experience".to_string()));
            }
        }
    }

    #[test]
    fn test_claim_with_reference() {
        let input = r#"Trust
  .erosion
    - asymmetric vs formation &Trust.formation"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                assert!(claim.references.contains(&"Trust.formation".to_string()));
            }
        }
    }

    #[test]
    fn test_expanded_document() {
        let input = r#"Power
  .nature
    - corrupts | unchecked !
    - reveals character => self-knowledge
    - concentration^ => abuse^ @historical-pattern
  .institutional
    - self-preserving
    - accountability <> trust &Trust.institutional
    - diffusion => dilution-of-responsibility

Trust
  .formation
    - slow
    - requires consistency | over time
    - contextual @personal-experience
  .erosion
    - fast !
    - single violation => collapse?
    - asymmetric vs formation &Trust.formation"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid document: {:?}", result.errors);
    }

    #[test]
    fn test_missing_facet_prefix() {
        let input = r#"Power
  core
    - corrupts"#;
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::MissingFacetPrefix { .. })));
    }

    #[test]
    fn test_missing_claim_prefix() {
        let input = r#"Power
  .core
    corrupts"#;
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::MissingClaimPrefix { .. })));
    }

    #[test]
    fn test_invalid_reference_format() {
        let input = r#"Power
  .core
    - corrupts &InvalidReference"#;
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::InvalidReferenceFormat { .. })));
    }

    #[test]
    fn test_blank_lines_allowed() {
        let input = r#"Power
  .core
    - corrupts

Trust
  .formation
    - slow"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);
    }
}
