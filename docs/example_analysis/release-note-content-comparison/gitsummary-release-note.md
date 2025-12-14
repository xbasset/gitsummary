# gitsummary 0.0.1 — 2025-12-02

*Introducing AI-powered, structured release notes with enhanced CLI and Git integration for seamless software version insights.*

## 🚀 Highlights

- 🚀 **New**: AI-assisted release notes generation with LLMs
- 🚀 **New**: Store and retrieve release notes via Git Notes
- ✨ **Improved**: Flexible CLI with rich options for release notes
- ⚠️ **Breaking**: CLI restructuring and removal of deprecated commands
- ✨ **Improved**: Pluggable LLM providers for customizable analysis

## 🆕 New Features

### AI-Assisted Release Notes Generation

Generate detailed, user-friendly release notes using large language models (LLMs) with configurable providers and models.

*Easily create insightful, well-structured release notes that highlight key changes without manual effort.*

### Git Notes Integration for Release Notes Storage

Persist generated release notes directly into Git Notes attached to commits, and retrieve them anytime via the CLI.

*Keep release notes versioned and accessible alongside your code history for better traceability and collaboration.*

### Enhanced Command-Line Interface

A reorganized CLI with new subcommands and options to generate, format (markdown/yaml/text), and display release notes and commit artifacts.

*More control and flexibility in how you generate and view release notes, tailored to your workflow and preferences.*

### Pluggable LLM Provider Architecture

Support for multiple LLM backends with easy selection of providers and models, including OpenAI integration with structured output.

*Customize your analysis and release note generation with the best AI models for your needs, improving accuracy and relevance.*

## ✨ Improvements

- Refined LLM provider initialization to securely and correctly handle API keys and model overrides, ensuring reliable AI integration.
- Improved date formatting in commit listings with absolute and relative options for clearer timelines.
- Centralized release note rendering logic for consistent formatting across markdown and text outputs.
- Comprehensive documentation updates including getting started guides, CLI usage clarifications, and project goals for better user onboarding.
- Introduced automated testing infrastructure covering core models and CLI formatting to ensure reliability and maintainability.

## 🛠️ Bug Fixes

- Fixed date formatting functions to correctly display absolute and relative dates in commit listings.

## ⚠️ Deprecations & Breaking Changes

### Removal of the deprecated 'report' CLI subcommand and its aliases.

**Reason**: To simplify the CLI and focus on the improved 'generate' and 'show' commands for report generation and display.

**Migration**: Use 'generate' commands for changelog, release-notes, and impact reports instead of 'report'. Update scripts and workflows accordingly.

### CLI restructuring introducing 'show' as a subcommand group and enhanced 'generate release-notes' options.

**Reason**: To provide a clearer, more extensible command structure and richer functionality for release notes management.

**Migration**: Adapt to the new CLI syntax: use 'gitsummary show release-note <rev>' to display stored notes and new flags like '--llm', '--provider', '--model', '--format', and '--store' with 'generate release-notes'.

---
*51 commits, 51 analyzed • Generated with openai/gpt-4.1-mini*
