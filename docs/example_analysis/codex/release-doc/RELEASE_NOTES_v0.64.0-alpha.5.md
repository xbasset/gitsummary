# Release Notes: rust-v0.64.0-alpha.5

**Release Date:** November 21, 2025  
**Previous Release:** rust-v0.61.1-alpha.2  
**Total Commits:** 60

---

## User-Visible Impact (Risk/Breaking Changes)

### ⚠️ ExecPolicy Sandbox Bypass Behavior Change
**Commit:** `87b211709` - bypass sandbox for policy approved commands (#7110)

**Risk Level:** Medium

Commands explicitly approved by execpolicy rules (with `Decision::Allow`) now **bypass the sandbox entirely** on the first execution attempt. Previously, these commands would still run in the sandbox and potentially fail if they required write access or network connectivity.

**Impact:**
- Commands matching execpolicy rules with `allow` decision will execute with full system access
- This applies to both `shell` and `unified_exec` tool calls
- Users relying on sandbox protection for policy-approved commands may see different behavior

**Code Reference:**
```110:112:codex-rs/core/src/exec_policy.rs
            Decision::Allow => Some(ApprovalRequirement::Skip {
                bypass_sandbox: true,
            }),
```

The `bypass_sandbox: true` flag is now propagated through the execution pipeline, causing `SandboxOverride::BypassSandboxFirstAttempt` to be applied:

```139:152:codex-rs/core/src/tools/runtimes/unified_exec.rs
    fn sandbox_mode_for_first_attempt(&self, req: &UnifiedExecRequest) -> SandboxOverride {
        if req.with_escalated_permissions.unwrap_or(false)
            || matches!(
                req.approval_requirement,
                ApprovalRequirement::Skip {
                    bypass_sandbox: true
                }
            )
        {
            SandboxOverride::BypassSandboxFirstAttempt
        } else {
            SandboxOverride::NoOverride
        }
    }
```

### ⚠️ ExecPolicy Package Migration
**Commit:** `fb9849e1e` - migrating execpolicy -> execpolicy-legacy and execpolicy2 -> execpolicy (#6956)

**Risk Level:** Low (Internal)

The execpolicy implementation has been restructured:
- `execpolicy` crate → `execpolicy-legacy` (preserved for backward compatibility)
- `execpolicy2` crate → `execpolicy` (new default implementation)

**Impact:**
- No user-visible API changes
- Internal code now uses the new `execpolicy` implementation
- Legacy policy format remains supported through `execpolicy-legacy`

### ⚠️ Windows Sandbox: Enhanced Dangerous Command Detection
**Commit:** `3bdcbc729` - Windows: flag some invocations that launch browsers/URLs as dangerous (#7111)

**Risk Level:** Medium

Windows sandbox now blocks PowerShell/CMD invocations that attempt to:
- Launch browsers (via `Start-Process`, `Invoke-Item`, etc.)
- Execute commands with URL arguments
- Use ShellExecute-style entry points

**Impact:**
- Commands that previously might have been allowed in the sandbox are now blocked
- Users may see more approval prompts for Windows-specific operations
- Browser-launching commands will be flagged as dangerous before reaching the sandbox

**Code Reference:**
The new detection logic in `codex-rs/core/src/command_safety/windows_dangerous_commands.rs` analyzes PowerShell invocations and URL-bearing arguments to prevent GUI launches.

### ⚠️ App-Server API V2: New Command Execution Status
**Commit:** `2ae1f81d8` - [app-server] feat: add Declined status for command exec (#7101)

**Risk Level:** Low (API Change)

The `CommandExecutionStatus` enum now includes a `Declined` variant, allowing clients to distinguish between:
- Commands that ran but failed (`Failed`)
- Commands that were declined by the user (`Declined`)

**Impact:**
- API V2 clients should handle the new `Declined` status
- This provides clearer feedback when users reject command execution requests

**Code Reference:**
```139:148:codex-rs/exec/src/exec_events.rs
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default, TS)]
#[serde(rename_all = "snake_case")]
pub enum CommandExecutionStatus {
    #[default]
    InProgress,
    Completed,
    Failed,
    Declined,
}
```

---

## Before/After Behavior

### ExecPolicy Sandbox Bypass

**Before:**
- Commands approved by execpolicy rules would still execute in the sandbox
- If a command required write access or network, it would fail in the sandbox
- User would need to approve retry outside sandbox

**After:**
- Commands with `Decision::Allow` in execpolicy bypass the sandbox on first attempt
- These commands execute with full system access immediately
- No retry approval needed for policy-approved commands

**Example:**
If an execpolicy rule allows `git push`, it will now execute directly without sandbox restrictions, whereas previously it would fail in the read-only sandbox and require approval to retry.

### MCP Elicitations Timeout Handling

**Before:**
**Commit:** `8e5f38c0f` - feat: waiting for an elicitation should not count against a shell tool timeout (#6973)

- Time spent waiting for user response to MCP elicitations counted against the shell tool timeout
- If user took >10 seconds to respond, the tool call would timeout and fail
- This created a poor user experience where fast responses were required

**After:**
- Introduced `Stopwatch` abstraction that pauses during elicitation requests
- Time spent waiting for user approval does not count against the tool timeout
- Multiple concurrent elicitations are tracked with a pause counter
- Tool timeout only applies to actual execution time, not user interaction time

**Code Reference:**
The `Stopwatch` implementation in `codex-rs/exec-server/src/posix/stopwatch.rs` manages pause/resume semantics, allowing the timeout to be suspended during user interactions.

### Windows Sandbox Network Access

**Before:**
**Commit:** `f4af6e389` - Windows Sandbox: support network_access and exclude_tmpdir_env_var (#7030)

- Windows sandbox did not support `network_access` configuration
- `exclude_tmpdir_env_var` option was not available

**After:**
- Windows sandbox now respects `network_access` policy setting
- `exclude_tmpdir_env_var` can be used to control whether `$TMPDIR` environment variables are included in sandboxed execution
- Provides parity with POSIX sandbox behavior

**Code Reference:**
```33:39:codex-rs/windows-sandbox-rs/src/allow.rs
    let include_tmp_env_vars = matches!(
        policy,
        SandboxPolicy::WorkspaceWrite {
            exclude_tmpdir_env_var: false,
            ..
        }
    );
```

### App-Server V2: Apply Patch Approval Flow

**Before:**
**Commit:** `d6c30ed25` - [app-server] feat: v2 apply_patch approval flow (#6760)

- V1 API used `ApplyPatchApproval` request/response pattern
- Event ordering was: `ApplyPatchApprovalRequest` → `PatchApplyBegin` → `PatchApplyEnd`
- No structured `ThreadItem::FileChange` representation

**After:**
- V2 API introduces `item/fileChange/requestApproval` RPC
- Event ordering: `item/started` → `item/fileChange/requestApproval` → `item/completed`
- File changes are represented as `ThreadItem::FileChange` with structured `changes` array
- Approval flow is consistent with `ThreadItem::CommandExecution` pattern

**Example V2 Payload:**
```json
{
  "method": "item/started",
  "params": {
    "item": {
      "type": "fileChange",
      "id": "call_...",
      "status": "inProgress",
      "changes": [
        {
          "kind": "add",
          "path": "/path/to/file.txt",
          "diff": "..."
        }
      ]
    }
  }
}
```

### TUI: Reasoning Selection Default

**Before:**
**Commit:** `1822ffe87` - feat(tui): default reasoning selection to medium (#7040)

- When opening `/models` reasoning selector, no option was pre-selected
- User had to manually navigate to desired reasoning level

**After:**
- Reasoning selector now defaults to "medium" effort level
- Selector opens with the default option highlighted
- Improves UX by reducing navigation steps

---

## Implementation Decisions

### ExecPolicy Sandbox Bypass Architecture

**Decision:** Commands approved by execpolicy bypass sandbox on first attempt rather than attempting sandbox first.

**Rationale:**
- Policy-approved commands are explicitly trusted by the user
- Reduces unnecessary sandbox failures and retry approvals
- Aligns with the principle that policy decisions should be authoritative
- Prepares for future execpolicy rules that may specify sandbox requirements

**Implementation:**
The bypass decision flows through the approval requirement system:
1. `evaluate_with_policy()` returns `ApprovalRequirement::Skip { bypass_sandbox: true }` for `Decision::Allow`
2. This propagates to `UnifiedExecRequest.approval_requirement`
3. `sandbox_mode_for_first_attempt()` checks for `bypass_sandbox: true` flag
4. Returns `SandboxOverride::BypassSandboxFirstAttempt` which is handled by the sandboxing layer

**Code Reference:**
```118:141:codex-rs/core/src/exec_policy.rs
pub(crate) fn create_approval_requirement_for_command(
    policy: &Policy,
    command: &[String],
    approval_policy: AskForApproval,
    sandbox_policy: &SandboxPolicy,
    sandbox_permissions: SandboxPermissions,
) -> ApprovalRequirement {
    if let Some(requirement) = evaluate_with_policy(policy, command, approval_policy) {
        return requirement;
    }

    if requires_initial_appoval(
        approval_policy,
        sandbox_policy,
        command,
        sandbox_permissions,
    ) {
        ApprovalRequirement::NeedsApproval { reason: None }
    } else {
        ApprovalRequirement::Skip {
            bypass_sandbox: false,
        }
    }
}
```

### MCP Elicitation Timeout Management

**Decision:** Use a pauseable `Stopwatch` abstraction rather than extending timeout duration.

**Rationale:**
- More precise: timeout applies only to execution, not user interaction
- Handles concurrent elicitations correctly with pause counter
- Prevents timeout abuse where long user delays would extend execution time
- Cleaner separation of concerns: execution time vs. interaction time

**Implementation:**
- `Stopwatch::new(timeout)` creates a stopwatch with the real timeout
- `Stopwatch::pause_for(async { ... })` suspends timeout during async operation
- Pause counter tracks nested/concurrent pauses
- Timeout only resumes when all pauses complete

**Code Reference:**
The `Stopwatch` implementation in `codex-rs/exec-server/src/posix/stopwatch.rs` provides:
- `pause_for()` method that suspends timeout during async operations
- Reference counting for concurrent pauses
- Integration with `Cancellation` variant of `ExecExpiration`

### App-Server V2 Apply Patch: State Management

**Decision:** Use `TurnSummaryStore` to reorder events rather than modifying core event emission order.

**Rationale:**
- Core event emission order (`ApplyPatchApprovalRequest` → `PatchApplyBegin`) is used by multiple consumers
- Changing core would require extensive testing across all code paths
- App-server can translate events to desired V2 API shape without core changes
- Less invasive approach maintains backward compatibility

**Implementation:**
- `TurnSummaryStore` stores pending file change items when `ApplyPatchApprovalRequest` is received
- When `PatchApplyBegin` arrives, check if item already exists in store
- If exists, emit `item/started` and `item/fileChange/requestApproval` immediately
- When `PatchApplyBegin` arrives, no-op if item already started
- Ensures correct event ordering: `item/started` → `requestApproval` → `item/completed`

**Code Reference:**
The implementation in `codex-rs/app-server/src/bespoke_event_handling.rs` uses `TurnSummaryStore` to manage this state translation.

### Windows Dangerous Command Detection

**Decision:** Implement structured parsing for PowerShell/CMD before falling back to simple argv heuristics.

**Rationale:**
- PowerShell has complex syntax with cmdlets, COM objects, and URL arguments
- Simple string matching would miss many dangerous patterns
- Need to detect `Start-Process`, `Invoke-Item`, and URL-bearing arguments
- Prevents GUI launches and browser invocations that bypass sandbox restrictions

**Implementation:**
- `is_dangerous_powershell()` parses PowerShell invocation tokens
- Detects dangerous cmdlets: `Start-Process`, `Invoke-Item`, `saps`, `ii`
- Scans for URL patterns in arguments
- Falls back to `is_dangerous_cmd()` for CMD.exe patterns
- Finally checks `is_direct_gui_launch()` for direct GUI executables

**Code Reference:**
```23:50:codex-rs/core/src/command_safety/windows_dangerous_commands.rs
fn is_dangerous_powershell(command: &[String]) -> bool {
    let Some((exe, rest)) = command.split_first() else {
        return false;
    };
    if !is_powershell_executable(exe) {
        return false;
    }
    // Parse the PowerShell invocation to get a flat token list we can scan for
    // dangerous cmdlets/COM calls plus any URL-looking arguments. This is a
    // best-effort shlex split of the script text, not a full PS parser.
    let Some(parsed) = parse_powershell_invocation(rest) else {
        return false;
    };

    let tokens_lc: Vec<String> = parsed
        .tokens
        .iter()
        .map(|t| t.trim_matches('\'').trim_matches('"').to_ascii_lowercase())
        .collect();
    let has_url = args_have_url(&parsed.tokens);

    if has_url
        && tokens_lc.iter().any(|t| {
            matches!(
                t.as_str(),
                "start-process" | "start" | "saps" | "invoke-item" | "ii"
            ) || t.contains("start-process")
                || t.contains("invoke-item")
```

### Codex Shell Tool MCP Package

**Decision:** Create standalone npm package `@openai/codex-shell-tool-mcp` with platform-specific binaries.

**Rationale:**
- Enables Codex to be used as an MCP tool in other MCP clients
- Provides pre-built binaries for multiple platforms (macOS arm64/x64, Linux musl arm64/x64)
- Includes patched Bash for glibc compatibility across Linux distributions
- Simplifies deployment: `npx @openai/codex-shell-tool-mcp` works out of the box

**Implementation:**
- GitHub workflow builds Rust binaries (`codex-exec-mcp-server`, `codex-execve-wrapper`) for all targets
- Builds dynamically-linked Bash with `BASH_EXEC_WRAPPER` patch for multiple Linux distributions
- TypeScript launcher (`bin/mcp-server.js`) performs runtime platform detection
- Selects appropriate binaries based on `process.platform`, `process.arch`, and `/etc/os-release`
- Packages everything into npm tarball for distribution

**Code Reference:**
The package structure and build process is defined in:
- `.github/workflows/shell-tool-mcp.yml` - Build workflow
- `shell-tool-mcp/src/index.ts` - Main launcher logic
- `shell-tool-mcp/src/bashSelection.ts` - Bash binary selection logic

---

## Other

### MCP Elicitations Support

**Commit:** `7561a6aaf` - support MCP elicitations (#6947)

**Summary:**
Codex now supports MCP elicitation requests from MCP servers. When an MCP server requests user input via the `elicitation/create` protocol, Codex displays the message in the TUI approval overlay and allows accept/decline actions.

**Implementation:**
- Added `McpElicitation` variant to `ApprovalVariant` enum
- TUI approval overlay handles elicitation requests
- Elicitation responses are routed back to the MCP server
- Currently supports basic accept/decline; request schema parsing not yet implemented

**Code Reference:**
The elicitation handling is implemented in:
- `codex-rs/core/src/mcp_connection_manager.rs` - Manages elicitation request/response lifecycle
- `codex-rs/tui/src/bottom_pane/approval_overlay.rs` - UI for elicitation approval

### App-Server: Thread Metadata Exposure

**Commit:** `aa4e0d823` - [app-server] feat: expose gitInfo/cwd/etc. on Thread (#7060)

**Summary:**
V2 API now exposes `gitInfo`, `cwd`, and other thread metadata on the `Thread` object, porting functionality from the legacy API.

**Impact:**
- VSCode extension and other V2 API clients can access git repository information
- Working directory information is available for each thread
- Enables better context-aware features in client applications

### Unified Exec for Experiments

**Commit:** `d5f661c91` - enable unified exec for experiments (#7118)

**Summary:**
Unified exec runtime is now enabled for experimental model families, allowing new execution features to be tested with experimental models.

**Impact:**
- Experimental models can use the unified exec path
- Enables testing of new execution features before broader rollout
- No user-visible changes for stable models

### TUI Improvements

**Commit:** `2c793083f` - tui: centralize markdown styling and make inline code cyan (#7023)

**Summary:**
- Centralized markdown styling logic
- Inline code blocks now render in cyan color for better visibility
- Improves readability of code snippets in agent responses

**Commit:** `d909048a8` - Added feature switch to disable animations in TUI (#6870)

**Summary:**
- Added configuration option to disable TUI animations
- Useful for users with accessibility needs or performance constraints
- Can be toggled via config file

### Bug Fixes

**Commit:** `3ea33a061` - fix(tui): Fail when stdin is not a terminal (#6382)

**Summary:**
TUI now properly detects when stdin is not a terminal and fails gracefully rather than hanging or producing undefined behavior.

**Commit:** `54e6e4ac3` - fix: when displaying execv, show file instead of arg0 (#6966)

**Summary:**
When displaying execv-style command executions, the UI now shows the actual file being executed rather than the arg0 value, providing more accurate command representation.

**Commit:** `e8af41de8` - fix: clean up elicitation used by exec-server (#6958)

**Summary:**
Fixed resource cleanup for elicitation requests in exec-server, preventing memory leaks in long-running sessions.

**Commit:** `888c6dd9e` - fix: command formatting for user commands (#7002)

**Summary:**
Improved command formatting consistency for user-initiated commands, ensuring proper display in history and approval overlays.

### Test Infrastructure

**Commit:** `1388e9967` - fix flaky `tool_call_output_exceeds_limit_truncated_chars_limit` (#7043)

**Commit:** `44fa06ae3` - fix flaky test: `approval_matrix_covers_all_modes` (#7028)

**Commit:** `54ee302a0` - Attempt to fix `unified_exec_formats_large_output_summary` flakiness (#7029)

**Summary:**
Multiple test stability improvements to reduce flakiness in CI/CD pipelines.

### Documentation

**Commit:** `a0434bbdb` - [app-server] doc: approvals (#7105)

**Summary:**
Added documentation for the approval flow in app-server, improving developer understanding of the approval request/response cycle.

### Configuration Changes

**Commit:** `c9e149fd5` - fix: read `max_output_tokens` param from config (#4139)

**Summary:**
Fixed reading of `max_output_tokens` configuration parameter, ensuring it is properly applied from config files.

**Commit:** `bce030ddb` - Revert "fix: read `max_output_tokens` param from config" (#7088)

**Summary:**
Temporarily reverted the above change due to compatibility issues, then re-applied in `c9e149fd5`.

**Commit:** `af6566656` - chore: drop model_max_output_tokens (#7100)

**Summary:**
Removed deprecated `model_max_output_tokens` configuration option in favor of `max_output_tokens`.

### Performance and Reliability

**Commit:** `b5dd18906` - Allow unified_exec to early exit (if the process terminates before yield_time_ms) (#6867)

**Summary:**
Unified exec now supports early exit when a process terminates before the yield timeout, improving responsiveness for short-running commands.

**Commit:** `30ca89424` - Always fallback to real shell (#6953)

**Summary:**
Ensures fallback to real shell execution when sandboxed execution is not available, improving reliability across different environments.

**Commit:** `0fbcdd77c` - core: make shell behavior portable on FreeBSD (#7039)

**Summary:**
Improved shell command execution portability for FreeBSD systems, ensuring consistent behavior across Unix-like platforms.

### Code Quality

**Commit:** `67975ed33` - refactor: inline sandbox type lookup in process_exec_tool_call (#7122)

**Summary:**
Code refactoring to inline sandbox type lookup, improving code clarity and reducing function call overhead.

**Commit:** `856f97f44` - Delete shell_command feature (#7024)

**Summary:**
Removed deprecated `shell_command` feature flag, cleaning up codebase and simplifying feature management.

**Commit:** `52d0ec4cd` - Delete tiktoken-rs (#7018)

**Summary:**
Removed unused `tiktoken-rs` dependency, reducing binary size and dependency complexity.

---

## Summary

This release introduces significant improvements to execution policy handling, MCP integration, Windows sandbox security, and app-server API V2. The most notable change is that execpolicy-approved commands now bypass the sandbox, which may affect users who rely on sandbox protection for these commands. The release also adds comprehensive MCP elicitation support, improves timeout handling for user interactions, and enhances Windows security through better dangerous command detection.

**Key Highlights:**
- ⚠️ **Breaking:** ExecPolicy-approved commands bypass sandbox
- 🆕 **New:** MCP elicitations support
- 🆕 **New:** Codex Shell Tool MCP npm package
- 🔒 **Security:** Enhanced Windows dangerous command detection
- 📡 **API:** V2 apply_patch approval flow
- 📡 **API:** Command execution declined status
- 🐛 **Fix:** MCP elicitation timeout handling
- 🐛 **Fix:** Multiple test stability improvements

