# Documentation Images

This directory contains visual assets for the Pseudocode Translator documentation.

## Required Images

### Screenshots

1. **gui-main-window.png**
   - Main GUI window showing input/output panels
   - Should show example pseudocode and translated Python code
   - Include toolbar with model selector and translate button

2. **gui-translation-progress.png**
   - GUI during translation showing progress bar
   - Status messages visible

3. **gui-menu-options.png**
   - File menu expanded showing New, Open, Save options
   - Help menu visible

4. **cli-basic-usage.png**
   - Terminal showing basic command line usage
   - Example: `pseudocode-translator translate input.txt -o output.py`

5. **cli-help-output.png**
   - Output of `pseudocode-translator --help`
   - Shows all available commands and options

6. **cli-batch-processing.png**
   - Batch processing in action
   - Progress indicators and summary

### Diagrams

1. **architecture-diagram.png**
   - System architecture showing:
     - Parser → LLM Interface → Assembler → Validator
     - Model Manager and available models
     - Configuration system

2. **translation-pipeline.png**
   - Flow diagram of translation process:
     - Input → Parse → Translate → Assemble → Validate → Output
     - Show decision points and error handling

3. **streaming-architecture.png**
   - How streaming works for large files
   - Chunk processing and memory management
   - Buffer and queue visualization

4. **model-hierarchy.png**
   - BaseModel class and implementations
   - Plugin architecture for custom models

### Workflow Diagrams

1. **quick-start-flow.png**
   - Visual representation of 5-minute setup
   - Install → First translation → Success

2. **troubleshooting-flowchart.png**
   - Common issues and solution paths
   - Decision tree format

### Configuration Examples

1. **config-wizard.png**
   - Configuration wizard interface
   - Step-by-step setup process

2. **vscode-integration.png**
   - VS Code with pseudocode file open
   - Terminal showing translation command

## Image Guidelines

### Format
- PNG format for screenshots and diagrams
- SVG for logos and icons (if applicable)

### Size
- Screenshots: 1200px max width
- Diagrams: 800-1000px width
- Maintain aspect ratio

### Style
- Use consistent color scheme:
  - Primary: #4CAF50 (green)
  - Secondary: #2196F3 (blue)
  - Background: #1E1E1E (dark) or #FFFFFF (light)
- Add borders/shadows to screenshots
- Use clear, readable fonts

### Naming Convention
- Use lowercase with hyphens
- Descriptive names
- Include image type (screenshot, diagram, etc.)

## Creating Images

### Screenshots
1. Use consistent window size
2. Clear unnecessary clutter
3. Use meaningful example data
4. Highlight important areas with boxes/arrows

### Diagrams
1. Use draw.io, Lucidchart, or similar tools
2. Export as PNG with transparent background
3. Keep text readable at display size
4. Use consistent iconography

### Tools
- **Screenshots**: ShareX (Windows), Flameshot (Linux), CleanShot (macOS)
- **Diagrams**: draw.io, Lucidchart, Mermaid
- **Editing**: GIMP, Photoshop, Canva

## Usage in Documentation

Reference images in markdown files:

```markdown
![GUI Main Window](images/gui-main-window.png)
*Figure 1: Pseudocode Translator GUI showing translation in progress*
```

Always include:
- Alt text for accessibility
- Caption explaining the image
- Relative path from docs directory