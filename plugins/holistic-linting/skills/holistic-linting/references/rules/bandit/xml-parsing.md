# XML Parsing Vulnerabilities

XML External Entity (XXE) attacks and XML Bomb (Billion Laughs) attacks exploit vulnerable XML parsers. Safe XML parsing requires using hardened parsers or validation.

## XML Parsing Checks (B313-B319, B405-B409)

**Severity**: MEDIUM

**What It Detects**: Using standard Python XML libraries vulnerable to XXE (External Entity) attacks.

### The Vulnerability: XXE (External Entity) Attacks

```xml
<!-- XXE Attack: Reads local files -->
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<foo>&xxe;</foo>

<!-- XXE Attack: Denial of Service (Billion Laughs) -->
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<lolz>&lol3;</lolz>
```

### When This Is a Vulnerability

```python
# VULNERABLE - Standard XML parsing (many libraries vulnerable)
import xml.etree.ElementTree as ET
import xml.sax
from xml.dom import minidom

# B313: xml.etree.ElementTree
tree = ET.parse(untrusted_xml_file)  # Can read local files

# B314: xml.sax
handler = xml.sax.parse(untrusted_xml_file, MyHandler())

# B315: xml.dom.expatbuilder
from xml.dom.expatbuilder import parse as expat_parse

expat_parse(untrusted_xml_file)

# B316: xml.dom.minidom
dom = minidom.parse(untrusted_xml_file)

# B317: xml.dom.pulldom
from xml.dom.pulldom import parse as pulldom_parse

pulldom_parse(untrusted_xml_file)

# B318: xml.sax.parse with handler
xml.sax.parse(untrusted_xml_string, MyHandler())
```

### Vulnerable Imports (B405-B409)

```python
# B405: VULNERABLE - xml.etree imports
from xml.etree.cElementTree import parse
from xml.etree import ElementTree

# B406: VULNERABLE - xml.sax imports
from xml.sax import parse

# B407: VULNERABLE - xml.dom.expatbuilder
from xml.dom.expatbuilder import parse

# B408: VULNERABLE - xml.dom.minidom
from xml.dom.minidom import parse

# B409: VULNERABLE - xml.dom.pulldom
from xml.dom.pulldom import parse
```

### How to Fix

**Use defusedxml (Recommended)**:

```python
# RIGHT - defusedxml is hardened against XXE
from defusedxml.ElementTree import parse as safe_parse

tree = safe_parse(untrusted_xml_file)

# Also for other libraries
from defusedxml import sax
from defusedxml import minidom
from defusedxml import pulldom

# defusedxml disables external entities by default
```

**Manual Hardening (If defusedxml Unavailable)**:

```python
import xml.etree.ElementTree as ET


def parse_safe_xml(filename):
    """Parse XML with XXE protection."""
    parser = ET.XMLParser()
    # Disable external entity loading
    parser.entity = {}
    parser.default_handler = None

    try:
        tree = ET.parse(filename, parser=parser)
        return tree
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}")
```

**For SAX Parsing**:

```python
import xml.sax
from defusedxml.sax import parse


class MyHandler(xml.sax.ContentHandler):
    def startElement(self, name, attrs):
        print(f"Element: {name}")


# RIGHT - Use defusedxml SAX
parse(untrusted_xml_file, MyHandler())
```

**For JSON/Web APIs** (Better Alternative):

```python
import json

# If you can use JSON instead of XML, do it
# JSON doesn't support entity expansion
data = json.loads(untrusted_json_string)
```

---

## Installation

```bash
pip install defusedxml
```

## Library Comparison

| Library                 | Vulnerable?     | Alternative                  |
| ----------------------- | --------------- | ---------------------------- |
| `xml.etree.ElementTree` | YES             | `defusedxml.ElementTree`     |
| `xml.sax`               | YES             | `defusedxml.sax`             |
| `xml.dom.minidom`       | YES             | `defusedxml.minidom`         |
| `xml.dom.pulldom`       | YES             | `defusedxml.pulldom`         |
| `xml.dom.expatbuilder`  | YES             | `defusedxml.expatbuilder`    |
| `lxml`                  | NO (by default) | OK, but verify configuration |

---

See also: [index.md](./index.md) for all Bandit security checks.
