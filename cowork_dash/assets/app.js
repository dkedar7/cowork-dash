// Initialize Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    logLevel: 'error'
});

// Render mermaid diagrams
async function renderMermaid() {
    const mermaidDivs = document.querySelectorAll('.mermaid-diagram');

    for (const div of mermaidDivs) {
        if (!div.getAttribute('data-processed')) {
            const code = div.textContent.trim();
            div.setAttribute('data-processed', 'true');

            try {
                // Clear the div and create unique ID
                const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
                div.innerHTML = '';

                // Render mermaid
                const { svg } = await mermaid.render(id, code);
                div.innerHTML = svg;
            } catch (error) {
                console.error('Mermaid rendering error:', error);
                div.innerHTML = '<div style="color: #d93025; padding: 20px; text-align: left;">' +
                    '<strong>Mermaid Syntax Error:</strong><br>' +
                    '<code style="font-size: 12px;">' + error.message + '</code><br><br>' +
                    '<details><summary style="cursor: pointer;">View Code</summary>' +
                    '<pre style="background: #f5f5f5; padding: 10px; margin-top: 10px; overflow: auto;">' +
                    code + '</pre></details></div>';
            }
        }
    }
}

// Run mermaid on load and when content changes
window.addEventListener('load', renderMermaid);

// Use MutationObserver to detect when canvas content changes
// Check if observer already exists to prevent redeclaration errors
if (typeof window.mermaidObserver === 'undefined') {
    window.mermaidObserver = new MutationObserver(function(mutations) {
        renderMermaid();
    });

    // Start observing once the canvas is available - retry until found
    function attachMermaidObserver() {
        const canvasContent = document.getElementById('canvas-content');
        if (canvasContent) {
            window.mermaidObserver.observe(canvasContent, { childList: true, subtree: true });
            console.log('Mermaid observer attached to canvas-content');
            // Run initial render in case content is already there
            renderMermaid();
        } else {
            // Retry after a short delay
            setTimeout(attachMermaidObserver, 500);
        }
    }
    attachMermaidObserver();
}

// Resizable split pane - improved reliability
(function initResizablePanes() {
    let isResizing = false;
    let container, chatPanel, resizeHandle, sidebar;

    function findElements() {
        container = document.getElementById('main-container');
        chatPanel = document.getElementById('chat-panel');
        resizeHandle = document.getElementById('resize-handle');
        sidebar = document.getElementById('sidebar-panel');

        return !!(resizeHandle && chatPanel && sidebar && container);
    }

    function handleMouseDown(e) {
        e.preventDefault();
        e.stopPropagation();
        isResizing = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        // Add a semi-transparent overlay to prevent interference
        const overlay = document.createElement('div');
        overlay.id = 'resize-overlay';
        overlay.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999; cursor: col-resize;';
        document.body.appendChild(overlay);
    }

    function handleMouseMove(e) {
        if (!isResizing) return;
        e.preventDefault();

        const containerRect = container.getBoundingClientRect();
        const containerWidth = containerRect.width;
        const offsetX = e.clientX - containerRect.left;
        const chatWidth = (offsetX / containerWidth) * 100;

        // Constrain between 30% and 70%
        if (chatWidth >= 30 && chatWidth <= 70) {
            chatPanel.style.flex = `0 0 ${chatWidth}%`;
            sidebar.style.flex = `0 0 ${100 - chatWidth}%`;
        }
    }

    function handleMouseUp() {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';

            // Remove the overlay
            const overlay = document.getElementById('resize-overlay');
            if (overlay) {
                overlay.remove();
            }
        }
    }

    function setupResizing() {
        if (!findElements()) {
            console.log('Resize elements not found, retrying...');
            setTimeout(setupResizing, 500);
            return;
        }

        // Remove any existing listeners to prevent duplicates
        resizeHandle.removeEventListener('mousedown', handleMouseDown);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);

        // Add event listeners
        resizeHandle.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        console.log('Resize functionality initialized');
    }

    // Initialize on load and after a short delay to ensure DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupResizing);
    } else {
        setupResizing();
    }

    // Also try after window load
    window.addEventListener('load', function() {
        setTimeout(setupResizing, 100);
    });
})();
