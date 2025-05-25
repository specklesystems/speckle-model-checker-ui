console.log('Models grid script starting...');

// Cache for model images
const imageCache = new Map();

// Function to update a single model image
function updateModelImage(element, previewUrl) {
  if (!element) return;

  const img = document.createElement('img');
  if (previewUrl) {
    img.src = previewUrl;
    img.onload = () => {
      const classes = Array.from(element.classList);
      classes.forEach(cls => {
        if (cls !== 'throbber' && cls !== 'animate-spin' && cls !== 'h-8' && cls !== 'w-8') {
          img.classList.add(cls);
        }
      });

      img.setAttribute('data-model-id', element.getAttribute('data-model-id'));
      img.alt = element.getAttribute('alt') || '';
      element.parentNode.replaceChild(img, element);
    };
    img.onerror = () => {
      // If image fails to load, show placeholder
      showPlaceholder(element);
    };
  } else {
    // If no preview URL provided, show placeholder
    showPlaceholder(element);
  }
}

// Function to show a placeholder for failed images
function showPlaceholder(element) {
  const placeholder = document.createElement('div');
  placeholder.className = 'model-image-placeholder';
  placeholder.innerHTML = `
    <svg class="h-8 w-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  `;
  placeholder.setAttribute('data-model-id', element.getAttribute('data-model-id'));
  element.parentNode.replaceChild(placeholder, element);
}

// Function to handle streaming preview updates
function handlePreviewUpdate(modelId, previewUrl) {
  // Update cache
  imageCache.set(modelId, previewUrl);

  // Find and update all matching model images
  document.querySelectorAll(`.model-image[data-model-id="${modelId}"]`).forEach(element => {
    updateModelImage(element, previewUrl);
  });
}

// Function to load actual model images after grid is rendered
async function loadModelImages(container) {
  if (!container) return;
  const modelIds = container.getAttribute('data-model-ids');
  if (!modelIds) return;

  try {
    // First, show any cached images we have
    const uncachedIds = [];
    JSON.parse(modelIds).forEach(modelId => {
      if (imageCache.has(modelId)) {
        const element = container.querySelector(`.model-image[data-model-id="${modelId}"]`);
        if (element) {
          updateModelImage(element, imageCache.get(modelId));
        }
      } else {
        uncachedIds.push(modelId);
      }
    });

    // If we have uncached images, fetch them via SSE
    if (uncachedIds.length > 0) {
      const eventSource = new EventSource(`/api/models/preview-stream?modelIds=${encodeURIComponent(JSON.stringify(uncachedIds))}`);
      const processedIds = new Set();

      eventSource.addEventListener('preview', (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.modelId && data.previewUrl) {
            processedIds.add(data.modelId);
            handlePreviewUpdate(data.modelId, data.previewUrl);
          }
        } catch (error) {
          console.error('Error handling preview event:', error);
        }
      });

      eventSource.addEventListener('complete', () => {
        // For any models that didn't get a preview, show placeholder
        uncachedIds.forEach(modelId => {
          if (!processedIds.has(modelId)) {
            const element = container.querySelector(`.model-image[data-model-id="${modelId}"]`);
            if (element) {
              showPlaceholder(element);
            }
          }
        });
        eventSource.close();
      });

      eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        // On error, show placeholders for all remaining uncached images
        uncachedIds.forEach(modelId => {
          if (!processedIds.has(modelId)) {
            const element = container.querySelector(`.model-image[data-model-id="${modelId}"]`);
            if (element) {
              showPlaceholder(element);
            }
          }
        });
        eventSource.close();
      };
    }
  } catch (e) {
    console.error('Failed to load model images:', e);
  }
}

// Function to initialize models grid for a specific container
function initializeModelsGrid(container) {
  if (!container) return;
  loadModelImages(container);
}

function initAllModelsGrids() {
  document.querySelectorAll('.models-grid[data-model-ids]').forEach(initializeModelsGrid);
}

document.addEventListener('DOMContentLoaded', () => {
  initAllModelsGrids();
});

document.body.addEventListener('htmx:afterSwap', (evt) => {
  // Remove 'hidden' from models container if needed
  if (evt.target && evt.target.id && evt.target.id.startsWith('models-')) {
    evt.target.classList.remove('hidden');
  }
  // Only initialize if the swap was for a models grid
  if (evt.target && evt.target.classList.contains('models-grid')) {
    initializeModelsGrid(evt.target);
  } else {
    // In case a parent was swapped, re-init all
    initAllModelsGrids();
  }
});

console.log('Models grid script loaded'); 