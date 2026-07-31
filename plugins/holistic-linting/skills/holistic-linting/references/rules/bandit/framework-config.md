# Framework and Application Configuration

Insecure default settings in web frameworks expose applications to debugging leaks, code injection, and XSS attacks.

## B201: Flask Debug True

**Severity**: HIGH

**What It Detects**: Running Flask application with `debug=True` in production or potentially in production.

### When This Is a Vulnerability

Flask debug mode:

- Exposes full stack traces to users
- Enables the interactive debugger accessible via the web
- Allows arbitrary code execution through the debugger console

```python
# VULNERABLE - Debug mode enabled
from flask import Flask

app = Flask(__name__)
app.run(debug=True)  # Debugger enabled in production!

# VULNERABLE - Hardcoded debug=True
if __name__ == "__main__":
    app.run(debug=True)  # Could be in production
```

### When This IS NOT a Vulnerability

Debug mode in local development:

```python
# OK - Local development only
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
app.run(debug=DEBUG)

# OK - Explicit environment check
if os.getenv("ENV") != "production":
    app.run(debug=True)
```

### How to Fix

**Environment-Driven Debug Mode**:

```python
from flask import Flask
import os

app = Flask(__name__)

# Debug based on environment
app.debug = os.getenv("FLASK_ENV") == "development"

if __name__ == "__main__":
    app.run(debug=app.debug, host="127.0.0.1")

# Or explicitly
import logging

app.logger.setLevel(logging.INFO if app.debug else logging.WARNING)
```

---

## B202: Tarfile Unsafe Members

**Severity**: MEDIUM

**What It Detects**: Extracting tar files without validating member paths, allowing directory traversal.

### When This Is a Vulnerability

Tar files can contain paths like `../../../etc/passwd`:

```python
# VULNERABLE - Extracting without validation
import tarfile

user_tar = "uploaded.tar.gz"
with tarfile.open(user_tar) as tar:
    tar.extractall()  # Extracts to parent directories!
```

### How to Fix

**Validate Tar Member Paths**:

```python
import tarfile
import os


def safe_extract_tar(tar_path, extract_path):
    """Extract tar safely, validating all member paths."""
    extract_path = os.path.abspath(extract_path)

    with tarfile.open(tar_path) as tar:
        for member in tar.getmembers():
            # Check for path traversal
            member_path = os.path.abspath(os.path.join(extract_path, member.name))

            if not member_path.startswith(extract_path):
                raise ValueError(f"Attempted directory traversal: {member.name}")

            # Extract safely
            tar.extract(member, path=extract_path)


# Safe extraction
safe_extract_tar("uploaded.tar.gz", "./temp/")
```

---

## B612: Logging Config Insecure Listen

**Severity**: MEDIUM

**What It Detects**: Python logging configured to listen on all interfaces (0.0.0.0) instead of localhost.

### When This Is a Vulnerability

Logging server listening on 0.0.0.0 allows remote attackers to send malicious log messages:

```python
# VULNERABLE - Listening on all interfaces
import logging.config

logging_config = {
    "version": 1,
    "handlers": {
        "socket": {
            "class": "logging.handlers.SocketHandler",
            "host": "0.0.0.0",  # Listens on all interfaces!
            "port": 9020,
        }
    },
}

logging.config.dictConfig(logging_config)
```

### How to Fix

**Use Localhost Only**:

```python
import logging.config

# RIGHT - Localhost only
logging_config = {
    "version": 1,
    "handlers": {
        "socket": {
            "class": "logging.handlers.SocketHandler",
            "host": "127.0.0.1",  # Only localhost
            "port": 9020,
        }
    },
}

logging.config.dictConfig(logging_config)
```

---

## B701: Jinja2 Autoescape False

**Severity**: HIGH

**What It Detects**: Jinja2 templates with autoescape disabled, allowing XSS attacks.

### When This Is a Vulnerability

Without autoescape, user input is inserted raw into HTML:

```python
# VULNERABLE - Autoescape disabled
from jinja2 import Environment

env = Environment(autoescape=False)  # Disables HTML escaping!

template = env.from_string("Hello {{ name }}!")
result = template.render(name="<script>alert('XSS')</script>")
# Result: Hello <script>alert('XSS')</script>!
# Script executes in browser!
```

### How to Fix

**Enable Autoescape**:

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

# RIGHT - Enable autoescape (default)
env = Environment(autoescape=True)

# RIGHT - Selective autoescape by extension
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
)

# RIGHT - For Flask (autoescape on by default)
from flask import Flask

app = Flask(__name__)
# Autoescape is enabled by default for .html, .xml, .xhtml
```

---

## B702: Use of Mako Templates

**Severity**: MEDIUM

**What It Detects**: Using Mako template engine, which doesn't have safe defaults for escaping.

### When This Is a Vulnerability

Mako doesn't auto-escape by default:

```python
# VULNERABLE - Mako without escaping
from mako.template import Template

template = Template("Hello ${name}")
result = template.render(name="<script>alert('XSS')</script>")
# Result: Hello <script>alert('XSS')</script>!
```

### How to Fix

**Use Jinja2 Instead**:

```python
# Prefer Jinja2 which has autoescape enabled by default
from jinja2 import Template

template = Template("Hello {{ name }}")
result = template.render(name="<script>alert('XSS')</script>")
# Result: Hello &lt;script&gt;alert('XSS')&lt;/script&gt; (safe)
```

**Or Use Mako with Escaping**:

```python
from mako.template import Template

# Explicitly escape in Mako
template = Template("Hello ${name | h}")  # | h means HTML escape
result = template.render(name="<script>alert('XSS')</script>")
# Result: Hello &lt;script&gt;alert('XSS')&lt;/script&gt; (safe)
```

---

## B703: Django Mark Safe

**Severity**: HIGH

**What It Detects**: Using Django's `mark_safe()` on user input, bypassing HTML escaping.

### When This Is a Vulnerability

`mark_safe()` tells Django to not escape HTML:

```python
# VULNERABLE - mark_safe with user input
from django.utils.safestring import mark_safe

user_content = request.POST.get("comment")  # "<script>alert('XSS')</script>"
# This bypasses Django's auto-escaping
safe_content = mark_safe(user_content)

# Template: {{ safe_content }}
# Result: Script executes!
```

### How to Fix

**Don't Use mark_safe() on User Input**:

```python
from django.utils.safestring import mark_safe
from django.utils.html import escape

# WRONG
user_content = request.POST.get("comment")
safe_content = mark_safe(user_content)

# RIGHT - Let Django escape by default
template_context = {
    "comment": user_content  # Django auto-escapes in templates
}

# RIGHT - If you must use mark_safe, escape first
user_content = request.POST.get("comment")
escaped = escape(user_content)  # HTML escape
safe_content = mark_safe(escaped)

# RIGHT - For markdown/rich text, use safe libraries
from markdownx import markdownify

rendered = markdownify(user_content)  # Safe markdown rendering
safe_content = mark_safe(rendered)
```

---

## B704: Markupsafe Markup XSS

**Severity**: HIGH

**What It Detects**: Directly instantiating `Markup()` from user input without escaping, allowing XSS.

### When This Is a Vulnerability

```python
# VULNERABLE - Markup with user input
from markupsafe import Markup

user_input = request.args.get("content")  # "<script>alert('XSS')</script>"
html = Markup(user_input)  # Marks as safe without escaping!
```

### How to Fix

**Use Escape Before Markup**:

```python
from markupsafe import Markup, escape

# WRONG
user_input = request.args.get("content")
html = Markup(user_input)

# RIGHT - Escape before marking as safe
user_input = request.args.get("content")
html = Markup(escape(user_input))

# RIGHT - Use Jinja2 which auto-escapes
from jinja2 import Template

template = Template("{{ content }}")
html = template.render(content=user_input)
```

---

See also: [index.md](./index.md) for all Bandit security checks.
