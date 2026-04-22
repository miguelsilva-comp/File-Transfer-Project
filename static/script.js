// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const uploadProgress = document.getElementById('upload-progress');
const filesContainer = document.getElementById('files-container');
const serverInfo = document.getElementById('server-info');
const fileCount = document.getElementById('file-count');
const storageUsed = document.getElementById('storage-used');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadServerInfo();
    loadFiles();
    
    // Refresh files every 2 seconds
    setInterval(loadFiles, 2000);
});

// Event Listeners
function setupEventListeners() {
    // Dropzone click
    dropzone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

// Get server info
async function loadServerInfo() {
    try {
        const response = await fetch('/api/info');
        const data = await response.json();
        const url = `http://${data.ip}:${data.port}`;
        serverInfo.textContent = `🌐 Server running at ${url}`;
    } catch (error) {
        console.error('Error loading server info:', error);
        serverInfo.textContent = '⚠️ Unable to connect to server';
    }
}

// Load and display files
async function loadFiles() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        
        if (data.error) {
            filesContainer.innerHTML = `<p class="empty-state">Error: ${data.error}</p>`;
            return;
        }
        
        const files = data.files;
        fileCount.textContent = files.length;
        
        // Calculate total storage
        const totalSize = files.reduce((sum, file) => sum + file.size, 0);
        storageUsed.textContent = formatSize(totalSize);
        
        if (files.length === 0) {
            filesContainer.innerHTML = '<p class="empty-state">No files yet. Upload some!</p>';
            return;
        }
        
        filesContainer.innerHTML = files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">📄 ${escapeHtml(file.name)}</div>
                    <div class="file-size">${file.size_display}</div>
                </div>
                <div class="file-actions">
                    <button class="btn-download" onclick="downloadFile('${escapeHtml(file.name)}')">Download</button>
                    <button class="btn-delete" onclick="deleteFile('${escapeHtml(file.name)}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading files:', error);
        filesContainer.innerHTML = '<p class="empty-state">Error loading files</p>';
    }
}

// Handle file uploads
async function handleFiles(files) {
    const fileArray = Array.from(files);
    
    for (const file of fileArray) {
        await uploadFile(file);
    }
    
    // Clear file input
    fileInput.value = '';
    
    // Reload files
    loadFiles();
}

// Upload a single file
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Create progress element
    const progressId = `progress-${Date.now()}-${Math.random()}`;
    const progressHtml = `
        <div class="progress-item" id="${progressId}">
            <div class="filename">${escapeHtml(file.name)}</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%"></div>
            </div>
        </div>
    `;
    uploadProgress.insertAdjacentHTML('beforeend', progressHtml);
    const progressElement = document.getElementById(progressId);
    const progressFill = progressElement.querySelector('.progress-fill');
    
    return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressFill.style.width = percentComplete + '%';
            }
        });
        
        xhr.addEventListener('load', () => {
            progressElement.remove();
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                showNotification(response.message || 'File uploaded successfully', 'success');
            } else {
                const response = JSON.parse(xhr.responseText);
                showNotification(response.error || 'Upload failed', 'error');
            }
            resolve();
        });
        
        xhr.addEventListener('error', () => {
            progressElement.remove();
            showNotification('Upload failed', 'error');
            resolve();
        });
        
        xhr.open('POST', '/api/upload');
        xhr.send(formData);
    });
}

// Download file
function downloadFile(filename) {
    window.location.href = `/api/download/${encodeURIComponent(filename)}`;
}

// Delete file
async function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/delete/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message || 'File deleted', 'success');
            loadFiles();
        } else {
            showNotification(data.error || 'Delete failed', 'error');
        }
    } catch (error) {
        console.error('Error deleting file:', error);
        showNotification('Error deleting file', 'error');
    }
}

// Utility functions
function formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showNotification(message, type) {
    // You can enhance this with a toast library if needed
    console.log(`[${type.toUpperCase()}] ${message}`);
}
