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

        const url = `/api/file/${encodeURIComponent(filePath)}?base_folder=${encodeURIComponent(currentFolder)}`;
        const response = await fetch(url);
        if (response.ok) {
            const html = await response.text();
            document.getElementById('markdown-content').innerHTML = html;
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

function handleFolderLoad() {
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
