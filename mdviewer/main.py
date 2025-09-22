from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown
import mimetypes

app = FastAPI(title="Markdown Viewer")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# No default markdown directory - users will select their own folders


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
            elif item.is_dir() and not item.name.startswith('.'):
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
def root(request: Request):
    """Serve the main HTML page using Jinja2 template"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Markdown Viewer",
        "sidebar_title": "Markdown Files",
        "default_message": "Select a markdown file from the tree to view its content."
    })


@app.get("/api/files")
def get_files(folder_path: Optional[str] = None):
    """API endpoint to get the file tree structure"""
    try:
        if folder_path is None:
            return JSONResponse(content=[])

        target_dir = Path(folder_path).resolve()

        # Security check: ensure the path exists and is a directory
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        file_tree = get_file_tree(target_dir)
        return JSONResponse(content=file_tree)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")


@app.get("/api/file/{file_path:path}")
def get_file_content(file_path: str, base_folder: Optional[str] = None):
    """API endpoint to get rendered markdown content"""
    try:
        if base_folder is None:
            raise HTTPException(status_code=400, detail="Base folder parameter is required")

        base_dir = Path(base_folder).resolve()
        full_path = base_dir / file_path

        # Security check: ensure the file is within the base directory
        if not str(full_path.resolve()).startswith(str(base_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        if full_path.suffix.lower() != '.md':
            raise HTTPException(status_code=400, detail="Not a markdown file")

        # Read and render markdown
        with open(full_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Convert markdown to HTML
        # Try to use emoji extension if available, fallback to basic extensions
        extensions = ['extra', 'codehilite']
        extension_configs = {}

        try:
            import pymdownx.emoji
            extensions.append('pymdownx.emoji')
            extension_configs['pymdownx.emoji'] = {
                'emoji_index': pymdownx.emoji.gemoji,
                'emoji_generator': pymdownx.emoji.to_alt
            }
        except ImportError:
            # pymdown-extensions not available, skip emoji support
            pass

        md = markdown.Markdown(
            extensions=extensions, 
            extension_configs=extension_configs,
            tab_length=2  # Allow nested lists with 2+ spaces instead of requiring 4 spaces
        )
        html_content = md.convert(markdown_content)

        return HTMLResponse(content=f'<div class="markdown-content">{html_content}</div>')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.get("/assets/{file_path:path}")
def serve_asset(file_path: str, base_folder: Optional[str] = None):
    """Serve static assets (images, etc.) from the selected markdown folder"""
    try:
        if base_folder is None:
            raise HTTPException(status_code=400, detail="Base folder parameter is required")

        base_dir = Path(base_folder).resolve()
        full_path = base_dir / file_path

        # Security check: ensure the file is within the base directory
        if not str(full_path.resolve()).startswith(str(base_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        return FileResponse(full_path, media_type=mime_type)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving asset: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)
