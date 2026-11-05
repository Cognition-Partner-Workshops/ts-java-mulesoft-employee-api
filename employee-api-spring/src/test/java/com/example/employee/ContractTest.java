package com.example.employee;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.testcontainers.containers.PostgreSQLContainer;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ContractTest {
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:15");
    static final ObjectMapper JSON = new ObjectMapper();
    static {
        POSTGRES.start();
        System.setProperty("test.db.url", POSTGRES.getJdbcUrl());
        System.setProperty("test.db.user", POSTGRES.getUsername());
        System.setProperty("test.db.password", POSTGRES.getPassword());
        try (var c = DriverManager.getConnection(POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())) {
            c.createStatement().execute(Files.readString(Path.of("../legacy-standin/seed.sql")));
        } catch (Exception exc) { throw new ExceptionInInitializerError(exc); }
    }
    @LocalServerPort int port;
    record Result(int status, JsonNode body, String contentType) {}

    Result call(String path, String method, Object data, String auth, String type) throws Exception {
        var builder = HttpRequest.newBuilder(URI.create("http://localhost:" + port + path)).header("Content-Type", type);
        if (auth != null) builder.header("Authorization", auth);
        var payload = data == null ? HttpRequest.BodyPublishers.noBody() :
            HttpRequest.BodyPublishers.ofString(data instanceof String s ? s : JSON.writeValueAsString(data));
        var response = HttpClient.newHttpClient().send(builder.method(method, payload).build(), HttpResponse.BodyHandlers.ofString());
        return new Result(response.statusCode(), response.body().isEmpty() ? null : JSON.readTree(response.body()), response.headers().firstValue("Content-Type").orElse(null));
    }
    Result call(String path, String method, Object data) throws Exception {
        return call(path, method, data, null, "application/json");
    }
    String access() throws Exception {
        Result response = call("/oauth/token", "POST", Map.of("client_id", "demo_client", "client_secret", "demo_secret"));
        assertEquals(200, response.status());
        assertEquals("application/json", response.contentType());
        assertTrue(response.body().get("access_token").asText().matches("[0-9a-f-]{36}-\\d{4}-.*Z"));
        return response.body().get("access_token").asText();
    }
    Result employee(String id, String endpoint, String access) throws Exception {
        return call("/api/employee/" + id + "/" + endpoint, "GET", null, access == null ? null : "Bearer " + access, "application/json");
    }

    @Test void requiredFieldTruthiness() throws Exception {
        for (Object absent : java.util.Arrays.asList(null, false, 0, 0L, 0.0, -0.0,
                new java.math.BigDecimal("0.00"), "", java.util.List.of(), Map.of())) {
            assertFalse(Api.present(absent), "Expected absent: " + absent);
            Result result = call("/auth/login", "POST",
                Api.obj("username", "synthetic", "password", "synthetic", "clientId", absent));
            assertEquals(400, result.status());
            assertEquals(JSON.readTree("{\"error\":\"invalid_request\",\"error_description\":\"Missing required fields: username, password, and clientId\"}"), result.body());
        }
        for (Object present : java.util.List.of(true, 1, -1L, 0.5,
                new java.math.BigDecimal("1e-1000"), " ", "0", java.util.List.of(false), Map.of("value", false))) {
            assertTrue(Api.present(present), "Expected present: " + present);
        }
    }

    @Test void oauthAndDatabaseValidation() throws Exception {
        assertEquals(401, call("/oauth/token", "POST", Map.of()).status());
        String first = access(), second = access();
        assertEquals(401, employee("EMP001", "goals", first).status());
        assertEquals(JSON.readTree("[\"Complete Q4 Sales Target\"]"), employee("EMP001", "goals", second).body());
        try (var c = DriverManager.getConnection(POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())) {
            c.createStatement().execute("UPDATE api_clients SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 second' WHERE client_id='demo_client'");
        }
        assertEquals(401, employee("EMP001", "goals", second).status());
    }
    @Test void basicFormAndBadJson() throws Exception {
        String basic = "Basic " + Base64.getEncoder().encodeToString("demo_client:demo_secret".getBytes());
        assertEquals(200, call("/oauth/token", "POST", "", basic, "application/json").status());
        assertEquals(200, call("/oauth/token", "POST", "client_id=demo_client&client_secret=demo_secret", null, "application/x-www-form-urlencoded").status());
        assertEquals(500, call("/oauth/token", "POST", "{").status());
        assertEquals(400, call("/auth/login", "POST", "{").status());
    }
    @Test void endpointAuthAndEmptyCases() throws Exception {
        for (String e : new String[]{"goals", "learning-status"}) {
            assertEquals(401, employee("EMP001", e, null).status());
            assertEquals(401, employee("EMP001", e, "invalid").status());
        }
        String access = access();
        assertEquals("No goals found for employee ABSENT", employee("ABSENT", "goals", access).body().get("message").asText());
        for (String e : new String[]{"learning-status", "next-pay-date", "pto/balance"})
            assertEquals(404, employee("ABSENT", e, access).status());
        assertEquals(120.0, employee("EMP001", "pto/balance", null).body().get("ptoBalance").asDouble());
        assertTrue(employee("EMP001", "pto/balance", null).body().get("ptoBalance").isFloatingPointNumber());
        assertEquals(0.0, employee("EMP002", "pto/balance", null).body().get("ptoBalance").asDouble());
        assertTrue(employee("EMP002", "next-pay-date", null).body().get("nextPayDate").isNull());
        assertEquals("Advanced Sales Techniques", employee("EMP001", "learning-status", access).body().at("/learningStatus/0/course").asText());
    }
    @Test void scheduleAndRouting() throws Exception {
        String path = "/api/employee/EMP001/pto/schedule";
        assertEquals(200, call(path, "POST", Map.of()).status());
        assertTrue(employee("EMP001", "next-pay-date", null).body().get("nextPayDate").isNull());
        assertEquals(500, call(path, "POST", Map.of("endDate", "2024-02-31")).status());
        assertEquals(200, call(path, "POST", Map.of("startDate", "ignored", "endDate", "2024-02-09")).status());
        assertEquals("2024-02-09", employee("EMP001", "next-pay-date", null).body().get("nextPayDate").asText());
        assertEquals(120.0, employee("EMP001", "pto/balance", null).body().get("ptoBalance").asDouble());
        assertEquals(500, call(path, "POST", Map.of("endDate", "bad")).status());
        assertEquals(415, call(path, "POST", "{}", null, "text/plain").status());
        assertEquals(405, call(path, "GET", null).status());
        assertEquals(404, call("/unknown", "GET", null).status());
        var response = HttpClient.newHttpClient().send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + path)).method("OPTIONS", HttpRequest.BodyPublishers.noBody()).build(), HttpResponse.BodyHandlers.ofString());
        assertEquals(200, response.statusCode());
        assertEquals("", response.body());
        assertEquals("POST, GET, OPTIONS", response.headers().firstValue("Access-Control-Allow-Methods").orElseThrow());
        assertEquals("*", response.headers().firstValue("Access-Control-Allow-Origin").orElseThrow());
    }
    @Test void registrationLoginRefreshDisconnect() throws Exception {
        String user = "fixture_" + UUID.randomUUID().toString().replace("-", "");
        var registration = Map.of("username", user, "password", "synthetic", "email", user + "@example.invalid");
        assertEquals(400, call("/auth/register", "POST", Map.of()).status());
        assertEquals(201, call("/auth/register", "POST", registration).status());
        assertEquals(409, call("/auth/register", "POST", registration).status());
        assertEquals(400, call("/auth/login", "POST", Map.of()).status());
        assertEquals(401, call("/auth/login", "POST", Map.of("username", user, "password", "bad", "clientId", user)).status());
        Result login = call("/auth/login", "POST", Map.of("username", user, "password", "synthetic", "clientId", user, "userId", user));
        assertEquals(200, login.status());
        assertEquals(3600, login.body().get("expires_in").asInt());
        assertEquals(400, call("/auth/refresh-token", "POST", Map.of()).status());
        assertEquals(401, call("/auth/refresh-token", "POST", Map.of("refresh_token", "bad")).status());
        assertEquals(200, call("/auth/refresh-token", "POST", Map.of("refresh_token", login.body().get("refresh_token").asText())).status());
        try (var c = DriverManager.getConnection(POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())) {
            var r = c.createStatement().executeQuery("SELECT password_hash FROM users WHERE username='" + user + "'");
            assertTrue(r.next());
            assertEquals(Base64.getEncoder().encodeToString("syntheticsalt".getBytes()), r.getString(1));
            r = c.createStatement().executeQuery("SELECT EXTRACT(EPOCH FROM expires_at - CURRENT_TIMESTAMP), EXTRACT(EPOCH FROM refresh_token_expires_at - CURRENT_TIMESTAMP) FROM api_clients WHERE client_id='" + user + "'");
            assertTrue(r.next());
            assertEquals(3600, r.getDouble(1), 10);
            assertEquals(30 * 86400, r.getDouble(2), 10);
        }
        assertEquals(400, call("/api/disconnect", "POST", Map.of()).status());
        assertEquals(200, call("/api/disconnect", "POST", Map.of("clientId", user, "userId", user)).status());
        assertEquals(404, call("/api/disconnect", "POST", Map.of("clientId", user, "userId", user)).status());
    }
    @Test void callbackIsAsyncAndHtmlUnchanged() throws Exception {
        var queue = new ArrayBlockingQueue<String>(1);
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            queue.add(new String(exchange.getRequestBody().readAllBytes()));
            exchange.sendResponseHeaders(200, -1);
            exchange.close();
        });
        server.start();
        try {
            Result result = call("/oauth/token", "POST", Map.of("client_id", "demo_client", "client_secret", "demo_secret", "callback_url", "http://127.0.0.1:" + server.getAddress().getPort()));
            JsonNode callback = JSON.readTree(queue.poll(5, TimeUnit.SECONDS));
            assertEquals(result.body().get("access_token"), callback.get("token"));
            assertEquals("demo_client", callback.get("userId").asText());
        } finally { server.stop(0); }
        for (String name : new String[]{"login", "register"}) {
            var response = HttpClient.newHttpClient().send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/web/" + name)).build(), HttpResponse.BodyHandlers.ofString());
            assertEquals(Files.readString(Path.of("../src/main/resources/web/" + name + ".html")), response.body());
            assertEquals("text/html", response.headers().firstValue("Content-Type").orElseThrow());
        }
        assertEquals("healthy", call("/health", "GET", null).body().get("status").asText());
    }
    @Test void databaseErrorMapping() throws Exception {
        Database db = mock(Database.class);
        Api api = new Api(db, JSON);
        when(db.rows(anyString(), anyMap())).thenThrow(new CannotGetJdbcConnectionException("offline"));
        assertEquals(401, api.authenticate("Bearer synthetic").status());
        assertEquals("Token validation failed", ((Map<?, ?>) api.authenticate("Bearer synthetic").body()).get("error_description"));
        assertEquals(503, api.employee("EMP001", "pto/balance", Map.of(), "").status());
        assertEquals(500, api.employee("EMP001", "next-pay-date", Map.of(), "").status());
        when(db.rows(eq("Retrieve Token from DB"), anyMap())).thenReturn(java.util.List.of(Map.of("access_token", "synthetic")));
        assertEquals(503, api.employee("EMP001", "goals", Map.of(), "Bearer synthetic").status());
        when(db.rows(eq("Select Employee Goals"), anyMap())).thenThrow(new DataAccessResourceFailureException("query failed"));
        assertEquals(500, api.employee("EMP001", "goals", Map.of(), "Bearer synthetic").status());
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/oauth/token");
        req.setContentType("application/json");
        req.setContent("{}".getBytes());
        MockHttpServletResponse response = new MockHttpServletResponse();
        api.handle(req, response);
        assertEquals(503, response.getStatus());
    }
}
