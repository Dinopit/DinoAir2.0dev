# 🛡️ DinoAir Security Testing Suite

Comprehensive red team testing framework for DinoAir's GUI and InputSanitizer components.

## Overview

This security testing suite implements automated red team testing to identify vulnerabilities in:
- **InputSanitizer**: Path traversal, command injection, XSS, encoding bypasses
- **GUI Components**: Rendering attacks, memory exhaustion, format strings
- **Rate Limiting**: Bypass attempts and DoS prevention
- **Unicode Handling**: Homoglyphs, RTL attacks, normalization issues

## Quick Start

### Run All Security Tests
```bash
python tests/security/run_security_tests.py
```

### Run Specific Category
```bash
python tests/security/run_security_tests.py -c path_traversal command_injection
```

### List Available Categories
```bash
python tests/security/run_security_tests.py --list
```

## Test Categories

### 1. Path Traversal
Tests for directory traversal vulnerabilities:
- Basic traversal (`../etc/passwd`)
- Double/triple encoding (`%252e%252e%252f`)
- Unicode encoding (`..%c0%af`)
- Mixed separators (`..//..//`)
- UNC paths (`\\server\share`)
- Null bytes (`file.txt%00`)

### 2. Command Injection
Tests for command execution vulnerabilities:
- Command separators (`;`, `|`, `&`)
- Command substitution (`` ` ``, `$()`)
- Environment variables (`${PATH}`)
- IFS bypass techniques
- Newline injection

### 3. XSS (Cross-Site Scripting)
Tests for script injection:
- Script tags (`<script>`)
- Event handlers (`onerror`, `onload`)
- JavaScript URLs (`javascript:`)
- Data URLs
- Encoded payloads

### 4. Unicode Attacks
Tests for Unicode-based vulnerabilities:
- Homoglyphs (lookalike characters)
- RTL/LTR overrides
- Zero-width characters
- Normalization attacks
- Combining characters

### 5. Null Byte Injection
Tests for null byte handling:
- Extension bypass (`file.txt\x00.jpg`)
- Path truncation
- URL encoded nulls

### 6. Buffer Overflow
Tests for memory exhaustion:
- Large inputs (10K+ characters)
- Deep nesting
- Emoji floods
- Pattern repetition

### 7. Rate Limiting
Tests rate limiting effectiveness:
- Rapid fire requests
- Bypass attempts
- DoS prevention

## Security Grading

The suite assigns security grades based on block rates:
- **A**: 99%+ blocked (Excellent)
- **B**: 95-98% blocked (Good)
- **C**: 90-94% blocked (Fair)
- **D**: 80-89% blocked (Poor)
- **F**: <80% blocked (Failing)

## Reports

Test results are saved to `tests/security/reports/` with:
- **JSON Reports**: Machine-readable detailed results
- **HTML Reports**: Human-readable reports with visualizations
- **Bypass Details**: Specific payloads that bypassed security
- **Recommendations**: Actionable security improvements

## GUI Testing

The GUI security tests (`gui_security_tests.py`) specifically test:
- Chat input component resilience
- Notification widget security
- File operation path validation
- Rendering attack prevention
- Memory exhaustion handling

## Payload Database

Attack payloads are stored in `payloads/attack_payloads.json`:
- Categorized by attack type
- OS-specific variants
- Severity ratings
- Extensible format

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Security Tests
  run: |
    python tests/security/run_security_tests.py
  continue-on-error: false
```

### Pre-commit Hook
```bash
#!/bin/bash
python tests/security/run_security_tests.py -c path_traversal command_injection
```

## Adding Custom Tests

### 1. Add to Payload Database
```json
{
  "custom_category": {
    "description": "Custom attack vectors",
    "payloads": [
      {
        "vector": "your_payload_here",
        "description": "What it tests",
        "severity": "high"
      }
    ]
  }
}
```

### 2. Add Test Method
```python
def _test_custom_attacks(self):
    """Test custom attack vectors."""
    print("\n🔍 Testing Custom Attacks...")
    
    payloads = [
        ("payload", "description"),
    ]
    
    self._run_payload_tests(payloads, "Custom")
```

## Security Best Practices

### For Developers
1. **Always validate input** at the earliest possible stage
2. **Use allowlists** instead of blocklists where possible
3. **Normalize Unicode** before processing
4. **Escape output** based on context (HTML, URL, etc.)
5. **Implement rate limiting** on all user inputs
6. **Log security events** for monitoring

### For Security Testing
1. **Run tests regularly** (daily in CI/CD)
2. **Update payloads** with new attack vectors
3. **Monitor for bypasses** and fix immediately
4. **Review security grades** trends over time
5. **Test after updates** to dependencies

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the project root
cd /path/to/DinoAir2.0dev
python tests/security/run_security_tests.py
```

**GUI Tests Failing**
- Requires display (use `xvfb-run` on headless systems)
- Check Qt dependencies are installed

**Rate Limit Tests**
- May need adjustment based on system performance
- Configure timeouts in test settings

## References

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security)

## Contributing

To contribute new attack vectors:
1. Add payloads to `attack_payloads.json`
2. Update test methods if needed
3. Document the attack vector
4. Submit PR with test results

## License

Part of the DinoAir project. See main project license.