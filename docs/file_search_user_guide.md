# DinoAir 2.0 File Search User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Key Features](#key-features)
4. [Using File Search](#using-file-search)
5. [Search Tips & Best Practices](#search-tips--best-practices)
6. [Managing Indexed Files](#managing-indexed-files)
7. [Security & Privacy](#security--privacy)
8. [Performance Tuning](#performance-tuning)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Introduction

DinoAir's File Search feature uses advanced RAG (Retrieval-Augmented Generation) technology to help you find information across your documents quickly and intelligently. Unlike traditional file search, our system understands the context and meaning of your queries, delivering more relevant results.

### What makes it special?
- **Semantic Search**: Finds content based on meaning, not just keywords
- **Multi-format Support**: Works with PDFs, Word documents, text files, code, and more
- **Smart Context**: Provides surrounding context for better understanding
- **Local & Private**: All processing happens on your computer - your data never leaves your machine

---

## Getting Started

### First-Time Setup

1. **Open DinoAir 2.0** and navigate to the File Search tab
2. **Set up search directories**:
   - Click "Add Directory" to include folders you want to search
   - Use "Exclude Directory" to skip sensitive or system folders
3. **Start indexing**:
   - Click "Index Files" to begin processing your documents
   - The first indexing may take some time depending on file count

### Quick Start
```
1. Type your search query in the search box
2. Press Enter or click "Search"
3. Browse results with context highlights
4. Click any result to view the full document
```

---

## Key Features

### 1. **Hybrid Search Technology**
Combines three powerful search methods:
- **Vector Search**: Finds semantically similar content
- **Keyword Search**: Exact matches for specific terms
- **Hybrid Mode**: Best of both worlds (recommended)

### 2. **Smart File Processing**
- Automatic text extraction from various formats
- Intelligent chunking preserves context
- Background file monitoring for changes

### 3. **Rich Search Results**
- Context snippets show surrounding text
- Relevance scoring helps you find the best matches
- File metadata (type, size, modified date)
- Quick preview without opening files

### 4. **Advanced Filtering**
- Filter by file type (PDFs, docs, code, etc.)
- Date range filtering
- Directory-specific searches
- Size constraints

---

## Using File Search

### Basic Search

1. **Simple Query**
   ```
   Example: "project timeline"
   Finds: Documents mentioning project schedules, deadlines, milestones
   ```

2. **Question Format**
   ```
   Example: "What are the Q3 sales targets?"
   Finds: Relevant information about quarterly sales goals
   ```

3. **Technical Search**
   ```
   Example: "Python error handling"
   Finds: Code files and documentation about exception handling
   ```

### Advanced Search Options

#### Search Modes
- **Semantic** (🧠): Best for concepts and ideas
- **Keyword** (🔤): Best for exact terms
- **Hybrid** (🔀): Balanced approach (default)

#### File Type Filters
```
✓ Documents (.pdf, .docx, .txt)
✓ Code (.py, .js, .java, etc.)
✓ Data (.csv, .json, .xml)
✓ Markdown (.md)
```

#### Search Operators
- Use quotes for exact phrases: `"quarterly report 2024"`
- Combine terms: `budget AND forecast`
- Exclude terms: `meeting NOT cancelled`

### Understanding Results

Each search result shows:
```
📄 Filename.pdf
├─ Relevance: 95% ⭐⭐⭐⭐⭐
├─ File path: /Documents/Reports/
├─ Modified: 2024-07-15
└─ Context: "...your search term appears here with surrounding text..."
```

**Relevance Indicators:**
- ⭐⭐⭐⭐⭐ (90-100%): Excellent match
- ⭐⭐⭐⭐ (70-89%): Good match
- ⭐⭐⭐ (50-69%): Fair match
- ⭐⭐ (30-49%): Weak match

---

## Search Tips & Best Practices

### 🎯 For Best Results

1. **Be Specific**
   - ❌ "report"
   - ✅ "Q2 financial report 2024"

2. **Use Natural Language**
   - ❌ "error log python"
   - ✅ "How to fix Python import errors"

3. **Try Different Phrasings**
   - "customer feedback"
   - "client reviews"
   - "user testimonials"

### 📊 Search Strategies

#### Finding Code
```
Strategy: Use function names, error messages, or comments
Example: "calculateTotalPrice function"
Tip: Enable code file filter for faster results
```

#### Finding Documents
```
Strategy: Use document titles, topics, or key phrases
Example: "meeting minutes product launch"
Tip: Add date ranges for recent documents
```

#### Research & Analysis
```
Strategy: Ask questions or describe what you need
Example: "competitor analysis smartphone market"
Tip: Use hybrid search for comprehensive results
```

---

## Managing Indexed Files

### Indexing Status Panel

The indexing status shows:
- **Total Files**: Number of files in your search index
- **Last Updated**: When the index was last refreshed
- **Index Size**: Storage used by the search index
- **Processing**: Current indexing activity

### Directory Management

#### Adding Directories
1. Click "Manage Directories"
2. Select "Add Directory"
3. Browse to the folder you want to include
4. Click "Add" to confirm

#### Excluding Directories
Use exclusions for:
- System folders (Windows, Program Files)
- Temporary directories
- Version control folders (.git, .svn)
- Large media collections
- Sensitive data folders

#### Best Practices
- **Start Small**: Begin with a few important directories
- **Organize First**: Clean up folders before indexing
- **Regular Updates**: Re-index monthly or after major changes
- **Monitor Performance**: Remove rarely-searched directories

### File Type Management

Control which files are indexed:
```
Essential File Types:
✓ Documents (.pdf, .docx, .txt)
✓ Spreadsheets (.xlsx, .csv)
✓ Presentations (.pptx)
✓ Code files (various extensions)

Optional Types:
○ Images (with OCR enabled)
○ Archives (.zip, .tar)
○ Email files (.eml, .msg)
```

---

## Security & Privacy

### 🔒 Your Data is Safe

1. **100% Local Processing**
   - No cloud uploads
   - No external API calls
   - No data sharing

2. **Access Control**
   - Respects file system permissions
   - Directory access restrictions
   - User-specific indexes

3. **Data Encryption**
   - Encrypted index storage
   - Secure file access
   - Protected search history

### Privacy Settings

Configure privacy options in Settings > File Search:
- **Clear search history**: Remove past queries
- **Exclude patterns**: Skip files matching patterns
- **Index encryption**: Enable/disable index encryption
- **Auto-cleanup**: Remove orphaned index entries

---

## Performance Tuning

### Optimization Settings

#### For Faster Indexing
```
Chunk Size: 500 characters (smaller = more precise)
Batch Size: 32 files (larger = faster processing)
Workers: 4 threads (match CPU cores)
```

#### For Better Search Results
```
Results Limit: 20 (more results = slower)
Context Length: 200 characters
Similarity Threshold: 0.7 (lower = more results)
```

### Performance Tips

1. **Initial Indexing**
   - Run during off-hours
   - Start with essential directories
   - Disable real-time monitoring initially

2. **Search Performance**
   - Use file type filters
   - Limit search to specific directories
   - Clear cache periodically

3. **System Resources**
   - Close other applications during initial indexing
   - Ensure adequate disk space (10% of indexed data)
   - Consider SSD for index storage

---

## Troubleshooting

### Common Issues

#### "No results found"
**Causes & Solutions:**
- Files not indexed yet → Check indexing status
- Query too specific → Try broader terms
- Wrong search mode → Switch to hybrid search
- Files excluded → Check directory settings

#### "Indexing is slow"
**Solutions:**
1. Reduce batch size in settings
2. Exclude large binary files
3. Index in smaller batches
4. Check available disk space

#### "Search is slow"
**Solutions:**
1. Reduce number of results
2. Use file type filters
3. Search specific directories
4. Clear search cache

#### "Files not updating"
**Solutions:**
1. Check file monitor status
2. Manually refresh index
3. Verify directory permissions
4. Re-add the directory

### Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "Access Denied" | No permission to read file | Check file permissions |
| "File Too Large" | Exceeds size limit | Adjust max file size setting |
| "Unsupported Format" | Can't extract text | Convert to supported format |
| "Index Corrupted" | Database error | Rebuild index from settings |

---

## FAQ

### General Questions

**Q: How much disk space does indexing use?**
A: Typically 5-10% of the indexed content size. A 10GB document collection needs about 0.5-1GB for the index.

**Q: Can I search while indexing is running?**
A: Yes! You can search already-indexed files while new files are being processed.

**Q: Does it work with cloud storage folders?**
A: Yes, if they're synced locally (OneDrive, Dropbox, Google Drive).

**Q: What languages are supported?**
A: Currently optimized for English, with basic support for other languages.

### Search Questions

**Q: Why are some results marked as "cached"?**
A: Recently accessed files are cached for faster retrieval. This doesn't affect search quality.

**Q: Can I export search results?**
A: Yes, right-click results and select "Export to CSV" or "Copy Results".

**Q: How do I search for exact file names?**
A: Use quotes around the filename: `"report_2024_final.pdf"`

**Q: Can I save searches?**
A: Yes, click the star icon next to the search box to save queries.

### Technical Questions

**Q: Which file formats are supported?**
A: PDF, DOCX, TXT, MD, RTF, and most programming languages. See Settings > Supported Formats for the full list.

**Q: Can I index network drives?**
A: Yes, but performance depends on network speed. Consider copying files locally for better performance.

**Q: Is there a file size limit?**
A: Default is 50MB per file. You can adjust this in Settings > Performance.

**Q: How often should I rebuild the index?**
A: Only when experiencing issues. Regular updates happen automatically.

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Focus search | `Ctrl+F` |
| Clear search | `Esc` |
| Next result | `↓` or `Tab` |
| Previous result | `↑` or `Shift+Tab` |
| Open result | `Enter` |
| New search | `Ctrl+N` |
| Toggle filters | `Ctrl+Shift+F` |
| Refresh index | `F5` |

---

## Getting Help

If you need additional assistance:

1. **In-App Help**: Click the ? icon in File Search
2. **Tooltips**: Hover over any button for explanations
3. **Settings**: Detailed descriptions for each option
4. **Support**: File an issue in the DinoAir repository

---

## Tips for Power Users

### Advanced Techniques

1. **Regular Expressions**
   ```
   Enable in Settings > Advanced
   Example: \b\d{3}-\d{4}\b finds phone numbers
   ```

2. **Custom File Parsers**
   ```
   Add extractors for proprietary formats
   See Developer Guide for details
   ```

3. **Batch Operations**
   ```
   Select multiple results:
   - Ctrl+Click: Individual selection
   - Shift+Click: Range selection
   - Ctrl+A: Select all
   ```

4. **Search Macros**
   ```
   Create reusable search templates:
   @weekly: "meeting minutes" date:last_week
   @code: type:code language:python
   ```

### Integration Features

- **Chat Integration**: Reference search results in chat conversations
- **Note Links**: Link search results to notes
- **Quick Actions**: Right-click menu for common operations
- **Export Options**: Save results as JSON, CSV, or Markdown

---

*Last updated: July 2024 | Version 2.0*