# Commit Message Analyzer

A smart tool that analyzes your code changes and generates meaningful commit messages automatically.

## Features

- 🤖 **Smart Analysis**: Analyzes code changes to understand what was modified
- 📝 **Semantic Detection**: Detects features, fixes, refactors, security issues, and more
- 🔍 **Multi-language Support**: Works with Python, JavaScript, TypeScript, and more
- 📊 **Detailed Reports**: Shows what functions, classes, and components were changed
- 🚀 **Easy to Use**: Just stage your changes and run the tool

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ngtrnhao/commit-analyzer.git
cd commit-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

## Usage

1. Stage your changes:
```bash
git add .
```

2. Run the analyzer:
```bash
py commit_analyzer/commit_analyzer.py
```

Or use the shortcut:
```bash
c
```

## Example Output

```
Change Analysis:
Security changes: authentication, password hashing
Features added: two-factor auth, password reset
Fixes: rate limiting, error handling
Refactors: component structure, API endpoints
Performance improvements: query optimization
Components changed: Login, Register
Dependencies changed: react@18.2.0, axios@1.6.0
Scripts changed: build, test

Code Changes Summary:
Lines added: 42
Lines removed: 15

Suggested commit message:
feat(auth): add two-factor authentication and password reset
```

## Supported Commit Types

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test changes
- `chore`: Maintenance tasks
- `security`: Security fixes
- `deps`: Dependency updates

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
