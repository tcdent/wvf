//! Worldview Agent CLI - A tool for adding facts to Worldview files using an AI agent
//!
//! This CLI accepts plain-text facts and uses an AI agent to properly format
//! and incorporate them into a Worldview format (.wvf) file.

use anyhow::Result;
use clap::Parser;
use codey::{Agent, AgentRuntimeConfig, AgentStep, RequestMode, SimpleTool, ToolRegistry};
use serde_json::json;
use std::path::PathBuf;
use std::sync::Arc;

/// The Worldview format specification (loaded from SPEC.md at compile time)
const SPEC: &str = include_str!("../../SPEC.md");

/// Task instructions for the agent
const TASK_INSTRUCTIONS: &str = r#"
# Your Task

When given a plain-text fact or statement:
1. First, read the current Worldview file to understand its structure and existing concepts
2. Determine if this fact belongs to an existing concept/facet or requires a new one
3. Format the fact as proper Worldview notation following the specification above
4. Use the edit_worldview tool to add or modify the appropriate line(s)
5. After editing, briefly confirm what you added

## Critical: Encode Only What Is Stated

The Worldview file stores information the user explicitly provides for later reference. You must:

- **Only encode information explicitly stated** in the user's fact or statement
- **Never add supplementary knowledge** from your training data (e.g., if told "gravity pulls objects toward Earth", do NOT add acceleration values, formulas, or other physics facts you know)
- **Never add assumptions or inferences** beyond what was directly stated
- **Be token-efficient** — the model already has general knowledge; we only need to store what the user specifically wants to remember

The purpose is to capture the user's specific framing and claims, not to build a comprehensive knowledge base. General facts already exist in model weights and don't need to be stored.

## Critical: Reject Ephemeral Events

The Worldview format is designed to store **durable beliefs, values, perspectives, and knowledge** — not transient events or one-time occurrences. You must:

- **Reject ephemeral personal events** like "I went to the park on Sunday" or "I had coffee this morning"
- **Reject time-bound occurrences** that describe what happened rather than what the user believes or values
- **Accept beliefs about events** like "parks are good for mental health" or "Sunday routines matter"

If given an ephemeral event, respond politely explaining that the Worldview format is for beliefs and perspectives, not personal diary entries, and do NOT modify the file.

Remember the design principles: state over narrative, predictability allows omission, conflict tolerance, freeform vocabulary, and LLM-native density.
"#;

/// Build the complete system prompt from spec + task instructions
fn build_system_prompt() -> String {
    format!(
        "You are a Worldview format agent. Your task is to take plain-text facts or statements and incorporate them into a Worldview file using the proper notation.\n\n\
        Below is the complete Worldview format specification. Study it carefully before making any edits.\n\n\
        ---\n\n\
        {}\n\n\
        ---\n\n\
        {}",
        SPEC, TASK_INSTRUCTIONS
    )
}

/// CLI for adding facts to Worldview files using an AI agent
#[derive(Parser, Debug)]
#[command(name = "worldview")]
#[command(about = "Add facts to Worldview files using an AI agent")]
#[command(version)]
struct Cli {
    /// The fact or statement to add to the Worldview file
    #[arg(required = true)]
    fact: String,

    /// Path to the Worldview file to modify
    #[arg(short, long, default_value = "worldview.wvf")]
    file: PathBuf,

    /// Model to use (claude-sonnet-4-20250514 or claude-opus-4-5-20251101)
    #[arg(short, long, default_value = "claude-sonnet-4-20250514")]
    model: String,

    /// Enable verbose output
    #[arg(short, long)]
    verbose: bool,
}

/// Create the read_worldview tool definition
fn create_read_tool() -> SimpleTool {
    SimpleTool::new(
        "read_worldview",
        "Read the current contents of the Worldview file. Returns the file contents with line numbers prefixed (e.g., '   1│content'). Use read_worldview first before editing to see current state.",
        json!({
            "type": "object",
            "properties": {},
            "required": []
        }),
    )
}

/// Create the edit_worldview tool definition
fn create_edit_tool() -> SimpleTool {
    SimpleTool::new(
        "edit_worldview",
        r#"Apply search/replace edits to the Worldview file. Each edit specifies an old_string to find and a new_string to replace it with.

Rules:
- Each old_string must match exactly (including whitespace/indentation)
- Each old_string must appear exactly once in the file (include more context if ambiguous)
- To insert new content, use old_string to match an existing line and include it plus your new lines in new_string
- To delete content, use an empty new_string
- Multiple edits are applied sequentially

The tool validates the result against Worldview syntax rules before writing."#,
        json!({
            "type": "object",
            "properties": {
                "edits": {
                    "type": "array",
                    "description": "List of search/replace operations to apply sequentially",
                    "items": {
                        "type": "object",
                        "properties": {
                            "old_string": {
                                "type": "string",
                                "description": "Exact string to find (must be unique in file). Include full lines with proper indentation."
                            },
                            "new_string": {
                                "type": "string",
                                "description": "String to replace it with. Use empty string to delete."
                            }
                        },
                        "required": ["old_string", "new_string"]
                    }
                }
            },
            "required": ["edits"]
        }),
    )
}

/// Handle the read_worldview tool call
fn handle_read_worldview(file_path: &PathBuf) -> String {
    if !file_path.exists() {
        return "File does not exist yet. Use edit_worldview with edits to create it.".to_string();
    }

    match std::fs::read_to_string(file_path) {
        Ok(content) => {
            // Return with line numbers in codey format
            content
                .lines()
                .enumerate()
                .map(|(i, line)| format!("{:4}│{}", i + 1, line))
                .collect::<Vec<_>>()
                .join("\n")
        }
        Err(e) => format!("Error reading file: {}", e),
    }
}

/// Handle the edit_worldview tool call
fn handle_edit_worldview(file_path: &PathBuf, params: &serde_json::Value) -> String {
    // Parse edits array
    let edits = match params.get("edits").and_then(|v| v.as_array()) {
        Some(arr) => arr,
        None => return "Error: 'edits' array is required".to_string(),
    };

    if edits.is_empty() {
        return "Error: 'edits' array cannot be empty".to_string();
    }

    // Read current file content (or start empty for new files)
    let mut content = if file_path.exists() {
        match std::fs::read_to_string(file_path) {
            Ok(c) => c,
            Err(e) => return format!("Error reading file: {}", e),
        }
    } else {
        String::new()
    };

    // Validate and apply each edit
    for (i, edit) in edits.iter().enumerate() {
        let old_string = match edit.get("old_string").and_then(|v| v.as_str()) {
            Some(s) => s,
            None => return format!("Edit {}: missing 'old_string'", i + 1),
        };
        let new_string = match edit.get("new_string").and_then(|v| v.as_str()) {
            Some(s) => s,
            None => return format!("Edit {}: missing 'new_string'", i + 1),
        };

        // For new files, old_string should be empty to append
        if content.is_empty() {
            if !old_string.is_empty() {
                return format!(
                    "Edit {}: file is empty, old_string must be empty to create new content",
                    i + 1
                );
            }
            content = new_string.to_string();
            continue;
        }

        // Check that old_string exists and is unique
        let count = content.matches(old_string).count();
        match count {
            0 => {
                return format!(
                    "Edit {}: old_string not found in file. \
                     Make sure the string matches exactly, including whitespace and indentation.",
                    i + 1
                );
            }
            1 => {} // good
            n => {
                return format!(
                    "Edit {}: old_string found {} times (must be unique). \
                     Include more surrounding context to make the match unique.",
                    i + 1,
                    n
                );
            }
        }

        // Apply the replacement
        content = content.replacen(old_string, new_string, 1);
    }

    // Ensure file ends with newline
    if !content.is_empty() && !content.ends_with('\n') {
        content.push('\n');
    }

    // Validate the new content before writing
    let validation = worldview_validator::validate(&content);

    if !validation.is_valid() {
        let errors: Vec<String> = validation.errors.iter().map(|e| e.to_string()).collect();
        return format!(
            "Validation failed - file not modified:\n{}",
            errors.join("\n")
        );
    }

    // Write the file
    if let Err(e) = std::fs::write(file_path, &content) {
        return format!("Error writing file: {}", e);
    }

    // Return success with edit count and any warnings
    let edit_count = edits.len();
    let base_msg = format!(
        "Successfully applied {} edit{}.",
        edit_count,
        if edit_count == 1 { "" } else { "s" }
    );

    if validation.has_warnings() {
        let warnings: Vec<String> = validation.warnings.iter().map(|w| w.to_string()).collect();
        format!("{} Warnings:\n{}", base_msg, warnings.join("\n"))
    } else {
        format!("{} File validated.", base_msg)
    }
}

/// Handle a tool call from the agent
fn handle_tool_call(file_path: &PathBuf, tool_name: &str, params: &serde_json::Value) -> String {
    match tool_name {
        "read_worldview" => handle_read_worldview(file_path),
        "edit_worldview" => handle_edit_worldview(file_path, params),
        _ => format!("Unknown tool: {}", tool_name),
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let start_time = std::time::Instant::now();

    // Check for API key
    if std::env::var("ANTHROPIC_API_KEY").is_err() {
        eprintln!("Error: ANTHROPIC_API_KEY environment variable not set");
        std::process::exit(1);
    }

    // Resolve the file path
    let file_path = if cli.file.is_absolute() {
        cli.file.clone()
    } else {
        std::env::current_dir()?.join(&cli.file)
    };

    if cli.verbose {
        eprintln!("[config] Worldview file: {:?}", file_path);
        eprintln!("[config] Model: {}", cli.model);
        eprintln!("[config] Fact: {}", cli.fact);
        eprintln!("[start] Beginning agent execution...");
    }

    // Create tool registry with our custom tools
    let mut registry = ToolRegistry::empty();
    registry.register(Arc::new(create_read_tool()));
    registry.register(Arc::new(create_edit_tool()));

    // Configure the agent
    let config = AgentRuntimeConfig {
        model: cli.model.clone(),
        max_tokens: 4096,
        thinking_budget: 1024,  // Minimum required
        max_retries: 3,
        compaction_thinking_budget: 2000,
    };

    // Create the agent with the dynamically built system prompt
    let system_prompt = build_system_prompt();
    let mut agent = Agent::new(
        config,
        &system_prompt,
        None, // Use ANTHROPIC_API_KEY env var
        registry,
    );

    // Format the user message
    let user_message = format!(
        "Please add this fact to the Worldview file at {:?}:\n\n{}",
        file_path, cli.fact
    );

    // Send the request
    agent.send_request(&user_message, RequestMode::Normal);

    // Process the agent loop
    let mut tool_call_count = 0;
    let mut thinking_started = false;

    while let Some(step) = agent.next().await {
        match step {
            AgentStep::TextDelta(text) => {
                print!("{}", text);
            }
            AgentStep::ThinkingDelta(thinking) => {
                if cli.verbose {
                    if !thinking_started {
                        thinking_started = true;
                        eprint!("\n[thinking] ");
                    }
                    eprint!("{}", thinking);
                }
            }
            AgentStep::CompactionDelta(_) => {
                // Not used in our simple case
            }
            AgentStep::ToolRequest(tool_calls) => {
                if cli.verbose && thinking_started {
                    eprintln!();  // End thinking block
                    thinking_started = false;
                }

                for call in tool_calls {
                    tool_call_count += 1;
                    let tool_start = std::time::Instant::now();

                    if cli.verbose {
                        // Format params nicely for readability
                        let params_str = if call.params.is_object() {
                            serde_json::to_string_pretty(&call.params).unwrap_or_else(|_| format!("{:?}", call.params))
                        } else {
                            format!("{:?}", call.params)
                        };
                        eprintln!("\n[tool:{}] {}", tool_call_count, call.name);
                        eprintln!("[params] {}", params_str);
                    }

                    let result = handle_tool_call(&file_path, &call.name, &call.params);

                    if cli.verbose {
                        let tool_elapsed = tool_start.elapsed();
                        eprintln!("[result:{}ms] {}", tool_elapsed.as_millis(), result);
                    }

                    agent.submit_tool_result(&call.call_id, result);
                }
            }
            AgentStep::Retrying { attempt, error } => {
                if cli.verbose {
                    eprintln!("[retry] Attempt {} after error: {}", attempt, error);
                }
            }
            AgentStep::Finished { usage } => {
                let total_elapsed = start_time.elapsed();
                if cli.verbose {
                    eprintln!("\n[done] Output: {}, Context: {}",
                        usage.output_tokens, usage.context_tokens);
                    eprintln!("[timing] Total: {}ms, Tool calls: {}",
                        total_elapsed.as_millis(), tool_call_count);
                }
                break;
            }
            AgentStep::Error(e) => {
                let total_elapsed = start_time.elapsed();
                if cli.verbose {
                    eprintln!("[error:{}ms] {}", total_elapsed.as_millis(), e);
                }
                eprintln!("\nError: {}", e);
                std::process::exit(1);
            }
        }
    }

    println!("\n\nWorldview file updated: {:?}", file_path);
    Ok(())
}
