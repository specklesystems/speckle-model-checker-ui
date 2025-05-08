/**
 * rulesets.js
 * Handles ruleset-specific functionality and HTMX enhancements
 */

const Rulesets = {
    // Initialize HTMX event handlers and observers
    init: function() {
        this.setupDeleteConfirmations();
    },

    // Setup confirmation dialogs for delete actions
    setupDeleteConfirmations: function() {
        document.body.addEventListener('click', function(e) {
            if (e.target.matches('[hx-delete]')) {
                if (!confirm('Are you sure you want to delete this item?')) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }
        });
    },

    // Handle form submission errors
    handleFormError: function(error) {
        console.error('Form submission error:', error);
        // You could add custom error handling here, like showing a toast
    },

    // Handle delete errors
    handleDeleteError: function(error) {
        console.error('Delete error:', error);
        // You could add custom error handling here, like showing a toast
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    Rulesets.init();
}); 