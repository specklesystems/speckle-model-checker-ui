/**
 * navigation.js
 * Handles all page navigation and routing
 */

const Navigation = {
  // Initialize navigation
  initialize: function () {
    // Listen for browser navigation events (back/forward buttons)
    window.addEventListener('popstate', () => {
      this.loadContentBasedOnUrl(Auth.getCurrentUser());
    });

    // Handle HTMX requests that should update the URL
    document.addEventListener('htmx:afterOnLoad', (event) => {
      // Check for data-hx-push-url attribute to update URL
      const pushUrl = event.detail.elt.getAttribute('hx-push-url');
      if (pushUrl) {
        window.history.pushState(null, '', pushUrl);
      }
    });
  },

  // Navigate to a URL and update the browser history
  navigateTo: function (url) {
    window.history.pushState(null, '', url);
    this.loadContentBasedOnUrl(Auth.getCurrentUser());
  },

  // Load content based on current URL and auth state
  loadContentBasedOnUrl: function (user) {
    if (!user) {
      UI.showWelcomeScreen();
      return;
    }

    const path = window.location.pathname;

    // Handle root path and /projects path
    if (path === '/' || path === '/projects') {
      Projects.goToProjects();
      return;
    }

    // Check if this is a shared ruleset URL
    if (path.startsWith('/shared/')) {
      const ruleSetId = path.split('/').pop();
      if (ruleSetId) {
        htmx.ajax('GET', `/api/shared-rule-sets/${ruleSetId}`, {
          target: '#main-content',
          swap: 'innerHTML'
        });
        return;
      }
    }

    // Check for specific ruleset URLs
    if (path.startsWith('/rulesets/')) {
      const ruleSetId = path.split('/').pop();
      if (ruleSetId) {
        API.fetchWithAuth(`/api/rulesets/${ruleSetId}`, {
          method: 'GET'
        })
          .then(html => {
            document.querySelector('#main-content').innerHTML = html;
            history.pushState({}, '', `/rulesets/${ruleSetId}`);
          })
          .catch(error => console.error("Fetch error:", error));
        return;
      }
    }

    // Check for specific project URLs
    if (path.startsWith('/project/')) {
      const projectId = path.split('/').pop();
      if (projectId) {
        Projects.getProjectRulesets(projectId, '#main-content');
        return;
      }
    }

    // Default: go to projects list
    Projects.goToProjects();
  },

  // Go to the projects list page
  goToProjects: function () {
    Projects.goToProjects();
  }
};