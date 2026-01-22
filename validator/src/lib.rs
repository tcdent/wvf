//! Worldview Validator - A validator for Worldview format files
//!
//! This crate provides validation for `.wvf` files according to the Worldview specification.
//! It checks structural correctness (hierarchy, indentation), claim syntax, brief forms,
//! modifiers, and evolution markers.

use std::collections::HashSet;
use std::fmt;
use thiserror::Error;

// Token definitions generated at compile time from spec/tokens.yaml
include!(concat!(env!("OUT_DIR"), "/tokens.rs"));

/// Errors that can occur during Worldview validation
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum ValidationError {
    // Structural errors
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

    #[error("line {line}: unexpected indentation level ({found} spaces)")]
    UnexpectedIndentation { line: usize, found: usize },

    #[error("line {line}: concept name cannot be empty")]
    EmptyConceptName { line: usize },

    #[error("line {line}: facet name cannot be empty")]
    EmptyFacetName { line: usize },

    // Inline element errors
    #[error("line {line}: invalid reference format '{reference}' (expected &Concept.facet)")]
    InvalidReferenceFormat { line: usize, reference: String },

    #[error("line {line}: undefined reference '{reference}' (no such concept.facet in document)")]
    UndefinedReference { line: usize, reference: String },

    #[error("line {line}: empty condition (standalone '|')")]
    EmptyCondition { line: usize },

    #[error("line {line}: empty source (standalone '@')")]
    EmptySource { line: usize },

    #[error("line {line}: empty reference (standalone '&')")]
    EmptyReference { line: usize },

    // Brief form errors
    #[error("line {line}: brief form '{operator}' missing left operand")]
    BriefFormMissingLeftOperand { line: usize, operator: String },

    #[error("line {line}: brief form '{operator}' missing right operand")]
    BriefFormMissingRightOperand { line: usize, operator: String },

    // Evolution marker errors
    #[error("line {line}: unclosed evolution marker '[<=' (missing ']')")]
    UnclosedEvolutionMarker { line: usize },

    #[error("line {line}: empty evolution marker '[<= ]' (no prior belief specified)")]
    EmptyEvolutionMarker { line: usize },

    #[error("line {line}: malformed evolution marker (expected '[<= prior belief]')")]
    MalformedEvolutionMarker { line: usize },

    // Modifier warnings (these are softer - might be intentional)
    #[error("line {line}: standalone modifier '{modifier}' may be unintentional")]
    StandaloneModifier { line: usize, modifier: String },
}

impl ValidationError {
    /// Returns true if this is a warning rather than a hard error
    pub fn is_warning(&self) -> bool {
        matches!(self, ValidationError::StandaloneModifier { .. })
    }
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
    pub brief_forms: Vec<BriefFormUsage>,
    pub modifiers: Vec<ModifierUsage>,
    pub evolution: Option<EvolutionMarker>,
}

/// A brief form operator found in a claim
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BriefFormUsage {
    pub operator: String,
    pub left_operand: String,
    pub right_operand: String,
}

/// A modifier found in a claim
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModifierUsage {
    pub symbol: char,
    pub attached_to: String,
}

/// An evolution marker [<= prior belief]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvolutionMarker {
    pub prior_belief: String,
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
    pub warnings: Vec<ValidationError>,
    pub lines: Vec<ParsedLine>,
}

impl ValidationResult {
    pub fn is_valid(&self) -> bool {
        self.errors.is_empty()
    }

    pub fn has_warnings(&self) -> bool {
        !self.warnings.is_empty()
    }
}

impl fmt::Display for ValidationResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.is_valid() && !self.has_warnings() {
            write!(f, "Valid Worldview document")
        } else if self.is_valid() {
            writeln!(f, "Valid Worldview document with {} warning(s):", self.warnings.len())?;
            for warning in &self.warnings {
                writeln!(f, "  {}", warning)?;
            }
            Ok(())
        } else {
            writeln!(f, "Invalid Worldview document ({} error(s)):", self.errors.len())?;
            for error in &self.errors {
                writeln!(f, "  {}", error)?;
            }
            if self.has_warnings() {
                writeln!(f, "Additionally, {} warning(s):", self.warnings.len())?;
                for warning in &self.warnings {
                    writeln!(f, "  {}", warning)?;
                }
            }
            Ok(())
        }
    }
}

/// Validates a Worldview document
pub fn validate(input: &str) -> ValidationResult {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();
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

    // Collect valid Concept.facet pairs for reference validation
    let valid_refs = collect_valid_references(&lines);

    // Second pass: validate structure
    validate_structure(&lines, &mut errors);

    // Third pass: validate claim syntax including brief forms, modifiers, evolution
    for line in &lines {
        if let LineType::Claim(claim) = &line.line_type {
            validate_claim_syntax(line.line_number, claim, &valid_refs, &mut errors, &mut warnings);
        }
    }

    ValidationResult { errors, warnings, lines }
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

    // First, extract evolution marker if present
    let (text_without_evolution, evolution) = extract_evolution_marker(text);
    let text = text_without_evolution.as_str();

    // Parse inline elements (|, @, &)
    let mut current_segment = String::new();
    let mut in_claim = true;
    let mut chars = text.chars().peekable();

    while let Some(c) = chars.next() {
        match c {
            '|' => {
                // Condition marker
                if in_claim {
                    claim_text = current_segment.trim().to_string();
                    in_claim = false;
                } else if !current_segment.trim().is_empty() {
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
                    conditions.push(current_segment.trim().to_string());
                }
                current_segment = String::new();
                // Collect source name (until space or another marker)
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
                    conditions.push(current_segment.trim().to_string());
                }
                current_segment = String::new();
                // Collect reference (until space or another marker)
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
        } else {
            conditions.push(current_segment.trim().to_string());
        }
    }

    // Extract brief forms from claim text
    let brief_forms = extract_brief_forms(&claim_text);

    // Extract modifiers from claim text
    let modifiers = extract_modifiers(&claim_text);

    ClaimData {
        text: claim_text,
        conditions,
        sources,
        references,
        brief_forms,
        modifiers,
        evolution,
    }
}

/// Extract evolution marker [<= prior belief] from text
fn extract_evolution_marker(text: &str) -> (String, Option<EvolutionMarker>) {
    if let Some(start) = text.find("[<=") {
        if let Some(end) = text[start..].find(']') {
            let marker_content = &text[start + 3..start + end];
            let prior_belief = marker_content.trim().to_string();
            let text_before = &text[..start];
            let text_after = &text[start + end + 1..];
            let cleaned = format!("{}{}", text_before.trim(), text_after.trim());
            return (
                cleaned,
                Some(EvolutionMarker { prior_belief }),
            );
        }
        // Unclosed marker - return as-is, validation will catch it
        return (text.to_string(), None);
    }
    (text.to_string(), None)
}

/// Extract brief form usages from claim text
fn extract_brief_forms(text: &str) -> Vec<BriefFormUsage> {
    let mut usages = Vec::new();

    // Check for each brief form operator
    // Order matters: check longer operators first to avoid partial matches
    let operators_by_length: &[&str] = &["=>", "<=", "<>", "><", "//", "vs", "~", "="];

    let remaining = text.to_string();

    for &op in operators_by_length {
        // Skip <= if it's part of [<= (evolution marker)
        if op == "<=" && remaining.contains("[<=") {
            continue;
        }

        // Special handling for = to avoid matching => or <=
        if op == "=" {
            // Look for standalone = not part of => or <=
            let mut i = 0;
            let chars: Vec<char> = remaining.chars().collect();
            while i < chars.len() {
                if chars[i] == '=' {
                    let prev = if i > 0 { Some(chars[i - 1]) } else { None };
                    let next = chars.get(i + 1);
                    // Check it's not part of =>, <=, or <>
                    if prev != Some('<') && prev != Some('>') && next != Some(&'>') {
                        // Found standalone =
                        let before: String = chars[..i].iter().collect();
                        let after: String = chars[i + 1..].iter().collect();
                        let left = before.split_whitespace().last().unwrap_or("").to_string();
                        let right = after.split_whitespace().next().unwrap_or("").to_string();
                        if !left.is_empty() || !right.is_empty() {
                            usages.push(BriefFormUsage {
                                operator: op.to_string(),
                                left_operand: left,
                                right_operand: right,
                            });
                        }
                    }
                }
                i += 1;
            }
            continue;
        }

        // For other operators
        for (idx, _) in remaining.match_indices(op) {
            let before = &remaining[..idx];
            let after = &remaining[idx + op.len()..];

            let left = before.split_whitespace().last().unwrap_or("").to_string();
            let right = after.split_whitespace().next().unwrap_or("").to_string();

            // Clean up modifiers from operands for matching
            let left_clean = left.trim_end_matches(|c| "^v!?*".contains(c));
            let right_clean = right.trim_end_matches(|c| "^v!?*".contains(c));

            usages.push(BriefFormUsage {
                operator: op.to_string(),
                left_operand: left_clean.to_string(),
                right_operand: right_clean.to_string(),
            });
        }
    }

    usages
}

/// Extract modifier usages from claim text
fn extract_modifiers(text: &str) -> Vec<ModifierUsage> {
    let mut usages = Vec::new();
    let modifier_chars = ['^', '!', '?', '*'];

    // Split into tokens
    let tokens: Vec<&str> = text.split_whitespace().collect();

    for (i, token) in tokens.iter().enumerate() {
        // Check for attached modifiers (e.g., "concentration^", "collapse?")
        for &m in &modifier_chars {
            if token.ends_with(m) && token.len() > 1 {
                let attached = token.trim_end_matches(m);
                usages.push(ModifierUsage {
                    symbol: m,
                    attached_to: attached.to_string(),
                });
            }
        }

        // Check for standalone modifiers (e.g., "fast !" where ! is separate token)
        // These modify the preceding term
        for &m in &modifier_chars {
            if token.len() == 1 && token.chars().next() == Some(m) && i > 0 {
                let prev = tokens[i - 1];
                // Don't count if previous token is an operator
                let is_after_operator = BRIEF_FORMS.iter().any(|(op, _)| prev.ends_with(op));
                if !is_after_operator {
                    usages.push(ModifierUsage {
                        symbol: m,
                        attached_to: prev.trim_end_matches(|c| "^!?*v".contains(c)).to_string(),
                    });
                }
            }
        }

        // Check for 'v' modifier - it's special because it's also a letter
        // It's a modifier when: standalone 'v' following a term
        if *token == "v" && i > 0 {
            let prev = tokens[i - 1];
            // Don't treat 'v' as modifier if previous token is an operator
            let is_after_operator = BRIEF_FORMS.iter().any(|(op, _)| prev.ends_with(op));
            if !is_after_operator {
                usages.push(ModifierUsage {
                    symbol: 'v',
                    attached_to: prev.trim_end_matches(|c| "^!?*".contains(c)).to_string(),
                });
            }
        }
    }

    usages
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

/// Collect all valid Concept.facet reference targets from the document
fn collect_valid_references(lines: &[ParsedLine]) -> HashSet<String> {
    let mut valid_refs = HashSet::new();
    let mut current_concept: Option<String> = None;

    for line in lines {
        match &line.line_type {
            LineType::Concept(name) => {
                current_concept = Some(name.clone());
            }
            LineType::Facet(name) => {
                if let Some(ref concept) = current_concept {
                    valid_refs.insert(format!("{}.{}", concept, name));
                }
            }
            _ => {}
        }
    }

    valid_refs
}

/// Validate claim syntax including brief forms, modifiers, and evolution markers
fn validate_claim_syntax(
    line_number: usize,
    claim: &ClaimData,
    valid_refs: &HashSet<String>,
    errors: &mut Vec<ValidationError>,
    warnings: &mut Vec<ValidationError>,
) {
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

    // Validate references point to existing concept.facet pairs
    for reference in &claim.references {
        if !reference.is_empty() && reference.contains('.') && !valid_refs.contains(reference) {
            errors.push(ValidationError::UndefinedReference {
                line: line_number,
                reference: reference.clone(),
            });
        }
    }

    // Validate brief forms have operands
    for bf in &claim.brief_forms {
        if bf.left_operand.is_empty() {
            errors.push(ValidationError::BriefFormMissingLeftOperand {
                line: line_number,
                operator: bf.operator.clone(),
            });
        }
        if bf.right_operand.is_empty() {
            errors.push(ValidationError::BriefFormMissingRightOperand {
                line: line_number,
                operator: bf.operator.clone(),
            });
        }
    }

    // Check for unclosed evolution markers in original text
    if claim.text.contains("[<=") && !claim.text.contains(']') {
        errors.push(ValidationError::UnclosedEvolutionMarker { line: line_number });
    }

    // Validate evolution marker content if present
    if let Some(ref evo) = claim.evolution {
        if evo.prior_belief.is_empty() {
            errors.push(ValidationError::EmptyEvolutionMarker { line: line_number });
        }
    }

    // Check for standalone modifiers that appear at the start (warning, not error)
    // Space-separated modifiers that follow a term are valid (e.g., "fast !")
    let tokens: Vec<&str> = claim.text.split_whitespace().collect();
    for (i, token) in tokens.iter().enumerate() {
        if *token == "^" || *token == "!" || *token == "?" || *token == "*" {
            // Only warn if it's at the start (no preceding term) or follows an operator
            if i == 0 {
                warnings.push(ValidationError::StandaloneModifier {
                    line: line_number,
                    modifier: token.to_string(),
                });
            } else {
                let prev = tokens[i - 1];
                let is_after_operator = BRIEF_FORMS.iter().any(|(op, _)| prev.ends_with(op));
                if is_after_operator {
                    warnings.push(ValidationError::StandaloneModifier {
                        line: line_number,
                        modifier: token.to_string(),
                    });
                }
            }
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

    // ==================== Structural tests ====================

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

    // ==================== Inline element tests ====================

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
  .formation
    - slow
  .erosion
    - asymmetric vs formation &Trust.formation"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        // Find the claim with the reference (second claim)
        let claims: Vec<_> = result.lines.iter()
            .filter_map(|l| match &l.line_type {
                LineType::Claim(c) => Some(c),
                _ => None,
            })
            .collect();
        
        assert!(claims.len() >= 2);
        assert!(claims[1].references.contains(&"Trust.formation".to_string()));
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
    fn test_undefined_reference() {
        let input = r#"Power
  .core
    - corrupts &Trust.formation"#;
        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::UndefinedReference { .. })));
    }

    #[test]
    fn test_valid_cross_reference() {
        // References between different concepts should work
        let input = r#"Power
  .institutional
    - accountability <> trust &Trust.institutional

Trust
  .institutional
    - possible | high transparency"#;
        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);
    }

    // ==================== Brief form tests ====================

    #[test]
    fn test_brief_form_causes() {
        let input = r#"Power
  .nature
    - power => corruption"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                assert!(!claim.brief_forms.is_empty());
                let bf = &claim.brief_forms[0];
                assert_eq!(bf.operator, "=>");
                assert_eq!(bf.left_operand, "power");
                assert_eq!(bf.right_operand, "corruption");
            }
        }
    }

    #[test]
    fn test_brief_form_caused_by() {
        let input = r#"Trust
  .formation
    - trust <= consistency"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let bf = claim.brief_forms.iter().find(|b| b.operator == "<=");
                assert!(bf.is_some(), "Expected <= operator");
            }
        }
    }

    #[test]
    fn test_brief_form_mutual() {
        let input = r#"Trust
  .institutional
    - accountability <> trust"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let bf = claim.brief_forms.iter().find(|b| b.operator == "<>");
                assert!(bf.is_some(), "Expected <> operator");
            }
        }
    }

    #[test]
    fn test_brief_form_tension() {
        let input = r#"Work
  .balance
    - efficiency >< thoroughness"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let bf = claim.brief_forms.iter().find(|b| b.operator == "><");
                assert!(bf.is_some(), "Expected >< operator");
            }
        }
    }

    #[test]
    fn test_brief_form_similar() {
        let input = r#"Authority
  .types
    - formal-authority ~ informal-influence"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let bf = claim.brief_forms.iter().find(|b| b.operator == "~");
                assert!(bf.is_some(), "Expected ~ operator");
            }
        }
    }

    #[test]
    fn test_brief_form_contrast() {
        let input = r#"Trust
  .erosion
    - asymmetric vs formation"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let bf = claim.brief_forms.iter().find(|b| b.operator == "vs");
                assert!(bf.is_some(), "Expected vs operator");
            }
        }
    }

    #[test]
    fn test_brief_form_regardless() {
        let input = r#"Institutions
  .dysfunction
    - self-perpetuate // original purpose"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let bf = claim.brief_forms.iter().find(|b| b.operator == "//");
                assert!(bf.is_some(), "Expected // operator");
            }
        }
    }

    #[test]
    fn test_brief_form_missing_left_operand() {
        let input = r#"Power
  .core
    - => corruption"#;

        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::BriefFormMissingLeftOperand { .. })));
    }

    #[test]
    fn test_brief_form_missing_right_operand() {
        let input = r#"Power
  .core
    - power =>"#;

        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::BriefFormMissingRightOperand { .. })));
    }

    // ==================== Modifier tests ====================

    #[test]
    fn test_modifier_increasing() {
        let input = r#"Power
  .nature
    - concentration^ => abuse"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let m = claim.modifiers.iter().find(|m| m.symbol == '^');
                assert!(m.is_some(), "Expected ^ modifier");
                assert_eq!(m.unwrap().attached_to, "concentration");
            }
        }
    }

    #[test]
    fn test_modifier_decreasing() {
        let input = r#"Trust
  .trends
    - institutional-trust v | recent decades"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let m = claim.modifiers.iter().find(|m| m.symbol == 'v');
                assert!(m.is_some(), "Expected v modifier");
            }
        }
    }

    #[test]
    fn test_modifier_emphatic() {
        let input = r#"Trust
  .erosion
    - fast !"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let m = claim.modifiers.iter().find(|m| m.symbol == '!');
                assert!(m.is_some(), "Expected ! modifier");
            }
        }
    }

    #[test]
    fn test_modifier_uncertain() {
        let input = r#"Philosophy
  .questions
    - free-will? @philosophy"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let m = claim.modifiers.iter().find(|m| m.symbol == '?');
                assert!(m.is_some(), "Expected ? modifier");
                assert_eq!(m.unwrap().attached_to, "free-will");
            }
        }
    }

    #[test]
    fn test_modifier_notable() {
        let input = r#"Change
  .types
    - paradigm-shift* | in progress"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                let m = claim.modifiers.iter().find(|m| m.symbol == '*');
                assert!(m.is_some(), "Expected * modifier");
            }
        }
    }

    #[test]
    fn test_standalone_modifier_warning() {
        // Modifier at start of claim (no preceding term) should warn
        let input = r#"Power
  .core
    - ^ something"#;

        let result = validate(input);
        // Should be valid but with warning
        assert!(result.is_valid());
        assert!(result.has_warnings());
        assert!(result.warnings.iter().any(|e| matches!(e, ValidationError::StandaloneModifier { .. })));
    }

    #[test]
    fn test_space_separated_modifier_valid() {
        // Space-separated modifier following a term is valid (no warning)
        let input = r#"Power
  .core
    - something ^"#;

        let result = validate(input);
        assert!(result.is_valid());
        // This should NOT produce a warning because ^ follows "something"
        assert!(!result.has_warnings(), "Expected no warnings: {:?}", result.warnings);
    }

    // ==================== Evolution marker tests ====================

    #[test]
    fn test_evolution_marker() {
        let input = r#"Human-nature
  .cognition
    - adaptive, context-dependent [<= inherently good]"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                assert!(claim.evolution.is_some(), "Expected evolution marker");
                assert_eq!(claim.evolution.as_ref().unwrap().prior_belief, "inherently good");
            }
        }
    }

    #[test]
    fn test_evolution_marker_rationalizes() {
        let input = r#"Human-nature
  .cognition
    - rationalizes post-hoc [<= rational actor]"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid: {:?}", result.errors);

        if let Some(line) = result.lines.iter().find(|l| matches!(l.line_type, LineType::Claim(_))) {
            if let LineType::Claim(claim) = &line.line_type {
                assert!(claim.evolution.is_some());
                assert_eq!(claim.evolution.as_ref().unwrap().prior_belief, "rational actor");
            }
        }
    }

    #[test]
    fn test_unclosed_evolution_marker() {
        let input = r#"Human-nature
  .cognition
    - adaptive [<= inherently good"#;

        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::UnclosedEvolutionMarker { .. })));
    }

    #[test]
    fn test_empty_evolution_marker() {
        let input = r#"Human-nature
  .cognition
    - adaptive [<= ]"#;

        let result = validate(input);
        assert!(!result.is_valid());
        assert!(result.errors.iter().any(|e| matches!(e, ValidationError::EmptyEvolutionMarker { .. })));
    }

    // ==================== Full document tests ====================

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
    - self-perpetuate // original purpose
    - capture-by-interests^ @public-choice-theory"#;

        let result = validate(input);
        assert!(result.is_valid(), "Expected valid document: {:?}", result.errors);
    }
}
