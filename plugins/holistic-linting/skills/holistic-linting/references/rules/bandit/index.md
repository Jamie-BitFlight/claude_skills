# Bandit Security Check Codes Reference

Bandit is a static analysis security tool for Python that identifies common security issues in code. This reference documents all Bandit security checks organized by vulnerability category.

## How to Use This Reference

Each Bandit finding includes:

- **Check Code** (e.g., B101) - Unique identifier for the security issue
- **Security Risk** - What vulnerability it detects
- **Severity Level** - LOW, MEDIUM, or HIGH
- **When It Applies** - Code patterns that trigger the check
- **When It Doesn't Apply** - Safe usage patterns where the check may be disabled
- **Vulnerable Code Examples** - Real examples of problematic patterns
- **Secure Code Examples** - How to fix the issue properly

## Security Check Categories

### Credentials and Secrets Management

Hardcoded passwords, API keys, and other secrets in source code.

- [B105: Hardcoded Password String](./credentials-secrets.md#b105-hardcoded_password_string)
- [B106: Hardcoded Password Function Argument](./credentials-secrets.md#b106-hardcoded_password_funcarg)
- [B107: Hardcoded Password Default Value](./credentials-secrets.md#b107-hardcoded_password_default)
- [B109: Password Config Option Not Marked Secret](./credentials-secrets.md#b109-password_config_option_not_marked_secret)
- [B401: Import Telnetlib (Contains Secrets Risk)](./credentials-secrets.md#b401-import_telnetlib)
- [B402: Import FTPlib (Contains Secrets Risk)](./credentials-secrets.md#b402-import_ftplib)

### Cryptography

Weak cryptographic algorithms, insufficient key sizes, and insecure hashing.

- [B303: MD5 and Weak Hash Functions](./cryptography.md#b303-md5-and-weak-hash-functions)
- [B304: Insecure Cipher](./cryptography.md#b304-insecure-cipher)
- [B305: Insecure Cipher Mode](./cryptography.md#b305-insecure-cipher-mode)
- [B324: Hashlib with Insecure Configuration](./cryptography.md#b324-hashlib-insecure-configuration)
- [B505: Weak Cryptographic Key](./cryptography.md#b505-weak-cryptographic-key)

### SSL/TLS Configuration

Insecure SSL/TLS versions, bad defaults, and missing certificate validation.

- [B501: Request with No Certificate Validation](./ssl-tls.md#b501-request_with_no_cert_validation)
- [B502: SSL with Bad Version](./ssl-tls.md#b502-ssl_with_bad_version)
- [B503: SSL with Bad Defaults](./ssl-tls.md#b503-ssl_with_bad_defaults)
- [B504: SSL with No Version](./ssl-tls.md#b504-ssl_with_no_version)
- [B507: SSH No Host Key Verification](./ssl-tls.md#b507-ssh_no_host_key_verification)
- [B508: SNMP Insecure Version](./ssl-tls.md#b508-snmp_insecure_version)
- [B509: SNMP Weak Cryptography](./ssl-tls.md#b509-snmp_weak_cryptography)

### Deserialization Vulnerabilities

Unsafe deserialization of untrusted data from pickle, marshal, YAML, etc.

- [B301: Pickle/Dill/Shelve Deserialization](./deserialization.md#b301-pickle-deserialization)
- [B302: Marshal Deserialization](./deserialization.md#b302-marshal-deserialization)
- [B506: YAML Load](./deserialization.md#b506-yaml_load)

### Injection Vulnerabilities

SQL injection, command injection, and shell injection attacks.

- [B602: Subprocess with shell=True](./injection-command.md#b602-subprocess_popen_with_shell_equals_true)
- [B603: Subprocess without shell=True](./injection-command.md#b603-subprocess_without_shell_equals_true)
- [B604: Any Other Function with shell=True](./injection-command.md#b604-any_other_function_with_shell_equals_true)
- [B605: Start Process with Shell](./injection-command.md#b605-start_process_with_a_shell)
- [B606: Start Process without Shell](./injection-command.md#b606-start_process_with_no_shell)
- [B607: Start Process with Partial Path](./injection-command.md#b607-start_process_with_partial_path)
- [B608: Hardcoded SQL Expression](./injection-command.md#b608-hardcoded_sql_expressions)
- [B609: Linux Commands Wildcard Injection](./injection-command.md#b609-linux_commands_wildcard_injection)
- [B610: Django Extra Used](./injection-command.md#b610-django_extra_used)
- [B611: Django RawSQL Used](./injection-command.md#b611-django_rawsql_used)
- [B614: PyTorch Unsafe Load](./injection-command.md#b614-pytorch_load)
- [B615: Hugging Face Unsafe Download](./injection-command.md#b615-huggingface_unsafe_download)

### XML Parsing

Vulnerable XML parsing that allows entity expansion and external entity attacks.

- [B313: XML ElementTree Vulnerable](./xml-parsing.md#b313-xml-etree)
- [B314: XML SAX Vulnerable](./xml-parsing.md#b314-xml-sax)
- [B315: XML Expat Vulnerable](./xml-parsing.md#b315-xml-expat)
- [B316: XML Minidom Vulnerable](./xml-parsing.md#b316-xml-minidom)
- [B317: XML Pulldom Vulnerable](./xml-parsing.md#b317-xml-pulldom)
- [B318: XML Sax Parse](./xml-parsing.md#b318-xml-sax-parse)
- [B319: XML DOM Parsing Vulnerable](./xml-parsing.md#b319-xml-dom-minidom-parse)
- [B405: Import xml.etree Vulnerable](./xml-parsing.md#b405-import-xml-etree)
- [B406: Import xml.sax Vulnerable](./xml-parsing.md#b406-import-xml-sax)
- [B407: Import xml.dom.expatbuilder](./xml-parsing.md#b407-import-xml-dom-expatbuilder)
- [B408: Import xml.dom.minidom](./xml-parsing.md#b408-import-xml-dom-minidom)
- [B409: Import xml.dom.pulldom](./xml-parsing.md#b409-import-xml-dom-pulldom)

### File Permissions and Temporary Files

Overly permissive file permissions and insecure temporary file handling.

- [B103: Set Bad File Permissions](./file-permissions.md#b103-set_bad_file_permissions)
- [B104: Hardcoded Bind All Interfaces](./file-permissions.md#b104-hardcoded_bind_all_interfaces)
- [B306: MkTemp Usage](./file-permissions.md#b306-mktemp)
- [B325: Tempnam Usage](./file-permissions.md#b325-tempnam)

### Unsafe Built-in Functions

Use of Python built-ins that can execute arbitrary code or bypass security checks.

- [B101: Assert Used](./unsafe-functions.md#b101-assert_used)
- [B102: Exec Used](./unsafe-functions.md#b102-exec_used)
- [B307: Use of eval()](./unsafe-functions.md#b307-eval)
- [B310: URL Open with Dangerous Schemes](./unsafe-functions.md#b310-urllib_urlopen)
- [B311: Use of random for Security](./unsafe-functions.md#b311-random)

### Framework and Application Configuration

Insecure configurations in web frameworks and applications.

- [B201: Flask Debug True](./framework-config.md#b201-flask_debug_true)
- [B202: Tarfile Unsafe Members](./framework-config.md#b202-tarfile_unsafe_members)
- [B612: Logging Config Insecure Listen](./framework-config.md#b612-logging_config_insecure_listen)
- [B701: Jinja2 Autoescape False](./framework-config.md#b701-jinja2_autoescape_false)
- [B702: Use of Mako Templates](./framework-config.md#b702-use_of_mako_templates)
- [B703: Django Mark Safe](./framework-config.md#b703-django_mark_safe)
- [B704: Markupsafe Markup XSS](./framework-config.md#b704-markupsafe_markup_xss)

### Module Imports

Dangerous or insecure module imports that indicate security risks.

- [B403: Import Pickle](./module-imports.md#b403-import_pickle)
- [B404: Import Subprocess](./module-imports.md#b404-import_subprocess)
- [B411: Import XMLRPC](./module-imports.md#b411-import_xmlrpclib)
- [B412: Import HTTPoxy (CGI Handler)](./module-imports.md#b412-import_httpoxy)
- [B413: Import PyCrypto](./module-imports.md#b413-import_pycrypto)
- [B415: Import PyGHMI](./module-imports.md#b415-import_pyghmi)

### Miscellaneous Security Issues

Other security-related patterns that don't fit other categories.

- [B108: Hardcoded Temporary Directory](./miscellaneous.md#b108-hardcoded_tmp_directory)
- [B110: Try/Except Pass](./miscellaneous.md#b110-try_except_pass)
- [B111: Execute with Run as Root](./miscellaneous.md#b111-execute_with_run_as_root_equals_true)
- [B112: Try/Except Continue](./miscellaneous.md#b112-try_except_continue)
- [B113: Request Without Timeout](./miscellaneous.md#b113-request_without_timeout)
- [B613: Trojan Source](./miscellaneous.md#b613-trojansource)

## Severity Levels

Bandit classifies findings with severity levels that help prioritize fixes:

- **HIGH** - Critical security vulnerabilities that should be fixed immediately
- **MEDIUM** - Significant security risks that need remediation
- **LOW** - Security hygiene issues or configuration patterns that could lead to problems

## Quick Reference by Code Range

| Range     | Category                             |
| --------- | ------------------------------------ |
| B101-B113 | Misc security tests and built-ins    |
| B201-B202 | Framework misconfiguration           |
| B301-B325 | Deserialization and unsafe functions |
| B401-B415 | Dangerous module imports             |
| B501-B509 | SSL/TLS and cryptography             |
| B601-B615 | Injection vulnerabilities            |
| B701-B704 | XSS and template security            |

## Using These References

When Bandit reports a security issue:

1. **Find the check code** (e.g., B608)
2. **Navigate to the category** using the links above
3. **Review the vulnerable example** to understand the problem
4. **Study the secure example** to see the recommended fix
5. **Understand when it applies** to decide if it's a false positive
6. **Apply the fix** to your code

## Related Documentation

For linting root-cause resolution workflows, see the [holistic-linting](../../../SKILL.md) skill, which the linting-root-cause-resolver agent loads.

For integration with Ruff (which includes Bandit checks in the "S" category), refer to Ruff's security plugin documentation.

---

**Last Updated**: November 2024 **Source**: [Bandit Official Documentation](https://bandit.readthedocs.io/)
