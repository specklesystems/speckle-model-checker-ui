/**
 * app.js
 * Core application initialization
 */

const App = {
  // Current Firebase token
  currentFirebaseToken: null,
  
  // Initialize the application
  initialize: function(firebaseConfig) {
    // Initialize Firebase
    firebase.initializeApp(firebaseConfig);
    
    // Initialize all modules
    Auth.initialize(firebase);
    UI.initialize();
    Navigation.initialize();
    
    // Check for authentication callback
    if (Auth.isAuthCallback()) {
      console.log("Callback detected. Processing...");
      document.getElementById('login-container').classList.add('hidden');
      Auth.processAuthCallback();
    } else {
      console.log("No callback detected. Checking auth state...");
      
      // Initialize the correct UI state based on current auth
      const user = Auth.getCurrentUser();
      if (user) {
        document.getElementById('user-profile').classList.remove('hidden');
        user.getIdToken(true).then(token => {
          this.currentFirebaseToken = token;
        });
      } else {
        document.getElementById('login-container').classList.remove('hidden');
      }
    }
    
    // Ensure dropdowns are closed initially
    document.getElementById('user-dropdown-menu').classList.add('hidden');
    document.getElementById('login-dropdown-menu').classList.add('hidden');
  }
};

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Initialize app with Firebase config
  App.initialize(firebaseConfig);
  
  // Check for initial severity dropdowns
  UI.updateSeverityColor();
});