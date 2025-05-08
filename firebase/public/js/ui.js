/**
 * ui.js
 * Handles all UI-related functionality
 */

const UI = {
  // Initialize UI elements and event listeners
  initialize: function () {
    this.setupDropdownHandlers();
    this.setupDelegatedListeners();
  },

  // Set up dropdown handlers
  setupDropdownHandlers: function () {
    // Close dropdowns when clicking outside
    document.addEventListener('click', function (event) {
      // Check if click is outside user dropdown
      const userDropdownBtn = document.getElementById('user-dropdown-btn');
      const userDropdownMenu = document.getElementById('user-dropdown-menu');

      if (
        userDropdownBtn &&
        userDropdownMenu &&
        !userDropdownBtn.contains(event.target) &&
        !userDropdownMenu.contains(event.target)
      ) {
        userDropdownMenu.classList.add('hidden');
        userDropdownBtn.querySelector('svg')?.classList.remove('rotate-180');
      }

      // Check if click is outside login dropdown
      const loginDropdownBtn = document.getElementById('login-dropdown-btn');
      const loginDropdownMenu = document.getElementById('login-dropdown-menu');

      if (
        loginDropdownBtn &&
        loginDropdownMenu &&
        !loginDropdownBtn.contains(event.target) &&
        !loginDropdownMenu.contains(event.target)
      ) {
        loginDropdownMenu.classList.add('hidden');
        loginDropdownBtn.querySelector('svg')?.classList.remove('rotate-180');
      }
    });

    // Close share dialog when clicking outside
    document
      .getElementById('share-dialog-container')
      ?.addEventListener('click', (e) => {
        if (e.target === document.getElementById('share-dialog-container')) {
          document
            .getElementById('share-dialog-container')
            .classList.add('hidden');
        }
      });
  },

  // Set up delegated event listeners for dynamic content
  setupDelegatedListeners: function () {
    // Delegate clicks on project headers
    document.body.addEventListener('click', function (e) {
      const header = e.target.closest('.project-header');
      if (header) {
        const projectId = header.getAttribute('data-project-id');
        const modelsElement = document.getElementById(`models-${projectId}`);
        if (!modelsElement) return;

        const toggleButton = header.querySelector('.toggle-btn');
        if (modelsElement.classList.contains('hidden')) {
          modelsElement.classList.remove('hidden');
          if (toggleButton) toggleButton.setAttribute('aria-expanded', 'true');
        } else {
          modelsElement.classList.add('hidden');
          if (toggleButton) toggleButton.setAttribute('aria-expanded', 'false');
        }
      }
    });

    // Delegate clicks on toggle buttons (so they don't propagate to header clicks)
    document.body.addEventListener('click', function (e) {
      const toggleButton = e.target.closest('.toggle-btn');
      if (toggleButton) {
        e.stopPropagation(); // prevent triggering header click
        const targetId = toggleButton.getAttribute('data-toggle');
        const modelsElement = document.getElementById(targetId);
        if (modelsElement) {
          if (modelsElement.classList.contains('hidden')) {
            modelsElement.classList.remove('hidden');
            toggleButton.setAttribute('aria-expanded', 'true');
          } else {
            modelsElement.classList.add('hidden');
            toggleButton.setAttribute('aria-expanded', 'false');
          }
        }
      }
    });

    // Handle severity dropdown changes
    document.body.addEventListener('change', function (e) {
      if (e.target.id === 'severity') {
        UI.updateSeverityColor(e.target);
      }
    });
  },

  // Toggle user dropdown
  toggleUserDropdown: function () {
    const dropdown = document.getElementById('user-dropdown-menu');
    const button = document.getElementById('user-dropdown-btn');
    const arrow = button.querySelector('svg');

    const isOpen = !dropdown.classList.contains('hidden');

    // Toggle the dropdown
    dropdown.classList.toggle('hidden');

    // Toggle arrow rotation
    if (isOpen) {
      arrow.classList.remove('rotate-180');
    } else {
      arrow.classList.add('rotate-180');
    }

    // Ensure login dropdown is closed
    document.getElementById('login-dropdown-menu')?.classList.add('hidden');
    document
      .getElementById('login-dropdown-btn')
      ?.querySelector('svg')
      ?.classList.remove('rotate-180');
  },

  // Toggle login dropdown
  toggleLoginDropdown: function () {
    const dropdown = document.getElementById('login-dropdown-menu');
    const button = document.getElementById('login-dropdown-btn');
    const arrow = button.querySelector('svg');

    const isOpen = !dropdown.classList.contains('hidden');

    // Toggle the dropdown
    dropdown.classList.toggle('hidden');

    // Toggle arrow rotation
    if (isOpen) {
      arrow.classList.remove('rotate-180');
    } else {
      arrow.classList.add('rotate-180');
    }

    // Ensure user dropdown is closed
    document.getElementById('user-dropdown-menu')?.classList.add('hidden');
    document
      .getElementById('user-dropdown-btn')
      ?.querySelector('svg')
      ?.classList.remove('rotate-180');
  },

  // Update UI based on authentication state
  updateAuthUI: function (user) {
    if (user) {
      // User is signed in
      document.getElementById('login-container').classList.add('hidden');
      document.getElementById('user-profile').classList.remove('hidden');

      // Update user info in both places
      const userName = user.displayName || 'User';
      const userEmail = user.email || '';

      document.getElementById('user-name').textContent = userName;
      document.getElementById('dropdown-user-name').textContent = userName;
      document.getElementById('dropdown-user-email').textContent = userEmail;

      if (user.photoURL) {
        // swap the default avatar, an svg, with an image with the user's photo
        document.getElementById('user-avatar').classList.remove('hidden');
        document
          .getElementById('user-avatar-placeholder')
          .classList.add('hidden');
        document.getElementById('user-avatar').src = user.photoURL;
      }
    } else {
      // User is signed out
      document.getElementById('user-profile').classList.add('hidden');

      // Close any open dropdowns
      document.getElementById('user-dropdown-menu').classList.add('hidden');
      document.getElementById('login-dropdown-menu').classList.add('hidden');
    }
    // Hide the loading indicator
    this.hideLoadingIndicator();
  },

  // Show loading indicator
  showLoadingIndicator: function () {
    const indicator = document.querySelector('.htmx-indicator');
    indicator.classList.remove('hidden');
    indicator.classList.add('active');
  },

  // Hide loading indicator
  hideLoadingIndicator: function () {
    const indicator = document.querySelector('.htmx-indicator');
    indicator.classList.add('hidden');
    indicator.classList.remove('active');
  },

  // Show welcome screen for non-authenticated users
  showWelcomeScreen: function () {
    const mainContent = document.getElementById('main-content');

    mainContent.innerHTML = `
      <div class="flex flex-col items-center justify-center h-64">
        <h1 class="text-2xl font-bold mb-4">Welcome to Model Checker</h1>
        <p class="text-secondary mb-6">Sign in with your Speckle account to manage rule sets for your projects.</p>
        <button onclick="Auth.signInToSpeckle()" class="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark">
          Sign In with Speckle
        </button>
      </div>
    `;
  },

  // Show toast notification
  showToast: function (message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : ''}`;
    toast.textContent = message;
    document.getElementById('toast-container').appendChild(toast);

    // Remove toast after animation completes
    setTimeout(() => {
      toast.remove();
    }, 3000);
  },

  // Update severity dropdown color
  updateSeverityColor: function (element) {
    const severityDropdown = element || document.getElementById('severity');
    if (severityDropdown) {
      // Remove all previous classes
      severityDropdown.classList.remove(
        'bg-red-100',
        'text-red-800',
        'bg-yellow-100',
        'text-yellow-800',
        'bg-blue-100',
        'text-blue-800'
      );

      // Add classes based on selected value
      switch (severityDropdown.value) {
        case 'Error':
          severityDropdown.classList.add('bg-red-100', 'text-red-800');
          break;
        case 'Warning':
          severityDropdown.classList.add('bg-yellow-100', 'text-yellow-800');
          break;
        case 'Info':
          severityDropdown.classList.add('bg-blue-100', 'text-blue-800');
          break;
      }
    }
  },

  // Copy to clipboard utility
  copyToClipboard: function (text) {
    // If text starts with a Cloud Function URL, replace it with the main application URL
    if (text && text.includes('.a.run.app/')) {
      // Extract the path after the Cloud Function domain
      const pathMatch = text.match(/\.a\.run\.app(\/.*)/);
      if (pathMatch && pathMatch[1]) {
        // Replace with the main application URL
        text = 'https://speckle-model-checker.web.app' + pathMatch[1];
      }
    }

    navigator.clipboard
      .writeText(text)
      .then(() => {
        this.showToast('Copied to clipboard!');
      })
      .catch(() => {
        this.showToast('Failed to copy to clipboard', true);
      });
  },

  loadAndRender: function (
    url,
    targetSelector,
    method = 'GET',
    options = {},
    event = null,
    injectMode = 'replace',
    afterRender = null
  ) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    console.log('loadAndRender');

    API.fetchWithAuth(url, { method, ...options })

      .then((html) => {
        const target = document.querySelector(targetSelector);
        if (!target) {
          console.warn(`Target ${targetSelector} not found.`);
          return;
        }

        if (injectMode === 'append') {
          target.insertAdjacentHTML('beforeend', html);
        } else {
          target.innerHTML = html;
        }

        if (event?.target) {
          event.target.style.display = 'none';
        }

        if (afterRender && typeof afterRender === 'function') {
          afterRender();
        }
      })
      .catch((error) => console.error('Fetch error:', error));
  },
};
