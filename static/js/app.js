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
document.addEventListener('DOMContentLoaded', loadFileTree);
