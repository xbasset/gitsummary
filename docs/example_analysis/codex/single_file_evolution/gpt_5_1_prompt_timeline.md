# Timeline of Changes to `gpt_5_1_prompt.md`

This document traces the iterative evolution of the GPT-5.1 prompt file from its initial creation through subsequent refinements, analyzing the inferred intentions and goals behind each change.

## Overview

The file was created on **November 12, 2025** and has undergone **3 major updates** over the course of **7 days**, growing from ~310 lines to ~369 lines. The changes reflect an iterative refinement process focused on improving agent behavior, clarity of instructions, and operational efficiency.

---

## Commit 1: Initial Creation
**Date:** November 12, 2025, 12:44:36 -0800  
**Author:** pakrym-oai  
**Commit:** `ec69a4a8` - "Add gpt-5.1 model definitions (#6551)"  
**File Size:** ~310 lines

### Initial State
The file was created as a foundational prompt for the GPT-5.1 model running in the Codex CLI. The initial version established:

- **Identity**: "You are a coding agent running in the Codex CLI"
- **Core capabilities**: Receiving prompts, communicating via streaming, making function calls
- **Personality guidelines**: Concise, direct, friendly communication style
- **AGENTS.md specification**: Rules for handling repository-specific instructions
- **Responsiveness section**: "Preamble messages" guidance for tool call communication
- **Planning system**: Guidelines for using the `update_plan` tool
- **Task execution**: Instructions for autonomous problem-solving
- **Sandbox and approvals**: Configuration options for filesystem/network sandboxing
- **Validation**: Testing and formatting guidelines
- **Code formatting**: Detailed style guidelines for final answers

### Inferred Intent
This was the initial baseline prompt, likely adapted from an existing prompt template (possibly for a different model version). The goal was to establish comprehensive behavioral guidelines for GPT-5.1's operation within the Codex CLI environment.

---

## Commit 2: Major Behavioral Refinement
**Date:** November 13, 2025, 07:51:28 -0800  
**Author:** Dylan Hurd  
**Commit:** `8dcbd29e` - "chore(core) Update prompt for gpt-5.1 (#6588)"  
**Changes:** ~100+ lines modified/added

### Key Changes

#### 1. Identity Update
- **Change**: "You are a coding agent" → "You are GPT-5.1"
- **Intent**: More specific model identity, likely to reinforce model-specific behavior expectations

#### 2. New "Autonomy and Persistence" Section
- **Added**: Explicit instructions to persist until tasks are fully handled end-to-end
- **Added**: Guidance to assume user wants code changes unless explicitly asking questions/brainstorming
- **Intent**: Address agent behavior where it would stop at analysis instead of implementing solutions. This suggests early testing revealed agents were being too cautious or stopping prematurely.

#### 3. "Responsiveness" → "User Updates Spec" Restructure
- **Change**: Renamed and restructured the responsiveness section
- **Added**: Structured guidance on frequency, length, tone, and content of updates
- **Removed**: "Preamble messages" terminology (kept examples but reframed)
- **Intent**: Standardize communication patterns. The shift from "preamble" to "updates" suggests a move toward more continuous, contextual communication rather than pre-action announcements.

#### 4. Enhanced Planning Guidelines
- **Added**: "Maintain statuses in the tool: exactly one item in_progress at a time..."
- **Intent**: Address plan management issues where agents were batch-completing items or letting plans go stale. This suggests agents weren't properly maintaining plan state during execution.

#### 5. Task Execution Strengthening
- **Change**: "Please keep going" → "You must keep going"
- **Added**: "Persist until the task is fully handled end-to-end within the current turn whenever feasible and persevere even when function calls fail"
- **Intent**: Reinforce persistence. The addition of "persevere even when function calls fail" suggests agents were giving up too easily on errors.

#### 6. apply_patch Tool Clarification
- **Change**: Removed JSON wrapper example, clarified it's a FREEFORM tool
- **Intent**: Fix implementation errors where agents were incorrectly wrapping patches in JSON.

#### 7. Sandbox Section Restructuring
- **Change**: "Sandbox and approvals" → "Codex CLI harness, sandboxing, and approvals"
- **Restructured**: More systematic organization with clearer definitions
- **Added**: Explicit default assumptions when sandboxing info isn't provided
- **Added**: Specific guidance on when to request approval
- **Added**: Instructions for using `with_escalated_permissions` and `justification` parameters
- **Intent**: Improve clarity around sandboxing behavior. The restructuring suggests confusion about when/how to request approvals, and the addition of parameter guidance indicates agents weren't properly using the escalation mechanism.

#### 8. Validation Section Refinement
- **Change**: "verify that your work is complete" → "verify changes once your work is complete"
- **Added**: "If you are unable to run tests, you must still do your utmost best to complete the task"
- **Intent**: Clarify timing and add fallback guidance for constrained environments.

#### 9. Final Answer Formatting Enhancements
- **Added**: "Verbosity" section with strict compactness rules (enforced)
- **Added**: "code samples" to monospace formatting guidelines
- **Change**: "full contents of large files" → "contents of files"
- **Intent**: Address verbosity issues. The detailed verbosity rules suggest agents were producing overly long responses, especially for small changes.

#### 10. Shell Guidelines Addition
- **Added**: "The arguments to `shell` will be passed to execvp()"
- **Added**: "Always set the `workdir` param when using the shell function. Do not use `cd` unless absolutely necessary"
- **Intent**: Improve shell command execution. The `workdir` guidance suggests agents were using `cd` unnecessarily, which could cause issues in sandboxed environments.

#### 11. New apply_patch Documentation Section
- **Added**: Complete documentation of the patch format with examples
- **Intent**: Provide comprehensive reference. This suggests agents were making errors in patch format, requiring detailed documentation.

### Overall Intent of Commit 2
This was a **major behavioral refinement** based on early testing/usage. The changes address:
- **Persistence issues**: Agents stopping too early or giving up on errors
- **Communication patterns**: Standardizing update frequency and style
- **Tool usage errors**: Incorrect patch formatting, improper approval requests
- **Plan management**: Agents not maintaining plan state properly
- **Verbosity**: Responses too long for simple tasks
- **Clarity**: Better organization and explicit defaults

---

## Commit 3: Shell Instructions Cleanup
**Date:** November 17, 2025, 13:05:15 -0800  
**Author:** Dylan Hurd  
**Commit:** `daf77b84` - "chore(core) Update shell instructions (#6679)"  
**Changes:** 2 lines removed

### Key Changes

#### Removed Shell Guidelines
- **Removed**: "The arguments to `shell` will be passed to execvp()"
- **Removed**: "Always set the `workdir` param when using the shell function. Do not use `cd` unless absolutely necessary"

### Inferred Intent
This appears to be a **rollback or simplification**. Possible reasons:
1. **Tool implementation changed**: The `workdir` parameter may no longer be available or required
2. **Over-specification**: The guidance may have been too prescriptive or causing confusion
3. **Redundancy**: This information may have been moved elsewhere or is now handled automatically
4. **Testing feedback**: The guidance may have led to incorrect usage patterns

The removal suggests these instructions were either incorrect, no longer applicable, or causing more problems than they solved.

---

## Commit 4: Parallelization Guidelines
**Date:** November 19, 2025, 17:04:05 +0000  
**Author:** jif-oai  
**Commit:** `b436bbb4` - "Prompts update"  
**Changes:** ~13 lines added

### Key Changes

#### New "Exploration and reading files" Section
- **Added**: Comprehensive guidelines for parallelizing file operations
- **Key principles**:
  - Think first, decide ALL files needed before any tool call
  - Batch everything - read multiple files together
  - Use `multi_tool_use.parallel` exclusively for parallelization
  - Only make sequential calls if truly unpredictable
  - Workflow: plan → parallel batch → analyze → repeat

- **Additional notes**:
  - Always maximize parallelism
  - Never read files one-by-one unless logically unavoidable
  - Applies to all read/list/search operations
  - Do not try to parallelize using scripting

### Inferred Intent
This addresses a **performance and efficiency issue**. The addition suggests:
- **Observation**: Agents were reading files sequentially even when parallel reads were possible
- **Impact**: This was causing slow performance and unnecessary latency
- **Solution**: Explicit, prescriptive guidance to maximize parallelization
- **Enforcement**: Strong language ("Always", "Never", "exclusively") indicates this was a significant problem

The timing (5 days after the major update) suggests this was identified through usage monitoring or user feedback about slow agent performance.

---

## Evolution Patterns

### 1. **From Generic to Specific**
- Identity: "coding agent" → "GPT-5.1"
- Instructions: General guidance → Specific, enforceable rules

### 2. **From Permissive to Prescriptive**
- Early: "Please keep going" → Later: "You must keep going"
- Early: General guidance → Later: Detailed verbosity rules with line counts

### 3. **From Reactive to Proactive**
- Added autonomy section encouraging implementation over analysis
- Added persistence requirements even when function calls fail

### 4. **From Implicit to Explicit**
- Added default assumptions for sandboxing
- Added explicit parameter usage instructions
- Added detailed patch format documentation

### 5. **Performance Optimization**
- Final commit focused entirely on parallelization efficiency
- Suggests a shift from correctness to performance optimization

### 6. **Iterative Refinement Based on Usage**
- Each commit addresses specific observed behaviors
- Changes become more targeted and specific over time
- Removal of instructions (commit 3) shows willingness to simplify when needed

---

## Inferred Development Process

1. **Initial Creation (Nov 12)**: Baseline prompt established
2. **Early Testing (Nov 12-13)**: Issues identified with agent behavior
3. **Major Refinement (Nov 13)**: Comprehensive update addressing multiple behavioral issues
4. **Tool Changes (Nov 17)**: Shell tool implementation likely changed, requiring instruction removal
5. **Performance Tuning (Nov 19)**: Parallelization identified as bottleneck, explicit guidance added

The rapid iteration (4 commits in 7 days) suggests active development and real-world testing, with changes driven by observed agent behavior rather than theoretical design.

---

## Key Themes

1. **Persistence and Autonomy**: Strong emphasis on completing tasks end-to-end
2. **Communication Clarity**: Standardized update patterns and verbosity controls
3. **Tool Correctness**: Detailed documentation to prevent usage errors
4. **Performance**: Explicit parallelization requirements
5. **Practicality**: Willingness to remove instructions that don't work in practice

