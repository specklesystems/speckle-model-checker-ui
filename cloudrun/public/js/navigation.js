/**
 * navigation.js
 * Handles all page navigation and routing with HTMX
 */

const Navigation = {
  // Initialize navigation
  initialize: function() {
    // Listen for browser navigation events (back/forward buttons)
    window.addEventListener('popstate', () => {
      this.loadContentBasedOnUrl(Auth.getCurrentUser());
    });
    
    // Setup HTMX integration
    this.setupHTMXListeners();
  },

  // Setup HTMX-specific event listeners
  setupHTMXListeners: function() {
    // Handle HTMX requests that should update the URL
    document.addEventListener('htmx:afterOnLoad', (event) => {
      // Check for successful responses
      if (event.detail.xhr.status === 200) {
        // Update URL based on the response
        const newUrl = event.detail.xhr.responseURL;
        if (newUrl && newUrl !== window.location.href) {
          window.history.pushState(null, '', newUrl);
        }
      }
    });

    // Handle authentication errors in HTMX requests
    document.addEventListener('htmx:responseError', (event) => {
      if (event.detail.xhr.status === 401) {
        // Session expired - redirect to login
        UI.showToast('Session expired. Please log in again.', true);
        setTimeout(() => {
          window.location.href = '/';
        }, 2000);
      }
    });

    // Show loading indicator for HTMX requests
    document.addEventListener('htmx:beforeOnLoad', () => {
      UI.showLoadingIndicator();
    });

    document.addEventListener('htmx:afterOnLoad', () => {
      UI.hideLoadingIndicator();
    });
  },

  // Navigate to a URL and update the browser history
  navigateTo: function(url) {
    // For HTMX-powered navigation, use htmx.ajax
    if (window.htmx) {
      htmx.ajax('GET', url, {
        target: '#main-content',
        swap: 'innerHTML',
        indicator: '.htmx-indicator'
      });
    } else {
      // Fallback to traditional navigation
      window.location.href = url;
    }
  },

  // Load content based on current URL and auth state
  loadContentBasedOnUrl: function(user) {
    if (!user) {
      UI.showWelcomeScreen();
      return;
    }

    const path = window.location.pathname;

    // Check if this is a shared ruleset URL
    if (path.startsWith('/shared/')) {
      const ruleSetId = path.split('/').pop();
      if (ruleSetId) {
        this.navigateTo(`/shared/${ruleSetId}`);
        return;
      }
    }

    // Check for specific ruleset URLs
    if (path.startsWith('/rulesets/')) {
      const ruleSetId = path.split('/').pop();
      if (ruleSetId) {
        this.navigateTo(`/api/rulesets/${ruleSetId}`);
        return;
      }
    }

    // Check for specific project URLs
    if (path.startsWith('/projects/')) {
      const projectId = path.split('/').pop();
      if (projectId) {
        this.navigateTo(`/api/projects/${projectId}`);
        return;
      }
    }

    // Default: go to projects list
    this.navigateTo('/api/projects');
  },

  // Go to the projects list page
  goToProjects: function() {
    this.navigateTo('/api/projects');
  }
};