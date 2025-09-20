from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown

app = FastAPI(title="Markdown Viewer")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
async def root(request: Request):
    """Serve the main HTML page using Jinja2 template"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Markdown Viewer",
        "sidebar_title": "Markdown Files",
        "default_message": "Select a markdown file from the tree to view its content."
    })


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
