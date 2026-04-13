# QMD Installation Summary

## Installation Status: ✅ COMPLETE

**Date**: April 13, 2026  
**Project**: construction-monitor-demo  
**QMD Version**: 2.1.0  

## What Was Installed

### 1. QMD Core Package
- Installed `@tobilu/qmd@2.1.0` globally via npm
- Created PowerShell wrapper function for easy CLI access

### 2. Project Collections
The following collections are now indexed and searchable:

| Collection | Path | Documents | Context |
|------------|------|-----------|---------|
| `docs` | `docs/` | 29 files | Requirements, architecture, workflows, design, and implementation documentation |
| `demo` | `demo/` | 0 files | Demo scripts and content for recording video tutorials |

### 3. QMD Daemon
- **Status**: ✅ Running
- **Port**: 8181
- **MCP Endpoint**: `http://localhost:8181/mcp`
- **Auto-start**: Configured via Windows startup shortcuts

### 4. VS Code Integration

#### Updated Files:
1. **`.vscode/settings.json`**
   - Added `search.exclude` for QMD-indexed folders
   - Prevents Copilot from reading docs directly (uses MCP instead)

2. **`.github/copilot-instructions.md`**
   - Added two-tier QMD architecture documentation
   - Instructs Copilot to use `mcp_qmd_query` for documentation searches

## How to Use QMD

### Via VS Code (Recommended)
1. **Reload VS Code Window**: Press `Ctrl+Shift+P` → "Developer: Reload Window"
2. The QMD MCP tools will be available with `mcp_qmd_*` prefix
3. Copilot will automatically use QMD for documentation queries

### Via Command Line
```powershell
# Define the qmd function in your PowerShell session
function qmd {
    $env:XDG_CACHE_HOME = 'C:\tmp\.cache'
    $env:NODE_NO_WARNINGS = '1'
    & node "$env:APPDATA\npm\node_modules\@tobilu\qmd\dist\cli\qmd.js" @args
}

# Search documentation
qmd search "deployment"

# Query with semantic search
qmd query "how to deploy the application"

# List collections
qmd collection list

# Update index after adding new docs
qmd update

# Generate embeddings for new content
qmd embed
```

### Testing the Installation
Run the test script to verify everything is working:
```powershell
.\tools\test-qmd.ps1
```

Expected output:
- ✓ QMD version 2.1.0
- ✓ Daemon running on port 8181
- ✓ Collections: docs, demo
- ✓ MCP server responding

## What QMD Does

QMD provides **hybrid semantic + keyword search** across your project documentation:

1. **BM25 keyword search**: Fast exact-match searching
2. **Vector embeddings**: Semantic similarity search
3. **LLM reranking**: Context-aware result ranking
4. **MCP integration**: Seamless Copilot access via Model Context Protocol

## Collection Configuration

Your project configuration is stored in `qmd-collections.json`:
```json
{
  "globalContext": "External customer-vendor delivery governance system...",
  "collections": [
    {
      "name": "docs",
      "path": "docs",
      "context": "requirements, architecture, workflows, design, and implementation documentation..."
    },
    {
      "name": "demo",
      "path": "demo",
      "context": "demo scripts and content for recording video tutorial..."
    }
  ]
}
```

## Maintenance

### Adding New Documents
QMD automatically indexes markdown files in the configured paths. After adding new docs:
```powershell
qmd update  # Update index
qmd embed   # Generate embeddings (if needed)
```

### Adding New Collections
1. Edit `qmd-collections.json` to add new collection
2. Run `Install-QmdProject.ps1` again with `-Force` flag:
   ```powershell
   C:\Users\maged\.copilot\qmd-setup\Install-QmdProject.ps1 -Force
   ```

## Troubleshooting

### QMD command not found
The `qmd` command requires the PowerShell function wrapper. Add this to your PowerShell profile:
```powershell
function global:qmd {
    $env:XDG_CACHE_HOME = 'C:\tmp\.cache'
    $env:NODE_NO_WARNINGS = '1'
    & node "$env:APPDATA\npm\node_modules\@tobilu\qmd\dist\cli\qmd.js" @args
}
```

### Daemon not running
Start the daemon manually:
```powershell
$env:XDG_CACHE_HOME = 'C:\tmp\.cache'
$env:NODE_NO_WARNINGS = '1'
$qmdJs = "$env:APPDATA\npm\node_modules\@tobilu\qmd\dist\cli\qmd.js"
Start-Process -FilePath 'node' -ArgumentList "`"$qmdJs`" mcp --http --port 8181 --daemon" -WindowStyle Hidden
```

### MCP tools not showing in VS Code
1. Verify daemon is running: `netstat -ano | findstr :8181`
2. Check VS Code MCP config: `%APPDATA%\Code\User\mcp.json`
3. Reload VS Code window

## Next Steps

1. **Reload VS Code** to activate MCP integration
2. Try asking Copilot: "What's in the architecture documentation?"
3. Add more markdown files to `docs/` or `demo/` - they'll be auto-indexed
4. Run `qmd update` periodically to refresh the index

## Files Created

- `tools/test-qmd.ps1` - QMD test script
- `docs/QMD_INSTALLATION.md` - This document

## References

- QMD Documentation: Via `qmd --help`
- MCP Protocol: https://modelcontextprotocol.io
- Installation Scripts: `C:\Users\maged\.copilot\qmd-setup\`

---

**Status**: Ready for production use ✅
