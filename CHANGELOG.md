# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-01-19

### Added
- Auto-scroll chat messages to bottom when new content is added
- SVG favicon support with custom logo
- Response time display for agent messages (e.g., "23s" or "1m 43s")
- Persistent todos in chat history (todos now stick like tool calls)
- dash-iconify as a required dependency

### Changed
- Eliminated index.html template - all styles now in styles.css
- Simplified app configuration with inline index string for favicon only
- Improved todo rendering to support list format from agent output
- Default agent spec now points to package's agent.py

### Fixed
- Terminal and refresh button icons not visible (switched to mdi icons)
- dangerously_allow_html incorrectly passed to html.Div instead of dcc.Markdown
- Todo items not rendering (format_todos now handles both list and dict formats)

### UI/UX
- Added Google Fonts import directly in CSS
- Consolidated all animations and styles in styles.css
- Dark mode support for all new components

## [0.1.1] - 2025-11-29

### Added
- Environment variable configuration support for all settings with `DEEPAGENT_*` prefix
- Configuration priority system: CLI args > Environment variables > config.py defaults
- Enhanced Python API: `run_app()` now accepts agent instance as first parameter
- Comprehensive test suite with 15 core functionality tests (CLI, Python API, agent loading)
- `uvx` compatibility for running without installation
- Python API examples demonstrating three usage patterns
- Environment variable `DEEPAGENT_WORKSPACE_ROOT` automatically set for agents

### Changed
- **BREAKING**: `run_app()` signature updated - `agent_instance` is now the first parameter (optional)
- README reduced by 56% for better clarity while maintaining all essential information
- Configuration documentation enhanced with clear priority hierarchy
- Agent priority in `run_app()`: agent_spec > agent_instance > config file
- Made all configuration settings clearly marked as optional in documentation

### Fixed
- Path conversion issue in config.py when using environment variables
- Test suite patch targets for proper CLI testing

### Documentation
- Added comprehensive environment variables documentation
- Added `uvx` installation and usage examples
- Updated Python API examples to show new agent instance pattern
- Clarified configuration priority in all documentation
- Added example agent setup with DeepAgents integration

## [0.1.0] - 2025-11-26

### Added
- Initial release
- AI Agent Chat with real-time streaming
- File Browser with interactive file tree and lazy loading
- Canvas for visualizing DataFrames, Plotly/Matplotlib charts, Mermaid diagrams, images
- Flexible configuration via config.py
- CLI interface with `cowork-dash` command
- Python API with `run_app()` function
- Support for custom agents via agent specification
- Manual mode (file browser only, no agent)
- Resizable split-pane interface
- Upload/download functionality for files

[0.1.2]: https://github.com/dkedar7/cowork-dash/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/dkedar7/cowork-dash/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dkedar7/cowork-dash/releases/tag/v0.1.0
