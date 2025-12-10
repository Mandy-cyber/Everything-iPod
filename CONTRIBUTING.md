# Contributing to Everything-iPod

Hi friends!! Thank you for even considering joining me in this slightly chaotic journey of coding things for iPods. Right now, I am just taking contributions for the `ipod-wrapped` stuff. Have fun!

## Table of Contents

<!-- START OF MDTOC -->
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Contributing Code](#contributing-code)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
  - [Git Commit Messages](#git-commit-messages)
  - [Python Code Style](#python-code-style)
- [Pull Request Process](#pull-request-process)

<!-- END OF MDTOC -->

## Code of Conduct

Guys, just be kind and respectful to everyone (including me omg)! I'm just here to have fun and code fun things, okay? Mwah :heart:.

## Getting Started

Before you begin:
- Check if there's already an [issue](https://github.com/mandycyber/Everything-iPod/issues) or [pull request](https://github.com/mandycyber/Everything-iPod/pulls) addressing what you want to do
- Make sure you have an iPod running rockbox
- Familiarize yourself with the project structure and [README](README.md)

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid any duplicate stuff. When creating a bug report, include as many details as possible:

**Great Bug Report Template:**
- **Clear title**: Brief, descriptive summary
- **Steps to reproduce**: Step-by-step instructions
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Screenshots**: If applicable
- **Environment**:
  - OS and version (e.g., Arch Linux 6.17.6)
  - Python version
  - iPod model and Rockbox version
  - Any relevant configuration
- **Additional context**: Error messages, logs, etc.

> Okay I haven't added great logging to the repo yet LOL, so the last part may be a bit difficult...

### Suggesting Enhancements

Enhancement suggestions are SO incredibly welcome! But, before you get typing away:
- Check if the feature already exists or is in the `TODO` list in the README
- Consider if it fits the project's scope
- Provide clear use cases and examples

**Great Enhancement Suggestion Template:**
- **Clear title**: Brief, descriptive summary
- **Use case**: Explain why this would be useful
- **Proposed solution**: How you think it should work
- **Additional context**: Mockups, examples from other projects, etc.

### Contributing Code

Please...

1. **Find an issue to work on** or create one discussing what you'd like to implement
2. **Comment on the issue** to let others know you're working on it
3. **Fork the repository** and create a branch from `main`
4. **Make your changes** following the style guidelines
5. **Test your changes** thoroughly
6. **Submit a pull request** following the PR process below

## Development Setup

### Prerequisites

1. An iPod running [Rockbox](https://www.ifixit.com/Guide/How+to+install+Rockbox+on+an+iPod+Classic/114824)
2. Python 3.13+ installed
3. Last.fm API credentials (get them [here](https://www.last.fm/api))

### Setting Up Your Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Everything-iPod.git
cd Everything-iPod

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd ipod_wrapped
pip install -r requirements.txt

# Set up your .env file
cp .env.example .env  # then add your credentials, or add them via the UI

# Run the app
python main.py
```

## Style Guidelines

### Git Commit Messages

- Not too long. Add more details in the description section if needed
- Use conventional commit prefixes:
  - `feat:` - New features
  - `fix:` - Bug fixes
  - `docs:` - Documentation changes
  - `style:` - Formatting, missing semicolons, etc.
  - `refactor:` - Code restructuring without changing behavior
  - `test:` - Adding tests
  - `chore:` - Maintenance tasks

**Examples:**
```
feat: add playlist export functionality

fix: resolve crash when parsing malformed log files

docs: update README with new installation steps
```

### Python Code Style

- Use type hints
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and reasonably sized
  - I will eventually go in and clean up my chunky monkeys too...
- Lowercase comments starting with `#` please. I can't explain why.

**Example:**
```python
def parse_rockbox_log(log_path: str) -> List[Dict[str, Any]]:
    """
    Parse a Rockbox log file and extract listening history.

    Args:
        log_path: Absolute path to the Rockbox log file

    Returns:
        List of dictionaries containing song metadata and timestamps

    Raises:
        FileNotFoundError: If log file doesn't exist
        ValueError: If log format is invalid
    """
    # implementation here
    pass
```

### GTK/UI Code

- Keep UI code in the `frontend/` directory
- Separate widgets into individual files in `frontend/widgets/`
- Follow existing patterns for page structure in `frontend/pages/`

## Pull Request Process

1. **Update documentation** if you've changed APIs or added features
2. **Update the TODO list** in README.md if you've completed an item
3. **Ensure all tests pass** (once we have a test suite LOL)
4. **Keep PRs focused**: One feature/fix per PR
5. **Fill out the PR template** with:
   - Description of changes
   - Related issue(s)
   - Type of change (bug fix, feature, docs, etc.)
   - Testing done
   - Screenshots (for UI changes)
6. **Be responsive** to feedback and questions
7. **Squash commits** if requested before merging

### PR Title Format

Use descriptive titles with prefixes:
- `feat: add dark mode toggle`
- `fix: resolve album art loading issue`
- `docs: improve setup instructions`

## Questions?

Just reach out to me or create an issue with the `question` label! I can't say I'm the quickest with responses, but I will *definitely* respond.

## Recognition

Contributors will 100% be recognized in the README.

---

> "I'm just a sleepy girl" - but together we can make this project super cool, super awesome, super fun <3!
