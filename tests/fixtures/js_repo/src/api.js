// Sample JavaScript file with REST API calls

const axios = require('axios');

const API_BASE = 'https://api.example.com';

// Get user by ID
async function getUser(userId) {
  try {
    const response = await axios.get(`${API_BASE}/api/v1/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user:', error);
    throw error;
  }
}

// Create a new post
async function createPost(title, content) {
  try {
    const response = await axios.post(`${API_BASE}/api/v1/posts`, {
      post_title: title,
      post_content: content,
      user_id: 1,
    });
    return response.data;
  } catch (error) {
    console.error('Error creating post:', error);
    throw error;
  }
}

// Update user profile
async function updateUserProfile(userId, userName, emailAddress) {
  try {
    const response = await fetch(
      `${API_BASE}/api/v1/users/${userId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_name: userName,
          email_address: emailAddress,
        }),
      }
    );
    return response.json();
  } catch (error) {
    console.error('Error updating profile:', error);
    throw error;
  }
}

module.exports = {
  getUser,
  createPost,
  updateUserProfile,
};
