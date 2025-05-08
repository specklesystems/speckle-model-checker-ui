// Apply predicate-specific changes to a value input
function applyPredicateChanges(select, valueInput) {
  if (
    select.value === 'exists' ||
    select.value === 'is true' ||
    select.value === 'is false'
  ) {
    valueInput.removeAttribute('required');
    valueInput.disabled = true;
    valueInput.placeholder = '';
    valueInput.value = '';
  } else {
    valueInput.setAttribute('required', '');
    valueInput.disabled = false;

    if (select.value === 'less than' || select.value === 'greater than') {
      valueInput.type = 'number';
      valueInput.placeholder = 'e.g. 10';
    } else if (select.value === 'in range') {
      valueInput.placeholder = 'e.g. 10,20';
    } else if (select.value === 'in list') {
      valueInput.placeholder = 'e.g. red, blue, green';
    } else if (select.value === 'is like') {
      valueInput.placeholder = 'e.g. Walls or ^Wall$ in non-fuzzy mode';
    } else {
      valueInput.placeholder = 'e.g. Walls';
    }
  }
}

// Handle predicate changes and value input state
function handlePredicateChange(select) {
  const row = select.closest('.condition-row');
  const valueInput = row.querySelector('.value-input');
  applyPredicateChanges(select, valueInput);
}

// Handle condition reordering
function handleConditionReorder(button) {
  const row = button.closest('.condition-row');
  const direction = button.getAttribute('data-direction');
  const conditionsList = document.getElementById('conditions-list');
  const rows = Array.from(conditionsList.children);

  const currentIndex = rows.indexOf(row);

  if (direction === 'up' && currentIndex > 0) {
    const targetIndex = currentIndex - 1;
    const targetRow = rows[targetIndex];
    conditionsList.insertBefore(row, targetRow);
  } else if (direction === 'down' && currentIndex < rows.length - 1) {
    const targetIndex = currentIndex + 1;
    const targetRow = rows[targetIndex];
    conditionsList.insertBefore(targetRow, row);
  }

  // Update logic values after reordering
  updateConditionLogic();

  // Update index values in form element names
  updateConditionIndexes();

  // Update arrow visibility
  const updatedRows = Array.from(conditionsList.children);
  updatedRows.forEach((row, index) => {
    const upArrow = row.querySelector('.up-arrow');
    const downArrow = row.querySelector('.down-arrow');

    if (upArrow) {
      upArrow.style.display = index > 0 ? '' : 'none';
    }
    if (downArrow) {
      downArrow.style.display = index < updatedRows.length - 1 ? '' : 'none';
    }
  });
}

// Update condition logic and enforce WHERE/CHECK pattern
function updateConditionLogic() {
  const conditionsList = document.getElementById('conditions-list');
  const rows = conditionsList.querySelectorAll('.condition-row');

  rows.forEach((row, index) => {
    const logicSelect = row.querySelector('select[name$="[logic]"]');
    const hiddenInput = row.querySelector('input[name$="[logic]"]');

    if (rows.length === 1) {
      // Single condition should be WHERE
      logicSelect.value = 'WHERE';
      if (hiddenInput) hiddenInput.value = 'WHERE';
    } else if (index === 0) {
      // First condition should be WHERE
      logicSelect.value = 'WHERE';
      if (hiddenInput) hiddenInput.value = 'WHERE';
    } else if (index === rows.length - 1) {
      // Last condition should be CHECK
      logicSelect.value = 'CHECK';
      if (hiddenInput) hiddenInput.value = 'CHECK';
    } else {
      // Middle conditions should be AND
      logicSelect.value = 'AND';
      if (hiddenInput) hiddenInput.value = 'AND';
    }
  });
}

// Update index values in form element names
function updateConditionIndexes() {
  const conditionsList = document.getElementById('conditions-list');
  const rows = Array.from(conditionsList.children);

  rows.forEach((row, index) => {
    // Update all form elements in the row
    row.querySelectorAll('select, input').forEach((element) => {
      const name = element.getAttribute('name');
      if (name) {
        // Replace the index in the name attribute
        const newName = name.replace(
          /conditions\[\d+\]/,
          `conditions[${index}]`
        );
        element.setAttribute('name', newName);
      }
    });

    // Update the data-conditionindex attribute
    row.setAttribute('data-conditionindex', index);
  });
}

// Alias map for deep properties
function getFriendlyPropertyName(propertyPath) {
  if (!propertyPath) return '';
  const last = propertyPath.split('.').slice(-1)[0];
  // Replace underscores with spaces and capitalize first letter
  return last.replace(/_/g, ' ').replace(/^[a-z]/, (c) => c.toUpperCase());
}

// Format comma-separated values with "or"
function formatList(listStr) {
  const items = listStr
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  if (items.length === 0) return '';
  if (items.length === 1) return items[0];
  return items.slice(0, -1).join(', ') + ' or ' + items[items.length - 1];
}

// Turn predicate into plain English
function describePredicate(propertyName, predicate, value) {
  switch (predicate) {
    case 'exists':
      return `${propertyName} is present`;
    case 'equal to':
      return `${propertyName} is ${value}`;
    case 'not equal to':
      return `${propertyName} is not ${value}`;
    case 'greater than':
      return `${propertyName} is greater than ${value}`;
    case 'less than':
      return `${propertyName} is less than ${value}`;
    case 'in list':
      return `${propertyName} is one of: ${formatList(value)}`;
    case 'in range':
      const [min, max] = value.split(',').map((v) => v.trim());
      return `${propertyName} is between ${min} and ${max}`;
    case 'contains':
      return `${propertyName} contains "${value}"`;
    case 'does not contain':
      return `${propertyName} does not contain "${value}"`;
    case 'is like':
      return `${propertyName} is like "${value}"`;
    case 'is true':
      return `${propertyName} is true`;
    case 'is false':
      return `${propertyName} is false`;
    case 'identical to':
      return `${propertyName} is identical to ${value}`;
    default:
      return `${propertyName} ${predicate} ${value}`;
  }
}

// Main message generator
function generateMessageFromConditions() {
  const conditionsList = document.getElementById('conditions-list');
  const rows = Array.from(conditionsList.children);
  const messageInput = document.getElementById('message');
  const autoGeneratedInput = document.getElementById('auto_generated_message');

  if (!messageInput || rows.length === 0) return;

  let filters = [];
  let check = null;

  rows.forEach((row) => {
    const propertyNameRaw = row.querySelector(
      'input[name$="[propertyName]"]'
    ).value;
    const predicate = row.querySelector('select[name$="[predicate]"]').value;
    const value = row.querySelector('input[name$="[value]"]').value;
    const logic = row.querySelector('select[name$="[logic]"]').value;

    if (!propertyNameRaw) return;

    const friendlyName = getFriendlyPropertyName(propertyNameRaw);

    if (logic === 'CHECK') {
      check = { propertyNameRaw, propertyName: friendlyName, predicate, value };
    } else {
      filters.push({
        propertyNameRaw,
        propertyName: friendlyName,
        predicate,
        value,
      });
    }
  });

  // Special case: single filter, no check
  if (filters.length === 1 && !check) {
    const f = filters[0];
    const message = `Matches: ${describePredicate(
      f.propertyName,
      f.predicate,
      f.value
    )}`;
    autoGeneratedInput.value = message;
    messageInput.value = message;
    return;
  }

  // Build filter text
  const filterParts = filters.map((f) =>
    describePredicate(f.propertyName, f.predicate, f.value)
  );
  const whereClause =
    filterParts.length > 0 ? `where ${filterParts.join(' and ')}` : '';

  // Build check text
  let checkClause = '';
  if (check) {
    // Check if the property is filtered for existence
    const filteredForExistence = filters.some(
      (f) =>
        f.propertyNameRaw === check.propertyNameRaw && f.predicate === 'exists'
    );
    const needsExistence = !filteredForExistence;
    const failsIfMissingPredicates = [
      'in list',
      'greater than',
      'less than',
      'equal to',
      'not equal to',
      'in range',
      'is like',
      'identical to',
      'contains',
      'does not contain',
    ];
    const failsIfMissing = failsIfMissingPredicates.includes(check.predicate);

    if (needsExistence && failsIfMissing) {
      // Use 'must be present and matching ...' phrasing
      if (check.predicate === 'in list') {
        checkClause = `${
          check.propertyName
        } must be present and matching one of: ${formatList(check.value)}`;
      } else if (check.predicate === 'equal to') {
        checkClause = `${check.propertyName} must be present and equal to ${check.value}`;
      } else if (check.predicate === 'greater than') {
        checkClause = `${check.propertyName} must be present and greater than ${check.value}`;
      } else if (check.predicate === 'less than') {
        checkClause = `${check.propertyName} must be present and less than ${check.value}`;
      } else if (check.predicate === 'in range') {
        const [min, max] = check.value.split(',').map((v) => v.trim());
        checkClause = `${check.propertyName} must be present and between ${min} and ${max}`;
      } else {
        checkClause = `${check.propertyName} must be present and ${check.predicate} ${check.value}`;
      }
    } else {
      // Standard phrasing
      checkClause = describePredicate(
        check.propertyName,
        check.predicate,
        check.value
      );
    }
  }

  // Compose the final message
  let message = 'For all elements';
  if (whereClause) message += ' ' + whereClause;
  if (checkClause) message += ', ' + checkClause;

  autoGeneratedInput.value = message;
  messageInput.value = message;
}

// Named event handler for HTMX after-settle
function handleHtmxAfterSettle(evt) {
  const target = evt.detail.target;

  // Handle new condition rows
  if (target.classList.contains('condition-row')) {
    const select = target.querySelector('.predicate-select');
    if (select) {
      handlePredicateChange(select);
    }
  }

  // Handle conditions list updates
  if (target.id === 'conditions-list') {
    // Initialize predicate state for all rows in the list
    target.querySelectorAll('.predicate-select').forEach((select) => {
      handlePredicateChange(select);
    });
    updateConditionLogic();
    updateConditionIndexes();
    generateMessageFromConditions();
  }

  if (
    evt.detail &&
    evt.detail.target &&
    evt.detail.target.id === 'rule-form-container'
  ) {
    updateConditionLogic();
    generateMessageFromConditions();
  }

  // Handle edit form container updates
  if (target.id === 'rule-form-container') {
    updateConditionLogic();
    updateConditionIndexes();
    generateMessageFromConditions();

    // Reattach move button event listeners
    const conditionsList = document.getElementById('conditions-list');
    if (conditionsList) {
      conditionsList.addEventListener('click', function (event) {
        const button = event.target.closest('.up-arrow, .down-arrow');
        if (button) {
          handleConditionReorder(button);
          generateMessageFromConditions();
        }
      });
    }
  }
}

// Add event listeners
document.addEventListener('DOMContentLoaded', function () {
  // Initialize predicate state for all rows
  document.querySelectorAll('.predicate-select').forEach((select) => {
    handlePredicateChange(select);
  });

  // Initialize logic pattern
  updateConditionLogic();
  updateConditionIndexes();

  // Use event delegation for arrow buttons
  document
    .getElementById('conditions-list')
    .addEventListener('click', function (event) {
      const button = event.target.closest('.up-arrow, .down-arrow');
      if (button) {
        handleConditionReorder(button);
      }
    });

  // Add HTMX event handler
  document.body.addEventListener('htmx:afterSettle', handleHtmxAfterSettle);

  // Add event listener for manual message edits
  const messageInput = document.getElementById('message');
  if (messageInput) {
    messageInput.addEventListener('input', function () {
      this.dataset.manuallyEdited = 'true';
    });
  }
});

// Handle predicate changes using event delegation
document.body.addEventListener('change', function (event) {
  const select = event.target.closest('.predicate-select');
  if (select) {
    handlePredicateChange(select);
    generateMessageFromConditions();
  }
});

// Handle condition removal
document.body.addEventListener('htmx:afterRequest', function (evt) {
  const target = evt.detail.target;

  if (target.id === 'conditions-list') {
    updateConditionLogic();
    generateMessageFromConditions();
  }

  // Handle new condition rows
  if (target.classList.contains('condition-row')) {
    const select = target.querySelector('.predicate-select');
    if (select) {
      handlePredicateChange(select);
    }
    generateMessageFromConditions();
  }
});

// Handle property name changes
document.body.addEventListener('input', function (evt) {
  if (
    evt.target.name &&
    (evt.target.name.endsWith('[propertyName]') ||
      evt.target.name.endsWith('[value]') ||
      evt.target.name.endsWith('[predicate]') ||
      evt.target.name.endsWith('[logic]'))
  ) {
    updateConditionLogic();
    generateMessageFromConditions();
  }
});

// Auto-resize textarea for message field
function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = el.scrollHeight + 'px';
}

document.addEventListener('input', function (event) {
  if (event.target.id === 'message') {
    autoResizeTextarea(event.target);
  }
});

document.addEventListener('DOMContentLoaded', function () {
  const messageTextarea = document.getElementById('message');
  if (messageTextarea) autoResizeTextarea(messageTextarea);
});
