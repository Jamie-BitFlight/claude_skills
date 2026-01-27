# Claude Skills Collection

A collection of Claude Code plugins that make Claude better at specific development tasks.

## Installation

```bash
# Add the marketplace (one-time setup)
/plugin marketplace add Jamie-BitFlight/claude_skills

# Install a plugin
/plugin install plugin-name@jamie-bitflight-skills
```

## Available Plugins

### Python Development

| Plugin                                                   | What It Does                                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [python3-development](./plugins/python3-development)     | Better Python code with modern patterns, proper testing, and clean project structure |
| [uv](./plugins/uv)                                       | Fast, modern Python project setup with uv instead of pip                             |
| [async-python-patterns](./plugins/async-python-patterns) | Write async Python code that actually works                                          |
| [hatchling](./plugins/hatchling)                         | Set up Python packages with modern pyproject.toml                                    |
| [pypi-readme-creator](./plugins/pypi-readme-creator)     | READMEs that render correctly on PyPI                                                |
| [toml-python](./plugins/toml-python)                     | Edit TOML files without breaking comments and formatting                             |

### Shell Development

| Plugin                                           | What It Does                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| [bash-development](./plugins/bash-development)   | Comprehensive Bash scripting with testing, linting, portability, and logging  |

### Perl Development

| Plugin                                           | What It Does                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| [perl-development](./plugins/perl-development)   | Modern Perl 5.30+ development with CPAN ecosystem, testing, and validation    |

### Code Quality

| Plugin                                         | What It Does                                                |
| ---------------------------------------------- | ----------------------------------------------------------- |
| [holistic-linting](./plugins/holistic-linting) | Claude checks and fixes lint errors before saying "done"    |
| [pre-commit](./plugins/pre-commit)             | Set up pre-commit hooks that actually catch issues          |
| [clang-format](./plugins/clang-format)         | Configure C/C++ formatting that matches your codebase style |

### Git & CI/CD

| Plugin                                                 | What It Does                                               |
| ------------------------------------------------------ | ---------------------------------------------------------- |
| [conventional-commits](./plugins/conventional-commits) | Consistent commit messages that work with semantic release |
| [commitlint](./plugins/commitlint)                     | Validate commit messages in CI                             |
| [gitlab-skill](./plugins/gitlab-skill)                 | Better GitLab CI pipelines and documentation               |

### AI & LLM Tools

| Plugin                                                                   | What It Does                           |
| ------------------------------------------------------------------------ | -------------------------------------- |
| [fastmcp-creator](./plugins/fastmcp-creator)                             | Build MCP servers that Claude can use  |
| [litellm](./plugins/litellm)                                             | Call any LLM API with one library      |
| [llamafile](./plugins/llamafile)                                         | Run LLMs locally without cloud APIs    |
| [prompt-optimization-claude-45](./plugins/prompt-optimization-claude-45) | Write better CLAUDE.md and skill files |

### Documentation

| Plugin                     | What It Does                                    |
| -------------------------- | ----------------------------------------------- |
| [mkdocs](./plugins/mkdocs) | Create documentation sites with MkDocs Material |

### Better Claude Behavior

| Plugin                                               | What It Does                                             |
| ---------------------------------------------------- | -------------------------------------------------------- |
| [agent-orchestration](./plugins/agent-orchestration) | Claude handles complex, multi-step tasks more thoroughly |
| [brainstorming-skill](./plugins/brainstorming-skill) | Structured brainstorming with proven prompt patterns     |
| [story-based-framing](./plugins/story-based-framing) | Better pattern recognition through narrative structure   |
| [verification-gate](./plugins/verification-gate)     | Claude verifies work before claiming "done"              |

### Plugin Development

| Plugin                                         | What It Does                                                         |
| ---------------------------------------------- | -------------------------------------------------------------------- |
| [plugin-creator](./plugins/plugin-creator)     | Step-by-step guidance for creating new Claude Code plugins           |
| [plugin-refactor](./plugins/plugin-refactor)   | Systematic toolkit for refactoring and improving existing plugins    |

### System

| Plugin                                             | What It Does                                    |
| -------------------------------------------------- | ----------------------------------------------- |
| [xdg-base-directory](./plugins/xdg-base-directory) | Store config and data files in the right places |

## Plugin Structure

```text
plugins/plugin-name/
├── .claude-plugin/
│   └── plugin.json       # Plugin manifest
├── skills/               # What Claude learns
├── commands/             # Slash commands you can use
├── agents/               # Specialized sub-agents
└── README.md             # Documentation
```

## Local Development

For testing plugins during development:

```bash
# Option 1: Load specific plugins for this session
claude --plugin-dir ./plugins/python3-development --plugin-dir ./plugins/holistic-linting

# Option 2: Add local marketplace for persistent enable/disable
/plugin marketplace add ./.claude-plugin/marketplace.json

# Install plugins you need (--scope local keeps it gitignored)
/plugin install python3-development@jamie-bitflight-skills --scope local

# Disable when not needed
/plugin disable python3-development@jamie-bitflight-skills

# Re-enable when needed
/plugin enable python3-development@jamie-bitflight-skills
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add or modify plugins
4. Test locally using one of the methods above
5. Submit a pull request

## License

MIT License - see individual plugins for specifics.
