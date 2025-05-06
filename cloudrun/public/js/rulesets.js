/**
 * rulesets.js
 * Handles ruleset-specific functionality
 */

const Rulesets = {
  // Edit ruleset
  editRuleset: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    API.fetchWithAuth(url, {
      method: 'GET',
    })
      .then((html) => {
        document.querySelector(targetSelector).innerHTML = html;
        const container = document.querySelector('#ruleset-container');
        if (container && container.dataset.rulesetId) {
          const rulesetId = container.dataset.rulesetId;
          history.pushState({}, '', `/rulesets/${rulesetId}`);
        }
      })
      .catch((error) => console.error('Fetch error:', error));
  },

  // Delete ruleset
  deleteRuleset: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    if (!confirm('Are you sure you want to delete this ruleset?')) {
      return;
    }

    API.deleteWithAuth(url, targetSelector)
      .then(() => {
        UI.showToast('Ruleset deleted successfully');
      })
      .catch((error) => console.error('Delete error:', error));
  },

  // Add new rule
  newRule: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    API.fetchWithAuth(url, {
      method: 'GET',
    })
      .then((html) => {
        document.querySelector(targetSelector).innerHTML = html;
        // Hide the button that was clicked
        if (event && event.target) {
          event.target.style.display = 'none';
        }
        UI.updateSeverityColor();
      })
      .catch((error) => console.error('Fetch error:', error));
  },

  // Add new rule form submission
  addNewRule: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    const form = event.target;
    const formData = new FormData(form);

    API.postFormWithAuth(url, formData)
      .then((html) => {
        // Receive rule list and swap into rules container
        document.querySelector(targetSelector).innerHTML = html;
        // Clear new rule form container
        document.getElementById('rule-form-container').innerHTML = '';
        UI.showToast('Rule added successfully');
      })
      .catch((error) => console.error('Form submission error:', error));

    return false;
  },

  // Edit rule
  editRule: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }
    const currentRow = event.target.closest('tr');
    const tbody = currentRow.parentElement; // get the parent <tbody>

    // Remove 'editing' class from all sibling <tr> elements
    Array.from(tbody.children).forEach((tr) => {
      if (tr !== currentRow) {
        tr.classList.remove('editing');
      }
    });

    // Add 'editing' to the current row
    currentRow.classList.add('editing');

    API.fetchWithAuth(url, {
      method: 'GET',
    })
      .then((html) => {
        // After injecting content, re-run the toggle check
        toggleAddRuleButton();

        // And re-attach the observer
        setupRuleFormObserver();
        document.querySelector(targetSelector).innerHTML = html;
        const container = document.querySelector('#rule-container');
        if (container && container.dataset.ruleId) {
          const ruleId = container.dataset.ruleId;
          history.pushState({}, '', `/rules/${ruleId}`);
        }
      })
      .catch((error) => console.error('Fetch error:', error));
  },

  addConditionRow: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    const target = event.target;
    const container = document.querySelector('#conditions-container');

    const index = container.querySelectorAll('.condition-row').length;

    queryUrl = `${url}?index=${index}`;

    fetch(queryUrl)
      .then((response) => {
        response.text().then((html) => {
          document
            .querySelector(targetSelector)
            .insertAdjacentHTML('beforeend', html);
        });
      })
      .catch((error) => console.error('Fetch error:', error));
  },

  deleteConditionRow: function (event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    const target = event.target;
    const index = target.closest('.condition-row').dataset.conditionindex;

    const row = document.querySelector(`[data-conditionIndex="${index}"]`);
    if (row) {
      row.remove();
    }
  },

  // Delete rule
  deleteRule: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    // Add class to deleting rule to show spinner - accessible from the event target
    if (event && event.target) {
      event.target.closest('tr').classList.add('deleting');
    }

    if (!confirm('Are you sure you want to delete this rule?')) {
      return;
    }

    API.deleteWithAuth(url, targetSelector)
      .then((response) => {
        UI.showToast('Rule deleted successfully');
      })
      .catch((error) => console.error('Delete error:', error));
  },

  updateRule: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    const form = event.target;
    const formData = new FormData(form);

    API.postFormWithAuth(url, formData, 'PUT')
      .then((html) => {
        // Receive rule list and swap into rules container
        document.querySelector(targetSelector).innerHTML = html;
        // Clear new rule form container
        document.getElementById('rule-form-container').innerHTML = '';

        UI.showToast('Rule updated successfully');
      })
      .catch((error) => console.error('Form submission error:', error));

    return false;
  },

  // Share ruleset which means set prop isShared to true
  toggleShareRuleset: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    API.fetchWithAuth(url, {
      method: 'PATCH',
    })
      .then((html) => {
        document.querySelector(targetSelector).outerHTML = html;

        const shared =
          new DOMParser()
            .parseFromString(html, 'text/html')
            .querySelector('[data-shared]')?.dataset.shared === 'True';

        UI.showToast(
          shared
            ? 'Ruleset shared successfully'
            : 'Ruleset unshared successfully'
        );
      })
      .catch((error) => console.error('Fetch error:', error));
  },

  // Export ruleset
  exportRuleset: function (url, targetSelector, event) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }

    API.fetchWithAuth(url, {
      method: 'GET',
    })
      .then((html) => {
        document.querySelector(targetSelector).innerHTML = html;
      })
      .catch((error) => console.error('Fetch error:', error));
  },
};

function toggleAddRuleButton() {
  const ruleFormContainer = document.querySelector('#rule-form-container');
  const addRuleButton = document.querySelector('#rules-container button');

  if (ruleFormContainer && addRuleButton) {
    if (ruleFormContainer.innerHTML.trim() !== '') {
      addRuleButton.style.display = 'none';
    } else {
      addRuleButton.style.display = '';
    }
  }
}

function setupRuleFormObserver() {
  const ruleFormContainer = document.querySelector('#rule-form-container');
  if (ruleFormContainer) {
    const observer = new MutationObserver(toggleAddRuleButton);
    observer.observe(ruleFormContainer, { childList: true, subtree: true });

    // Trigger once on setup
    toggleAddRuleButton();
  } else {
    console.warn(
      '#rule-form-container not found in DOM at observer setup time.'
    );
  }
}
