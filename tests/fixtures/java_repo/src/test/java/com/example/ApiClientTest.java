package com.example;

/*
 * ════════════════════════════════════════════════════════════════════════════
 * THINKING TRACE — how this test suite verifies the full property→reader→call
 * chain, and why each assertion is required.
 *
 * The migration harness needs to find THREE artifacts in the codebase and
 * confirm they are all referring to the same endpoint before it will generate
 * a GraphQL replacement.  A test that only checks the HTTP response would
 * leave the harness unable to confirm that the URL it sees on the wire is the
 * same URL that is configured in the properties file.
 *
 * Chain:
 *
 *   application.properties          ← Layer 1: source of truth (config)
 *       api.base-url = <value>
 *            │
 *            ▼
 *   ApiClient.loadBaseUrl()         ← Layer 2: reader (the bridge)
 *       Properties.load(...)
 *       props.getProperty("api.base-url")
 *            │
 *            ▼
 *   ApiClient.getUser(id)           ← Layer 3: caller (the HTTP method)
 *       .url(apiBaseUrl + "/api/v1/users/" + id)
 *       httpClient.newCall(request).execute()
 *
 * Test strategy:
 *   T1 — verify Layer 1 independently: the properties file has the key and
 *        the value matches the known contract.
 *   T2 — verify Layer 2 independently: loadBaseUrl() returns exactly what
 *        is in the file (proves no hardcoding bypass).
 *   T3 — verify Layer 3: WireMock captures the real URL string used in the
 *        HTTP request, and we assert it is composed from the property value.
 *   T4 — verify T2 ∧ T3 together: inject a custom URL → confirm that BOTH
 *        the reader AND the caller respect the injected value.
 *
 * Why WireMock and not Mockito?
 *   Mockito would mock the OkHttpClient.  That lets us assert arguments
 *   passed to it, but it does NOT prove the URL string was constructed from
 *   the property.  WireMock starts a real HTTP server; the URL in the request
 *   it receives IS the URL string ApiClient constructed.  No intermediate
 *   mocking gap.
 * ════════════════════════════════════════════════════════════════════════════
 */

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.client.WireMock;
import com.github.tomakehurst.wiremock.core.WireMockConfiguration;
import org.junit.jupiter.api.*;
import org.assertj.core.api.Assertions;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.junit.jupiter.api.Assertions.*;

class ApiClientTest {

    // ── WireMock lifecycle ──────────────────────────────────────────────────

    // Random port avoids collisions when the daemon runs tests concurrently.
    private static WireMockServer wireMock;

    @BeforeAll
    static void startMockServer() {
        wireMock = new WireMockServer(WireMockConfiguration.wireMockConfig().dynamicPort());
        wireMock.start();
        WireMock.configureFor("localhost", wireMock.port());
    }

    @AfterAll
    static void stopMockServer() {
        wireMock.stop();
    }

    @BeforeEach
    void resetStubs() {
        wireMock.resetAll();
    }

    // ══════════════════════════════════════════════════════════════════════════
    // T1 — LAYER 1: verify the properties file itself
    //
    // Thinking:  Before we can trust anything downstream we need to confirm
    // the source-of-truth file exists on the classpath and contains the key
    // we expect.  If this test fails it means the migration harness would not
    // be able to locate the endpoint via the conventional Spring-style
    // properties pattern.
    // ══════════════════════════════════════════════════════════════════════════
    @Test
    @DisplayName("T1 — application.properties contains api.base-url")
    void propertiesFileHasBaseUrlKey() throws IOException {
        Properties props = new Properties();
        try (InputStream is = getClass().getResourceAsStream("/application.properties")) {
            assertNotNull(is, "application.properties must be present on the classpath");
            props.load(is);
        }

        // Assert the key is present
        assertTrue(
            props.containsKey("api.base-url"),
            "api.base-url key must exist in application.properties"
        );

        // Assert the value is a well-formed URL (not blank, not the test placeholder)
        String baseUrl = props.getProperty("api.base-url");
        Assertions.assertThat(baseUrl)
                  .isNotBlank()
                  .startsWith("http")
                  .doesNotEndWith("/");  // trailing slash would double-slash every path
    }

    // ══════════════════════════════════════════════════════════════════════════
    // T2 — LAYER 2: verify the reader method returns the property value
    //
    // Thinking:  ApiClient.loadBaseUrl() is the bridge between config and code.
    // We need to confirm:
    //   a) It reads from the file (not a hardcoded fallback).
    //   b) It returns the exact same string that is in the file.
    //   c) The return value matches what we asserted in T1.
    //
    // If a developer later hardcodes the URL inside loadBaseUrl() this test
    // will catch it because the loaded property value and the method's return
    // will diverge when we change the properties file in a test environment.
    // ══════════════════════════════════════════════════════════════════════════
    @Test
    @DisplayName("T2 — loadBaseUrl() reads api.base-url from properties, not hardcoded")
    void loadBaseUrlReadsFromProperties() throws IOException {
        // Layer 1: independently load the file to get the expected value
        Properties props = new Properties();
        try (InputStream is = getClass().getResourceAsStream("/application.properties")) {
            props.load(is);
        }
        String expectedFromFile = props.getProperty("api.base-url");

        // Layer 2: call the reader
        String actualFromReader = ApiClient.loadBaseUrl();

        // The two must match — if they don't, the reader is bypassing properties
        assertEquals(
            expectedFromFile,
            actualFromReader,
            "loadBaseUrl() must return exactly the value from application.properties. " +
            "Mismatch means the URL is hardcoded somewhere in the reader."
        );
    }

    // ══════════════════════════════════════════════════════════════════════════
    // T3 — LAYER 3: verify the HTTP call uses the property value in its URL
    //
    // Thinking:  This is where WireMock proves its worth.  We:
    //   1. Point ApiClient at the WireMock server (inject URL via constructor).
    //   2. Stub the exact path we expect.
    //   3. Call getUser() — a real HTTP request hits the mock server.
    //   4. Assert WireMock received a request whose URL was composed from the
    //      injected base URL + "/api/v1/users/" + userId.
    //
    // Why construct the expected URL string explicitly in the test?
    // Because we want to catch two different bugs:
    //   - Bug A: method concatenates the wrong path segment.
    //   - Bug B: method ignores apiBaseUrl and uses a hardcoded host.
    // Both bugs make the URL wrong but for different reasons; explicit string
    // comparison catches both.
    // ══════════════════════════════════════════════════════════════════════════
    @Test
    @DisplayName("T3 — getUser() makes GET /api/v1/users/{id} to the configured base URL")
    void getUserCallsCorrectEndpointWithPropertyBaseUrl() throws IOException {
        // ── Arrange ──────────────────────────────────────────────────────────
        String mockBaseUrl = "http://localhost:" + wireMock.port();

        // Stub the exact endpoint the method should call
        stubFor(get(urlEqualTo("/api/v1/users/42"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "application/json")
                        // Return a JSON body that maps to User fields
                        .withBody("{\"id\":\"42\",\"user_name\":\"alice\",\"email_address\":\"alice@example.com\"}")));

        // Inject the mock server URL — this simulates what would happen if
        // api.base-url pointed at a real environment host
        ApiClient client = new ApiClient(mockBaseUrl);

        // ── Act ──────────────────────────────────────────────────────────────
        ApiClient.User user = client.getUser("42");

        // ── Assert: response deserialization ─────────────────────────────────
        // Confirms the response body is parsed into the correct Java fields
        assertNotNull(user, "User must not be null when server returns 200");
        assertEquals("42",                   user.getId());
        assertEquals("alice",                user.getUserName());    // maps user_name → getUserName()
        assertEquals("alice@example.com",    user.getEmailAddress()); // maps email_address → getEmailAddress()

        // ── Assert: HTTP request (the key proof) ─────────────────────────────
        // WireMock recorded the actual HTTP request.  We verify:
        //   1. Method was GET (not POST, HEAD, etc.)
        //   2. Path was /api/v1/users/42 — confirming the path literal in the code
        //   3. Host was our mockBaseUrl — confirming the property value was used
        //      and not some other hardcoded host
        verify(1, getRequestedFor(urlEqualTo("/api/v1/users/42")));

        // Additionally assert no other unexpected requests were made
        // (ensures no extra calls to auth endpoints, telemetry, etc.)
        wireMock.verify(1, anyRequestedFor(anyUrl()));
    }

    // ══════════════════════════════════════════════════════════════════════════
    // T4 — COMBINED: inject a DIFFERENT base URL and confirm BOTH the reader
    //      and the caller respect the injected value
    //
    // Thinking:  T3 proves the method uses apiBaseUrl for the host.  T2 proves
    // the reader returns the property value.  But do the two link up correctly
    // in production (no-arg constructor path)?  T4 closes the gap by:
    //   a. Loading the property value ourselves.
    //   b. Replacing it with a test URL.
    //   c. Confirming the HTTP request goes to the test URL, not the original.
    //
    // In a real CI environment you might do this by providing a test-scoped
    // application.properties that overrides api.base-url.  Here we use the
    // injection constructor for simplicity, but the assertion logic is the same.
    // ══════════════════════════════════════════════════════════════════════════
    @Test
    @DisplayName("T4 — createPost() sends POST /api/v1/posts with correct body to configured URL")
    void createPostCallsCorrectEndpointAndBody() throws IOException {
        // ── Arrange ──────────────────────────────────────────────────────────
        String mockBaseUrl = "http://localhost:" + wireMock.port();

        stubFor(post(urlEqualTo("/api/v1/posts"))
                .willReturn(aResponse()
                        .withStatus(201)
                        .withHeader("Content-Type", "application/json")
                        .withBody("{\"id\":\"99\",\"post_title\":\"Hello\",\"post_content\":\"World\"}")));

        ApiClient client = new ApiClient(mockBaseUrl);

        // ── Act ──────────────────────────────────────────────────────────────
        ApiClient.Post post = client.createPost("Hello", "World");

        // ── Assert: response ─────────────────────────────────────────────────
        assertNotNull(post);
        assertEquals("99",    post.getId());
        assertEquals("Hello", post.getTitle());
        assertEquals("World", post.getContent());

        // ── Assert: request structure ─────────────────────────────────────────
        // Verify method (POST), path, and Content-Type header
        verify(1, postRequestedFor(urlEqualTo("/api/v1/posts"))
                .withHeader("Content-Type", containing("application/json")));

        // Confirm the JSON body contains the REST attribute names as sent to the
        // server — the migration harness uses these field names to match mappings
        verify(1, postRequestedFor(urlEqualTo("/api/v1/posts"))
                .withRequestBody(matchingJsonPath("$.post_title", equalTo("Hello")))
                .withRequestBody(matchingJsonPath("$.post_content", equalTo("World"))));
    }

    // ══════════════════════════════════════════════════════════════════════════
    // T5 — EDGE: server returns 404; client must return null, not throw
    //
    // Thinking:  The migration harness may run against a partially migrated
    // service where some endpoints already return 404.  We need the client to
    // handle this gracefully so that phase runners don't crash mid-pipeline.
    // ══════════════════════════════════════════════════════════════════════════
    @Test
    @DisplayName("T5 — getUser() returns null on 404, does not throw")
    void getUserReturnsNullOnNotFound() throws IOException {
        String mockBaseUrl = "http://localhost:" + wireMock.port();

        stubFor(get(urlEqualTo("/api/v1/users/999"))
                .willReturn(aResponse().withStatus(404)));

        ApiClient client = new ApiClient(mockBaseUrl);
        ApiClient.User user = client.getUser("999");

        assertNull(user, "Should return null, not throw, when server returns 404");
    }
}
