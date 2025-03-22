/**
 * auth.js
 * Handles all authentication-related functionality
 */

const Auth = {
  // Initialize Firebase Auth
  initialize: function(firebase) {
    this.auth = firebase.auth();
    this.setupAuthListener();
  },

  // Set up auth state change listener
  setupAuthListener: function() {
    this.auth.onAuthStateChanged((user) => {
      UI.updateAuthUI(user);

      if (user) {
        // Check if we have a return URL from login
        const returnUrl = localStorage.getItem('speckle:auth:returnUrl');
        if (returnUrl) {
          localStorage.removeItem('speckle:auth:returnUrl');
          window.history.pushState(null, '', returnUrl);
        }
        
        // Store current token for API calls
        user.getIdToken(true).then(token => {
          App.currentFirebaseToken = token;
        });
      }

      Navigation.loadContentBasedOnUrl(user);
    });
  },

  // Sign in with Speckle
  signInToSpeckle: async function() {
    try {
      // Show loading indicator
      document.getElementById('login-container').classList.add('hidden');
      UI.showLoadingIndicator();

      // Close dropdown menu if open
      document.getElementById('login-dropdown-menu').classList.add('hidden');

      // Initialize authentication with the server
      const response = await fetch('/api/auth/init');
      if (!response.ok) {
        throw new Error('Could not initialize authentication');
      }

      const authData = await response.json();

      // Store the challenge ID for later use
      localStorage.setItem('speckle:auth:challengeId', authData.challengeId);
      localStorage.setItem('speckle:auth:appId', authData.appId);
      localStorage.setItem('speckle:auth:appSecret', authData.appSecret);
      localStorage.setItem('speckle:auth:authUrl', authData.authUrl);

      // Save the current URL for after login
      localStorage.setItem('speckle:auth:returnUrl', window.location.pathname + window.location.search);

      // Redirect to Speckle authentication
      window.location.href = authData.authUrl;
    } catch (error) {
      console.error('Authentication initialization error:', error);
      UI.showToast('Failed to initialize login process. Please try again.', true);

      // Reset auth container
      document.getElementById('login-container').classList.remove('hidden');
      UI.hideLoadingIndicator();
    }
  },

  // Sign out
  signOut: function() {
    // Close dropdown menu if open
    document.getElementById('user-dropdown-menu').classList.add('hidden');

    this.auth.signOut().then(() => {
      // Clear any local storage items related to auth
      localStorage.removeItem("speckle:auth:challengeId");
      localStorage.removeItem("speckle:auth:returnUrl");
      localStorage.removeItem("speckle:auth:appId");
      localStorage.removeItem("speckle:auth:appSecret");
      localStorage.removeItem("speckle:auth:authUrl");
      localStorage.removeItem("speckle:auth:token");
      localStorage.removeItem("speckle:auth:refreshToken");

      // Update UI
      document.getElementById('user-profile').classList.add('hidden');
      document.getElementById('login-container').classList.remove('hidden');

      // Clear main content and show welcome screen
      UI.showWelcomeScreen();
    }).catch((error) => {
      console.error("Error signing out:", error);
      UI.showToast("Error signing out", true);
    });
  },

  // Process authentication callback
  processAuthCallback: async function() {
    UI.showLoadingIndicator();
    
    try {
      // Get URL parameters and stored challenge ID
      const params = new URLSearchParams(window.location.search);
      const accessCode = params.get("access_code");
      const challengeId = localStorage.getItem("speckle:auth:challengeId");
      const appId = localStorage.getItem("speckle:auth:appId");
      const authUrl = localStorage.getItem("speckle:auth:authUrl");
      const appSecret = localStorage.getItem("speckle:auth:appSecret");

      if (!accessCode || !challengeId) {
        throw new Error("Missing authentication parameters");
      }

      // Extract the server URL from the auth URL
      const serverUrl = authUrl.split("/").slice(0, 3).join("/");

      // Exchange access code for token
      const response = await fetch(`${serverUrl}/auth/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          accessCode: accessCode,
          challenge: challengeId,
          appSecret: appSecret,
          appId: appId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }

      const authData = await response.json();

      // Store tokens
      localStorage.setItem("speckle:auth:token", authData.token);
      localStorage.setItem("speckle:auth:refreshToken", authData.refreshToken);

      // Clean up auth parameters
      localStorage.removeItem("speckle:auth:challengeId");
      localStorage.removeItem("speckle:auth:appId");
      localStorage.removeItem("speckle:auth:appSecret");
      localStorage.removeItem("speckle:auth:authUrl");

      // Get user info from server
      const userResponse = await fetch('/api/auth/users', {
        method: 'POST',
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ token: authData.token, refreshToken: authData.refreshToken })
      });

      if (!userResponse.ok) {
        throw new Error('Failed to get user information');
      }

      const userData = await userResponse.json();

      // Sign in with the custom token
      await this.auth.signInWithCustomToken(userData.customToken);

      UI.showToast('Successfully signed in');

      // Clean up URL without page reload
      const cleanUrl = window.location.pathname + window.location.hash;
      window.history.replaceState({}, document.title, cleanUrl);

      // Hide loading indicator
      UI.hideLoadingIndicator();

    } catch (error) {
      // Handle errors
      console.error("Authentication error:", error);
      UI.showToast('Authentication failed: ' + error.message, true);
      UI.hideLoadingIndicator();
    }
  },

  // Handle auth redirect (when returning from Speckle auth)
  handleAuthRedirect: function() {
    // Get URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const authenticated = urlParams.get('authenticated');
    const firebaseToken = urlParams.get('ft');
    const sst = urlParams.get('sst');
    const ssrt = urlParams.get('ssrt');

    // Check if this is an auth callback
    if (authenticated && firebaseToken) {
      console.log('Authentication redirect detected');

      // Parse authentication state
      const authenticatedState = authenticated === 'True';

      // Check if authentication was successful
      if (authenticatedState) {
        // Store the token in localStorage
        localStorage.setItem('firebase:authToken', firebaseToken);

        // Sign in with the custom token
        this.auth.signInWithCustomToken(firebaseToken)
          .then(() => {
            console.log('Successfully signed in with custom token');
            UI.showToast('Successfully signed in');
          })
          .catch((error) => {
            console.error('Error signing in with custom token:', error);
            UI.showToast('Failed to sign in with the provided token', true);
          });

      } else {
        UI.showToast('Authentication failed', true);
      }

      // Clean up URL without page reload
      const cleanUrl = window.location.pathname + window.location.hash;
      window.history.replaceState({}, document.title, cleanUrl);
    }
  },

  // Check if current URL is an auth callback
  isAuthCallback: function() {
    const params = new URLSearchParams(window.location.search);
    return params.get('access_code') !== null;
  },

  // Get current user
  getCurrentUser: function() {
    return this.auth.currentUser;
  },

  // Get ID token for current user
  getIdToken: async function() {
    const user = this.getCurrentUser();
    if (user) {
      try {
        return await user.getIdToken(true);
      } catch (error) {
        console.error("Error getting ID token:", error);
        return null;
      }
    }
    return null;
  }
};