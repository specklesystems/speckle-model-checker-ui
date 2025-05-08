/**
 * projects.js
 * Handles project-specific functionality
 */

const Projects = {
  // Go to projects list
  goToProjects: function(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    API.fetchWithAuth('/api/projects', {
      method: 'GET'
    })
    .then(html => {
      document.querySelector('#main-content').innerHTML = html;
      // Update browser history
      history.pushState({}, '', '/projects');
    })
    .catch(error => console.error("Fetch error:", error));
  },

  // Get project rulesets
  getProjectRulesets: function(projectId, targetSelector, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    API.fetchWithAuth(`/api/projects/${projectId}`, {
      method: 'GET'
    })
    .then(html => {
      document.querySelector(targetSelector).innerHTML = html;
      // Update browser history after successful fetch
      history.pushState({}, '', `/project/${projectId}`);
    })
    .catch(error => console.error("Fetch error:", error));
  },

  // Create new ruleset form
  newRuleSet: function(url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    API.fetchWithAuth(url, {
      method: 'GET'
    })
    .then(html => {
      document.querySelector(targetSelector).innerHTML = html;
    })
    .catch(error => console.error("Fetch error:", error));
  },

  // Handle form submission for creating a ruleset
  createRuleSet: function(url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    const form = event.target;
    const formData = new FormData(form);

    API.postFormWithAuth(url, formData)
    .then(html => {
      document.querySelector(targetSelector).innerHTML = html;
      // Try to get ruleset ID from container for history update
      const container = document.querySelector('#ruleset-container');
      if (container && container.dataset.rulesetId) {
        const rulesetId = container.dataset.rulesetId;
        history.pushState({}, '', `/rulesets/${rulesetId}`);
      }
    })
    .catch(error => console.error("Form submission error:", error));
    
    return false;
  }
};