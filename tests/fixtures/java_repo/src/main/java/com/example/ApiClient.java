package com.example;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import com.google.gson.Gson;
import java.io.IOException;

/**
 * Sample Java REST API client
 */
public class ApiClient {
    private static final String API_BASE = "https://api.example.com";
    private final OkHttpClient httpClient = new OkHttpClient();
    private final Gson gson = new Gson();

    /**
     * Get user by ID
     */
    public User getUser(String userId) throws IOException {
        Request request = new Request.Builder()
                .url(API_BASE + "/api/v1/users/" + userId)
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (response.isSuccessful() && response.body() != null) {
                return gson.fromJson(response.body().string(), User.class);
            }
        }
        return null;
    }

    /**
     * Create a new post
     */
    public Post createPost(String postTitle, String postContent) throws IOException {
        Post post = new Post();
        post.setTitle(postTitle);
        post.setContent(postContent);

        String json = gson.toJson(post);
        RequestBody body = RequestBody.create(json, okhttp3.MediaType.parse("application/json"));

        Request request = new Request.Builder()
                .url(API_BASE + "/api/v1/posts")
                .post(body)
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (response.isSuccessful() && response.body() != null) {
                return gson.fromJson(response.body().string(), Post.class);
            }
        }
        return null;
    }

    /**
     * User model
     */
    public static class User {
        private String id;
        private String user_name;
        private String email_address;

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getUserName() { return user_name; }
        public void setUserName(String user_name) { this.user_name = user_name; }

        public String getEmailAddress() { return email_address; }
        public void setEmailAddress(String email_address) { this.email_address = email_address; }
    }

    /**
     * Post model
     */
    public static class Post {
        private String id;
        private String post_title;
        private String post_content;

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getTitle() { return post_title; }
        public void setTitle(String title) { this.post_title = title; }

        public String getContent() { return post_content; }
        public void setContent(String content) { this.post_content = content; }
    }
}
