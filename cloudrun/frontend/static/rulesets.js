/**
 * rulesets.js
 * Handles ruleset-specific functionality and HTMX enhancements
 */

console.debug('rulesets.js loaded and running');

const Rulesets = {
  // Initialize HTMX event handlers and observers
  init: function () {
    this.setupDeleteConfirmations();
    this.setupDirtyCheck();
  },

  // Setup confirmation dialogs for delete actions
  setupDeleteConfirmations: function () {
    document.body.addEventListener('click', function (e) {
      if (e.target.matches('[hx-delete]')) {
        if (!confirm('Are you sure you want to delete this item?')) {
          e.preventDefault();
          e.stopPropagation();
        }
      }
    });
  },

  // Handle form submission errors
  handleFormError: function (error) {
    console.error('Form submission error:', error);
    // You could add custom error handling here, like showing a toast
  },

  // Handle delete errors
  handleDeleteError: function (error) {
    console.error('Delete error:', error);
    // You could add custom error handling here, like showing a toast
  },

  setupDirtyCheck: function () {
    console.debug('setupDirtyCheck called');
    // Name field
    const nameInput = document.getElementById('name');
    const nameActions = document.getElementById('name-actions');
    const cancelNameBtn = document.getElementById('cancel-name-btn');
    let initialName = nameInput ? nameInput.value : '';
    let nameWasDirty = false;

    // Description field
    const descInput = document.getElementById('description');
    const descActions = document.getElementById('desc-actions');
    const cancelDescBtn = document.getElementById('cancel-desc-btn');
    let initialDesc = descInput ? descInput.value : '';
    let descWasDirty = false;

    console.debug('Name input:', nameInput, 'Desc input:', descInput);

    function handleNameEvent(e) {
      const isDirty = nameInput.value !== initialName;
      console.debug(
        `[Name] Event: ${e.type}, value: '${nameInput.value}', initial: '${initialName}', dirty: ${isDirty}`
      );
      if (isDirty !== nameWasDirty) {
        if (isDirty) {
          console.debug('[Name] Field became dirty');
        } else {
          console.debug('[Name] Field reverted to clean');
        }
        nameWasDirty = isDirty;
      }
      nameActions.style.display = isDirty ? '' : 'none';
    }

    function handleDescEvent(e) {
      const isDirty = descInput.value !== initialDesc;
      console.debug(
        `[Desc] Event: ${e.type}, value: '${descInput.value}', initial: '${initialDesc}', dirty: ${isDirty}`
      );
      if (isDirty !== descWasDirty) {
        if (isDirty) {
          console.debug('[Desc] Field became dirty');
        } else {
          console.debug('[Desc] Field reverted to clean');
        }
        descWasDirty = isDirty;
      }
      descActions.style.display = isDirty ? '' : 'none';
    }

    if (nameInput && nameActions && cancelNameBtn) {
      nameInput.addEventListener('input', handleNameEvent);
      nameInput.addEventListener('change', handleNameEvent);
      nameInput.addEventListener('keyup', handleNameEvent);
      cancelNameBtn.addEventListener('click', function () {
        nameInput.value = initialName;
        nameActions.style.display = 'none';
        if (nameWasDirty) {
          console.debug('[Name] Field reverted to clean (via cancel)');
          nameWasDirty = false;
        }
      });
      // After save, update initial value and hide actions
      nameInput.form &&
        nameInput.form.addEventListener('htmx:afterRequest', function (evt) {
          if (
            evt.target === nameInput.form &&
            evt.detail &&
            evt.detail.elt &&
            evt.detail.elt.id === 'save-name-btn'
          ) {
            initialName = nameInput.value;
            nameActions.style.display = 'none';
            nameWasDirty = false;
            console.debug('[Name] Save: new clean state set');
          }
        });
    } else {
      console.debug('[Name] One or more elements missing:', {
        nameInput,
        nameActions,
        cancelNameBtn,
      });
    }

    if (descInput && descActions && cancelDescBtn) {
      descInput.addEventListener('input', handleDescEvent);
      descInput.addEventListener('change', handleDescEvent);
      descInput.addEventListener('keyup', handleDescEvent);
      cancelDescBtn.addEventListener('click', function () {
        descInput.value = initialDesc;
        descActions.style.display = 'none';
        if (descWasDirty) {
          console.debug('[Desc] Field reverted to clean (via cancel)');
          descWasDirty = false;
        }
      });
      // After save, update initial value and hide actions
      descInput.form &&
        descInput.form.addEventListener('htmx:afterRequest', function (evt) {
          if (
            evt.target === descInput.form &&
            evt.detail &&
            evt.detail.elt &&
            evt.detail.elt.id === 'save-desc-btn'
          ) {
            initialDesc = descInput.value;
            descActions.style.display = 'none';
            descWasDirty = false;
            console.debug('[Desc] Save: new clean state set');
          }
        });
    } else {
      console.debug('[Desc] One or more elements missing:', {
        descInput,
        descActions,
        cancelDescBtn,
      });
    }
  },
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
  Rulesets.init();
});

document.addEventListener('htmx:afterSwap', function (evt) {
  // Only re-initialize if a field container or the form was swapped in
  if (
    evt.target.id === 'name-field-container' ||
    evt.target.id === 'desc-field-container' ||
    evt.target.id === 'form-container'
  ) {
    Rulesets.setupDirtyCheck();
  }
});
