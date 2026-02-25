package com.example;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import com.google.gson.Gson;
import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * REST API client.
 *
 * The base URL is loaded from application.properties (key: api.base-url).
 * The secondary constructor accepts an explicit URL for test injection —
 * this is the seam the test uses to redirect calls to WireMock.
 */
public class ApiClient {

    private final String apiBaseUrl;
    private final OkHttpClient httpClient;
    private final Gson gson;

    /** Production constructor — reads api.base-url from application.properties. */
    public ApiClient() {
        this(loadBaseUrl());
    }

    /**
     * Test-injection constructor.
     * Accepts any base URL, which lets tests point the client at WireMock
     * without touching the properties file.
     */
    public ApiClient(String apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.httpClient = new OkHttpClient();
        this.gson = new Gson();
    }

    /**
     * Reads api.base-url from /application.properties on the classpath.
     *
     * This is the READER method the migration harness needs to detect:
     *   property file  →  this method  →  passed to constructors and HTTP calls.
     */
    static String loadBaseUrl() {
        Properties props = new Properties();
        try (InputStream is = ApiClient.class.getResourceAsStream("/application.properties")) {
            if (is != null) {
                props.load(is);
            }
        } catch (IOException ignored) {
        }
        return props.getProperty("api.base-url", "https://api.example.com");
    }

    // ---------- API Methods ----------

    /**
     * GET /api/v1/users/{id}
     *
     * Uses apiBaseUrl (from properties) as prefix — the migration harness
     * should replace this entire method with a GraphQL query.
     */
    public User getUser(String userId) throws IOException {
        Request request = new Request.Builder()
                .url(apiBaseUrl + "/api/v1/users/" + userId)
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (response.isSuccessful() && response.body() != null) {
                return gson.fromJson(response.body().string(), User.class);
            }
        }
        return null;
    }

    /**
     * POST /api/v1/posts
     *
     * Same pattern: uses apiBaseUrl prefix.
     */
    public Post createPost(String postTitle, String postContent) throws IOException {
        Post post = new Post();
        post.setTitle(postTitle);
        post.setContent(postContent);

        String json = gson.toJson(post);
        RequestBody body = RequestBody.create(json, okhttp3.MediaType.parse("application/json"));

        Request request = new Request.Builder()
                .url(apiBaseUrl + "/api/v1/posts")
                .post(body)
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (response.isSuccessful() && response.body() != null) {
                return gson.fromJson(response.body().string(), Post.class);
            }
        }
        return null;
    }

    // ---------- Models ----------

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
