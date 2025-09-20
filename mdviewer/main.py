from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import markdown
import json

app = FastAPI(title="Markdown Viewer")

# Configuration - change this to your markdown files directory
MARKDOWN_DIR = Path("./markdown_files")

# Ensure the markdown directory exists
MARKDOWN_DIR.mkdir(exist_ok=True)


def get_file_tree(directory: Path, relative_to: Optional[Path] = None) -> list:
    """Recursively build a tree structure of markdown files"""
    if relative_to is None:
        relative_to = directory

    items = []
    try:
        for item in sorted(directory.iterdir()):
            if item.is_file() and item.suffix.lower() == '.md':
                relative_path = item.relative_to(relative_to)
                items.append({
                    "name": item.name,
                    "path": str(relative_path),
                    "type": "file"
                })
            elif item.is_dir():
                subdirectory_items = get_file_tree(item, relative_to)
                if subdirectory_items:  # Only include directories with markdown files
                    items.append({
                        "name": item.name,
                        "path": str(item.relative_to(relative_to)),
                        "type": "directory",
                        "children": subdirectory_items
                    })
    except PermissionError:
        pass

    return items


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Markdown Viewer</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                height: 100vh;
                display: flex;
            }

            .sidebar {
                width: 300px;
                background: #f8f9fa;
                border-right: 1px solid #e9ecef;
                overflow-y: auto;
                padding: 20px;
            }

            .content {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                background: white;
            }

            .tree {
                list-style: none;
            }

            .tree-item {
                margin: 2px 0;
            }

            .tree-file {
                padding: 5px 8px;
                cursor: pointer;
                border-radius: 4px;
                transition: background-color 0.2s;
            }

            .tree-file:hover {
                background: #e9ecef;
            }

            .tree-file.selected {
                background: #007bff;
                color: white;
            }

            .tree-directory {
                font-weight: 600;
                padding: 5px 8px;
                cursor: pointer;
                user-select: none;
            }

            .tree-directory::before {
                content: "📁 ";
                margin-right: 5px;
            }

            .tree-directory.expanded::before {
                content: "📂 ";
            }

            .tree-file::before {
                content: "📄 ";
                margin-right: 5px;
            }

            .tree-children {
                margin-left: 20px;
                display: none;
            }

            .tree-children.expanded {
                display: block;
            }

            .loading {
                color: #6c757d;
                font-style: italic;
            }

            .error {
                color: #dc3545;
                background: #f8d7da;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
            }

            /* Markdown styling */
            .markdown-content h1, .markdown-content h2, .markdown-content h3 {
                margin-top: 20px;
                margin-bottom: 10px;
            }

            .markdown-content p {
                margin-bottom: 15px;
                line-height: 1.6;
            }

            .markdown-content code {
                background: #f8f9fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Monaco', 'Consolas', monospace;
            }

            .markdown-content pre {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                margin: 15px 0;
            }

            .markdown-content ul, .markdown-content ol {
                margin: 15px 0;
                padding-left: 30px;
            }

            .markdown-content blockquote {
                border-left: 4px solid #007bff;
                padding-left: 15px;
                margin: 15px 0;
                color: #6c757d;
            }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h3>Markdown Files</h3>
            <div id="tree-container">
                <div class="loading">Loading files...</div>
            </div>
        </div>
        <div class="content">
            <div id="markdown-content">
                <p style="color: #6c757d;">Select a markdown file from the tree to view its content.</p>
            </div>
        </div>

        <script>
            let selectedFile = null;

            async function loadFileTree() {
                try {
                    const response = await fetch('/api/files');
                    const files = await response.json();
                    renderTree(files);
                } catch (error) {
                    document.getElementById('tree-container').innerHTML =
                        '<div class="error">Error loading file tree</div>';
                }
            }

            function renderTree(items, container = null) {
                if (!container) {
                    container = document.getElementById('tree-container');
                    container.innerHTML = '';
                }

                const ul = document.createElement('ul');
                ul.className = 'tree';

                items.forEach(item => {
                    const li = document.createElement('li');
                    li.className = 'tree-item';

                    if (item.type === 'file') {
                        const div = document.createElement('div');
                        div.className = 'tree-file';
                        div.textContent = item.name;
                        div.onclick = () => selectFile(item.path, div);
                        li.appendChild(div);
                    } else {
                        const div = document.createElement('div');
                        div.className = 'tree-directory';
                        div.textContent = item.name;

                        const childrenContainer = document.createElement('div');
                        childrenContainer.className = 'tree-children';

                        div.onclick = () => toggleDirectory(div, childrenContainer);

                        li.appendChild(div);
                        li.appendChild(childrenContainer);

                        renderTree(item.children, childrenContainer);
                    }

                    ul.appendChild(li);
                });

                container.appendChild(ul);
            }

            function toggleDirectory(dirDiv, childrenContainer) {
                const isExpanded = childrenContainer.classList.contains('expanded');
                if (isExpanded) {
                    childrenContainer.classList.remove('expanded');
                    dirDiv.classList.remove('expanded');
                } else {
                    childrenContainer.classList.add('expanded');
                    dirDiv.classList.add('expanded');
                }
            }

            async function selectFile(filePath, element) {
                // Update selection styling
                if (selectedFile) {
                    selectedFile.classList.remove('selected');
                }
                element.classList.add('selected');
                selectedFile = element;

                // Load file content
                try {
                    const response = await fetch(`/api/file/${encodeURIComponent(filePath)}`);
                    if (response.ok) {
                        const html = await response.text();
                        document.getElementById('markdown-content').innerHTML = html;
                    } else {
                        document.getElementById('markdown-content').innerHTML =
                            '<div class="error">Error loading file content</div>';
                    }
                } catch (error) {
                    document.getElementById('markdown-content').innerHTML =
                        '<div class="error">Error loading file content</div>';
                }
            }

            // Load file tree on page load
            loadFileTree();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/files")
async def get_files():
    """API endpoint to get the file tree structure"""
    try:
        file_tree = get_file_tree(MARKDOWN_DIR)
        return JSONResponse(content=file_tree)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")


@app.get("/api/file/{file_path:path}")
async def get_file_content(file_path: str):
    """API endpoint to get rendered markdown content"""
    try:
        full_path = MARKDOWN_DIR / file_path

        # Security check: ensure the file is within the markdown directory
        if not str(full_path.resolve()).startswith(str(MARKDOWN_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        if full_path.suffix.lower() != '.md':
            raise HTTPException(status_code=400, detail="Not a markdown file")

        # Read and render markdown
        with open(full_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['extra', 'codehilite'])
        html_content = md.convert(markdown_content)

        return HTMLResponse(content=f'<div class="markdown-content">{html_content}</div>')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # Create some sample markdown files for testing
    sample_dir = MARKDOWN_DIR / "sample"
    sample_dir.mkdir(exist_ok=True)

    # Create sample files if they don't exist
    sample_files = {
        "README.md": "# Welcome\n\nThis is a sample markdown file.\n\n## Features\n\n- File tree navigation\n- Live markdown rendering\n- Responsive design",
        "sample/hello.md": "# Hello World\n\nThis is in a subdirectory.\n\n```python\nprint('Hello, World!')\n```",
        "sample/example.md": "# Example Document\n\n> This is a blockquote\n\n1. First item\n2. Second item\n3. Third item"
    }

    for file_path, content in sample_files.items():
        full_path = MARKDOWN_DIR / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

    uvicorn.run(app, host="0.0.0.0", port=8700)
