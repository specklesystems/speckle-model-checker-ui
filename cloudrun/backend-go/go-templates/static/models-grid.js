console.log('Models grid script starting...');

// Cache for model images
const imageCache = new Map();

// Function to load actual model images after grid is rendered
async function loadModelImages(container) {
  if (!container) return;
  const modelIds = container.getAttribute('data-model-ids');
  if (!modelIds) return;

  try {
    // First, show any cached images we have
    const cachedImages = {};
    const uncachedIds = [];

    JSON.parse(modelIds).forEach(modelId => {
      if (imageCache.has(modelId)) {
        cachedImages[modelId] = imageCache.get(modelId);
      } else {
        uncachedIds.push(modelId);
      }
    });

    // Update with any cached images immediately
    if (Object.keys(cachedImages).length > 0) {
      updateGridWithImages(container, cachedImages);
    }

    // If we have uncached images, fetch them
    if (uncachedIds.length > 0) {
      const response = await fetch('/api/models/images', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ modelIds: uncachedIds })
      });

      if (!response.ok) throw new Error('Failed to fetch model images');

      const images = await response.json();

      // Cache the new images
      Object.entries(images).forEach(([modelId, dataUri]) => {
        imageCache.set(modelId, dataUri);
      });

      // Update the grid with new images
      updateGridWithImages(container, images);
    }
  } catch (e) {
    console.error('Failed to load model images:', e);
  }
}

// Function to update grid with actual images
function updateGridWithImages(container, images) {
  const imageElements = container.querySelectorAll('.model-image');
  imageElements.forEach(element => {
    const modelId = element.getAttribute('data-model-id');
    if (images[modelId]) {
      // Create new img element
      const img = document.createElement('img');
      img.src = images[modelId];

      // Copy classes from original element, excluding throbber and animate-spin
      const classes = Array.from(element.classList);
      classes.forEach(cls => {
        if (cls !== 'throbber' && cls !== 'animate-spin' && cls !== 'h-8' && cls !== 'w-8') {
          img.classList.add(cls);
        }
      });

      img.setAttribute('data-model-id', modelId);
      img.alt = element.getAttribute('alt') || '';

      // Replace the element (whether it's an img or svg) with the new img
      element.parentNode.replaceChild(img, element);
    }
  });
}

// Function to initialize models grid for a specific container
function initializeModelsGrid(container) {
  if (!container) return;

  // Start loading actual images after grid is rendered
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