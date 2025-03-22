/**
 * api.js
 * Handles all API communication
 */

const API = {
  // Default timeout for API calls (in milliseconds)
  TIMEOUT: 200,
  
  // Fetch data with authentication
  fetchWithAuth: async function(url, options = {}) {
    try {
      const token = await Auth.getIdToken();
      if (!token) {
        throw new Error('No authentication token available');
      }
      
      // Set default headers if not provided
      if (!options.headers) {
        options.headers = {};
      }
      
      // Add auth token to headers
      options.headers['Authorization'] = `Bearer ${token}`;
      
      // Add small delay to ensure token is properly set
      await new Promise(resolve => setTimeout(resolve, this.TIMEOUT));
      
      // Perform the fetch
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      // Handle different response types
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  },
  
  // Post form data with authentication
  postFormWithAuth: async function(url, formData, method = 'POST', targetSelector = null) {
    try {
      const token = await Auth.getIdToken();
      if (!token) {
        throw new Error('No authentication token available');
      }
      
      // Create request options
      const options = {
        method: method,
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      };
      
      // Add small delay to ensure token is properly set
      await new Promise(resolve => setTimeout(resolve, this.TIMEOUT));
      
      // Perform the fetch
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      const responseText = await response.text();
      
      // Update the target if provided
      if (targetSelector && responseText) {
        document.querySelector(targetSelector).innerHTML = responseText;
      }
      
      return responseText;
    } catch (error) {
      console.error('API form submission failed:', error);
      UI.showToast(`Error: ${error.message}`, true);
      throw error;
    }
  },
  
  // Delete resource with authentication
  deleteWithAuth: async function(url, targetSelector = null) {
    try {
      const token = await Auth.getIdToken();
      if (!token) {
        throw new Error('No authentication token available');
      }
      
      // Create request options
      const options = {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      };
      
      // Add small delay to ensure token is properly set
      await new Promise(resolve => setTimeout(resolve, this.TIMEOUT));
      
      // Perform the fetch
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      // Remove the target element if provided and status is 204 (No Content)
      if (targetSelector && response.status === 204) {
        const element = document.querySelector(targetSelector);
        if (element) element.remove();
      }

      // Replace the target element with the response if status is 200 (OK)
      if (response.status === 200) {
        const responseText = await response.text();
        if (targetSelector && responseText) {
          document.querySelector(targetSelector).innerHTML = responseText;
        }
      }
      
      return true;
    } catch (error) {
      console.error('API delete failed:', error);
      UI.showToast(`Error: ${error.message}`, true);
      throw error;
    }
  }
};