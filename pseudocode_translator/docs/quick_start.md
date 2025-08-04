# Quick Start Guide - Get Started in 5 Minutes! 🚀

Welcome! This guide will have you translating pseudocode to Python in under 5 minutes. Let's jump right in!

## 1. Install (1 minute)

Open your terminal and run:

```bash
pip install pseudocode-translator
```

That's it! The default model will download automatically on first use.

## 2. Your First Translation (30 seconds)

### Option A: Command Line

```bash
echo "create a function that says hello to a name" | pseudocode-translator
```

Output:
```python
def say_hello(name):
    """Say hello to a name."""
    return f"Hello, {name}!"
```

### Option B: Interactive GUI

```bash
pseudocode-translator-gui
```

Then type your pseudocode and click "Translate" or press `Ctrl+Enter`.

## 3. Translate a File (1 minute)

Create a file `ideas.txt`:

```text
create a calculator class that can:
- add two numbers
- subtract two numbers
- multiply two numbers
- divide two numbers (handle division by zero)
```

Translate it:

```bash
pseudocode-translator translate ideas.txt -o calculator.py
```

## 4. Mix English and Python (30 seconds)

Create `mixed.txt`:

```python
def process_list(items):
    # remove duplicates and sort the list
    
    # filter out negative numbers
    
    # return the sum of remaining numbers
```

Translate it:

```bash
pseudocode-translator translate mixed.txt -o processed.py
```

## 5. Use in Your Python Code (2 minutes)

Create `quick_demo.py`:

```python
from pseudocode_translator import PseudocodeTranslatorAPI

# Initialize translator
translator = PseudocodeTranslatorAPI()

# Translate pseudocode
pseudocode = """
create a function called is_palindrome that:
- takes a string as input
- ignores spaces and case
- returns True if it reads the same forwards and backwards
- returns False otherwise
"""

result = translator.translate(pseudocode)

# Print the generated code
print(result.code)

# Save to file
with open("palindrome.py", "w") as f:
    f.write(result.code)
```

Run it:

```bash
python quick_demo.py
```

## Common Quick Tasks

### Generate a Class

```bash
echo "create a Person class with name and age, and a method to introduce themselves" | pseudocode-translator
```

### Create an Algorithm

```bash
echo "implement bubble sort for a list of numbers" | pseudocode-translator
```

### Build a Function

```bash
echo "function to validate email addresses using regex" | pseudocode-translator
```

### Data Processing

```bash
echo "read a CSV file, filter rows where age > 18, save to new file" | pseudocode-translator
```

## Quick Tips for Better Results

### 1. Be Specific
❌ "make a sort function"  
✅ "create a function that sorts a list of numbers in ascending order"

### 2. Mention Edge Cases
❌ "divide two numbers"  
✅ "divide two numbers, return None if dividing by zero"

### 3. Specify Types When Needed
❌ "add items"  
✅ "add two integers and return the sum"

### 4. Use Natural Language
- "create a function called..." ✅
- "make a class that..." ✅
- "implement an algorithm to..." ✅
- "def func():" (just write Python) ✅

## GUI Quick Features

Launch GUI:
```bash
pseudocode-translator-gui
```

**Keyboard Shortcuts:**
- `Ctrl+Enter` - Translate
- `Ctrl+S` - Save file
- `Ctrl+O` - Open file
- `F5` - Re-translate

## What's Next? (30 seconds to explore)

### Try Different Models
```bash
# Faster, simpler translations
pseudocode-translator translate ideas.txt --model gpt2

# More complex code generation
pseudocode-translator translate ideas.txt --model codegen
```

### Explore Examples
```bash
# List available examples
ls ~/.local/share/pseudocode_translator/examples/

# Try an example
pseudocode-translator translate ~/.local/share/pseudocode_translator/examples/web_scraper.txt
```

### Get Help
```bash
# See all options
pseudocode-translator --help

# Get detailed command help
pseudocode-translator translate --help
```

## Troubleshooting Quick Fixes

### Model Download Issues
```bash
# Manual download
pseudocode-translator download-model qwen
```

### Slow Performance
```bash
# Use a faster model
pseudocode-translator translate input.txt --model gpt2
```

### Out of Memory
```bash
# Enable streaming for large files
pseudocode-translator translate large_file.txt --stream
```

## 🎉 Congratulations!

You're now ready to transform your ideas into code! Here are your next steps:

1. **[Read the User Guide](user_guide.md)** - Master advanced features
2. **[Check out Examples](../examples/)** - See what's possible
3. **[Configure Settings](configuration_guide.md)** - Customize your experience

## One-Liner Cheat Sheet

```bash
# Basic translation
echo "your idea here" | pseudocode-translator

# File translation
pseudocode-translator translate input.txt -o output.py

# GUI mode
pseudocode-translator-gui

# Use specific model
pseudocode-translator translate input.txt --model gpt2

# Get help
pseudocode-translator --help
```

---

**Remember**: Think in ideas, not syntax. Let the translator handle the details! 🚀