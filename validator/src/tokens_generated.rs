// Auto-generated from spec/tokens.yaml
// Do not edit manually - run `python spec/generate.py rust`

/// Brief form operators defined in the Worldview spec
pub const BRIEF_FORMS: &[(&str, &str)] = &[
    ("=>", "causes, leads to"),
    ("<=", "caused by, results from"),
    ("<>", "mutual, bidirectional"),
    ("><", "tension, conflicts with"),
    ("~", "similar to, resembles"),
    ("=", "equivalent to, means"),
    ("vs", "in contrast to"),
    ("//", "regardless of"),
];

/// Modifier symbols defined in the Worldview spec
pub const MODIFIERS: &[(&str, &str)] = &[
    ("^", "increasing, trending up"),
    ("v", "decreasing, trending down"),
    ("!", "strong, emphatic, high confidence"),
    ("?", "uncertain, contested, tentative"),
    ("*", "notable, important, flagged"),
];

/// Inline element symbols
pub const CONDITION_SYMBOL: char = '|';
pub const SOURCE_SYMBOL: char = '@';
pub const REFERENCE_SYMBOL: char = '&';

/// Indentation levels (in spaces)
pub const CONCEPT_INDENT: usize = 0;
pub const FACET_INDENT: usize = 2;
pub const CLAIM_INDENT: usize = 4;

/// Element prefixes
pub const FACET_PREFIX: char = '.';
pub const CLAIM_PREFIX: char = '-';
