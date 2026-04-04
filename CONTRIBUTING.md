# Contributing to Sniffixx

Thank you for your interest in contributing to Sniffixx!

## Code of Conduct

By participating in this project, you agree to maintain a respectful and constructive environment.

## Getting Started

### Prerequisites
- Kali NetHunter (Android with Termux)
- Root access
- WiFi adapter supporting monitor mode

### Development Setup
```bash
git clone https://github.com/dtrail/sniffixx.git
cd sniffixx
chmod +x install.sh
sudo ./install.sh
```

## How to Contribute

### Reporting Bugs
1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include environment details and reproduction steps

### Suggesting Features
1. Check existing issues and pull requests
2. Use the feature request template
3. Explain the use case and motivation

### Pull Requests
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test thoroughly on your system
5. Commit with clear messages: `git commit -m "Add: description"`
6. Push and submit a PR

## Style Guidelines

### Bash Scripts
- Use `set -euo pipefail` at the top
- Quote all variables
- Use meaningful function and variable names
- Add comments for complex logic

### Python Scripts
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to functions

## Questions?

Open an issue for discussion before starting large changes.
