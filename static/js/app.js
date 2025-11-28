let selectedFile = null;
let currentFolder = null;

async function loadFileTree(folderPath = null) {
    try {
        const url = folderPath ? `/api/files?folder_path=${encodeURIComponent(folderPath)}` : '/api/files';
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const files = await response.json();
        currentFolder = folderPath;
        renderTree(files);
    } catch (error) {
        document.getElementById('tree-container').innerHTML =
            `<div class="error">Error loading file tree: ${error.message}</div>`;
    }
}

function renderTree(items, container = null) {
    if (!container) {
        container = document.getElementById('tree-container');
        container.innerHTML = '';
    }

    if (items.length === 0) {
        container.innerHTML = currentFolder
            ? '<div class="no-files">No markdown files found in this folder.</div>'
            : '<div class="no-folder">No folder selected. Please enter a folder path above.</div>';
        return;
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
        if (!currentFolder) {
            document.getElementById('markdown-content').innerHTML =
                '<div class="error">No folder selected</div>';
            return;
        }

        const url = `/${encodeURIComponent(filePath)}`;
        const response = await fetch(url);
        if (response.ok) {
            const html = await response.text();
            document.getElementById('markdown-content').innerHTML = html;
            // Fix image and asset paths relative to the markdown file's directory
            fixAssetPaths(filePath);
        } else {
            const errorText = await response.text();
            document.getElementById('markdown-content').innerHTML =
                `<div class="error">Error loading file content: ${errorText}</div>`;
        }
    } catch (error) {
        document.getElementById('markdown-content').innerHTML =
            `<div class="error">Error loading file content: ${error.message}</div>`;
    }
}

function fixAssetPaths(markdownFilePath) {
    if (!currentFolder || !markdownFilePath) return;

    const contentDiv = document.getElementById('markdown-content');

    // Calculate the base directory of the markdown file
    const markdownDir = markdownFilePath.includes('/')
        ? markdownFilePath.substring(0, markdownFilePath.lastIndexOf('/'))
        : '';

    // Fix image sources
    const images = contentDiv.querySelectorAll('img');
    images.forEach(img => {
        const src = img.getAttribute('src');
        if (src && !src.startsWith('http://') && !src.startsWith('https://') && !src.startsWith('/static/')) {
            // Resolve the image path relative to the markdown file's directory
            let resolvedPath;

            if (src.startsWith('./')) {
                // Relative to current directory: ./image.png
                resolvedPath = markdownDir ? `${markdownDir}/${src.substring(2)}` : src.substring(2);
            } else if (src.startsWith('../')) {
                // Relative to parent directory: ../images/image.png
                if (markdownDir) {
                    const pathParts = markdownDir.split('/');
                    let srcParts = src.split('/');

                    // Handle multiple ../ in the path
                    while (srcParts[0] === '..' && pathParts.length > 0) {
                        pathParts.pop();
                        srcParts.shift();
                    }

                    resolvedPath = pathParts.length > 0
                        ? `${pathParts.join('/')}/${srcParts.join('/')}`
                        : srcParts.join('/');
                } else {
                    // If we're at root level, just remove the ../
                    resolvedPath = src.replace(/^\.\.\/+/, '');
                }
            } else if (src.startsWith('/')) {
                // Absolute path from root: /images/image.png
                resolvedPath = src.substring(1);
            } else {
                // Relative path without ./ prefix: images/image.png
                resolvedPath = markdownDir ? `${markdownDir}/${src}` : src;
            }

            img.src = `/assets/${resolvedPath}?base_folder=${encodeURIComponent(currentFolder)}`;
        }
    });

    // Fix other asset links (like CSS, PDFs, etc.)
    const links = contentDiv.querySelectorAll('a[href]');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.startsWith('http://') && !href.startsWith('https://') && !href.startsWith('#') && !href.startsWith('/static/')) {
            // Check if it's pointing to a file that might be an asset
            const extension = href.split('.').pop()?.toLowerCase();
            const assetExtensions = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'pdf', 'css', 'js', 'doc', 'docx', 'txt'];
            if (extension && assetExtensions.includes(extension)) {
                // Apply same path resolution logic as images
                let resolvedPath;

                if (href.startsWith('./')) {
                    resolvedPath = markdownDir ? `${markdownDir}/${href.substring(2)}` : href.substring(2);
                } else if (href.startsWith('../')) {
                    if (markdownDir) {
                        const pathParts = markdownDir.split('/');
                        let hrefParts = href.split('/');

                        while (hrefParts[0] === '..' && pathParts.length > 0) {
                            pathParts.pop();
                            hrefParts.shift();
                        }

                        resolvedPath = pathParts.length > 0
                            ? `${pathParts.join('/')}/${hrefParts.join('/')}`
                            : hrefParts.join('/');
                    } else {
                        resolvedPath = href.replace(/^\.\.\/+/, '');
                    }
                } else if (href.startsWith('/')) {
                    resolvedPath = href.substring(1);
                } else {
                    resolvedPath = markdownDir ? `${markdownDir}/${href}` : href;
                }

                link.href = `/assets/${resolvedPath}?base_folder=${encodeURIComponent(currentFolder)}`;
            }
        }
    });
}

async function handleFolderLoad() {
    const folderInput = document.getElementById('folder-input');
    const folderPath = folderInput.value.trim();

    if (!folderPath) {
        document.getElementById('tree-container').innerHTML =
            '<div class="error">Please enter a folder path</div>';
        return;
    }

    // Clear current selection and content
    selectedFile = null;
    document.getElementById('markdown-content').innerHTML =
        '<p style="color: #6c757d;">Loading folder...</p>';

    // Set the base folder on the server
    try {
        const response = await fetch('/api/set-base-folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ folder_path: folderPath })
        });

        if (!response.ok) {
            const error = await response.json();
            document.getElementById('tree-container').innerHTML =
                `<div class="error">Error setting base folder: ${error.detail}</div>`;
            return;
        }
    } catch (error) {
        document.getElementById('tree-container').innerHTML =
            `<div class="error">Error setting base folder: ${error.message}</div>`;
        return;
    }

    loadFileTree(folderPath);
}

// Load file tree on page load (will be empty by default)
document.addEventListener('DOMContentLoaded', function() {
    loadFileTree(); // Load empty tree initially

    // Set up event handlers
    document.getElementById('load-folder-btn').addEventListener('click', handleFolderLoad);

    document.getElementById('folder-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleFolderLoad();
        }
    });
});
