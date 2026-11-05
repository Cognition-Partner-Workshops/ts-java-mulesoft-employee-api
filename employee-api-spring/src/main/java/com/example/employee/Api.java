package com.example.employee;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.math.BigDecimal;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.core.io.ClassPathResource;
import org.springframework.dao.DataAccessException;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class Api {
    private final Database db;
    private final ObjectMapper mapper;
    private static final Pattern EMPLOYEE = Pattern.compile("/api/employee/([^/]+)/(goals|learning-status|next-pay-date|pto/balance|pto/schedule)");
    private static final Map<String, String> QUERIES = Map.of(
        "goals", "Select Employee Goals", "learning-status", "Select Learning Status",
        "next-pay-date", "Select Next Pay Date", "pto/balance", "Select PTO Balance",
        "pto/schedule", "Insert or Update PTO Schedule");
    record Reply(int status, Object body) {}

    public Api(Database db, ObjectMapper mapper) {
        this.db = db;
        this.mapper = mapper;
    }

    static Map<String, Object> obj(Object... pairs) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) result.put((String) pairs[i], pairs[i + 1]);
        return result;
    }

    static LocalDateTime now() { return LocalDateTime.now(ZoneOffset.UTC); }
    static String token(String prefix) {
        return prefix + UUID.randomUUID() + "-" + now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS")) + "Z";
    }
    static Reply error(int status, String code, String description) {
        return new Reply(status, obj("error", code, "error_description", description));
    }
    static boolean present(Object value) {
        if (value == null || Boolean.FALSE.equals(value)) return false;
        if (value instanceof BigDecimal decimal) return decimal.signum() != 0;
        if (value instanceof Number number) return number.doubleValue() != 0;
        if (value instanceof String text) return !text.isEmpty();
        if (value instanceof List<?> list) return !list.isEmpty();
        if (value instanceof Map<?, ?> map) return !map.isEmpty();
        return true;
    }
    static String hash(Object password) {
        return Base64.getEncoder().encodeToString((password.toString() + "salt").getBytes(StandardCharsets.UTF_8));
    }
    static boolean connectivity(DataAccessException exc) {
        for (Throwable cause = exc; cause != null; cause = cause.getCause()) {
            if (cause instanceof SQLException sql && sql.getSQLState() != null &&
                (sql.getSQLState().startsWith("08") || sql.getSQLState().startsWith("57P"))) return true;
        }
        return exc instanceof org.springframework.jdbc.CannotGetJdbcConnectionException;
    }

    @RequestMapping(value = "/**", method = {RequestMethod.GET, RequestMethod.POST, RequestMethod.OPTIONS,
        RequestMethod.PUT, RequestMethod.DELETE, RequestMethod.PATCH, RequestMethod.HEAD})
    public void handle(HttpServletRequest request, HttpServletResponse response) throws Exception {
        response.setHeader("Access-Control-Allow-Origin", "*");
        if (request.getMethod().equals("OPTIONS")) {
            response.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
            response.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
            response.setHeader("Access-Control-Max-Age", "3600");
            response.setStatus(200);
            return;
        }
        String path = request.getRequestURI();
        Reply reply;
        try {
            byte[] raw = request.getInputStream().readAllBytes();
            Map<String, Object> data = obj();
            if (raw.length > 0) {
                if (contentType(request).contains("application/x-www-form-urlencoded")) {
                    for (String part : new String(raw, StandardCharsets.UTF_8).split("&")) {
                        String[] pair = part.split("=", 2);
                        if (pair.length == 2 && !pair[1].isEmpty()) data.put(decode(pair[0]), decode(pair[1]));
                    }
                } else data = mapper.readValue(raw, new TypeReference<Map<String, Object>>() {});
            }
            reply = dispatch(path, request, data);
        } catch (DataAccessException exc) {
            if (path.equals("/oauth/token")) reply = error(connectivity(exc) ? 503 : 500, "server_error",
                connectivity(exc) ? "Database connection failed during authentication" : "Database error during authentication");
            else {
                String code = switch (path) { case "/auth/register" -> "registration_failed"; case "/auth/login" -> "login_failed"; default -> "server_error"; };
                String context = switch (path) { case "/auth/register" -> "registration"; case "/auth/login" -> "login"; case "/auth/refresh-token" -> "token refresh"; case "/api/disconnect" -> "disconnect"; default -> "request"; };
                reply = error(500, code, "Database error occurred during " + context);
            }
        } catch (IllegalArgumentException | NullPointerException | IndexOutOfBoundsException | com.fasterxml.jackson.core.JacksonException exc) {
            reply = path.equals("/oauth/token") ? error(500, "server_error", "An error occurred while processing the token request") : new Reply(400, obj("message", "Bad request"));
        }
        response.setStatus(reply.status());
        response.setHeader("Content-Type", reply.body() instanceof String ? "text/html" : "application/json");
        response.getOutputStream().write(reply.body() instanceof String s ? s.getBytes(StandardCharsets.UTF_8) : mapper.writeValueAsBytes(reply.body()));
    }

    static String decode(String value) { return URLDecoder.decode(value, StandardCharsets.UTF_8); }
    static String contentType(HttpServletRequest request) { return request.getContentType() == null ? "" : request.getContentType(); }

    Reply dispatch(String path, HttpServletRequest req, Map<String, Object> data) throws Exception {
        if (path.equals("/health")) {
            boolean healthy;
            try { db.rows("Test DB Connection", obj()); healthy = true; }
            catch (DataAccessException exc) { healthy = false; }
            return new Reply(healthy ? 200 : 503, obj("status", healthy ? "healthy" : "unhealthy", "database", healthy ? "connected" : "disconnected", "timestamp", now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS")) + "Z"));
        }
        if (path.startsWith("/web/")) {
            String name = switch (path) { case "/web/", "/web/login" -> "login"; case "/web/register" -> "register"; default -> null; };
            return name == null ? new Reply(404, obj("error", "Page not found")) :
                new Reply(200, new ClassPathResource("web/" + name + ".html").getContentAsString(StandardCharsets.UTF_8));
        }
        String header = req.getHeader("Authorization") == null ? "" : req.getHeader("Authorization");
        if (List.of("/oauth/token", "/auth/register", "/auth/login", "/auth/refresh-token", "/api/disconnect").contains(path)) {
            if (!req.getMethod().equals("POST")) return new Reply(405, obj("message", "Method not allowed"));
            return path.equals("/oauth/token") ? oauth(data, header) : auth(path, data);
        }
        var match = EMPLOYEE.matcher(path);
        if (!match.matches()) return new Reply(404, obj("message", "Resource not found"));
        String endpoint = match.group(2);
        if (!req.getMethod().equals(endpoint.equals("pto/schedule") ? "POST" : "GET")) return new Reply(405, obj("message", "Method not allowed"));
        if (endpoint.equals("pto/schedule") && !contentType(req).contains("application/json")) return new Reply(415, obj("message", "Unsupported media type"));
        return employee(decode(match.group(1).replace("+", "%2B")), endpoint, data, header);
    }

    Reply authenticate(String header) {
        if (!header.startsWith("Bearer ")) return error(401, "missing_token", "Authorization header is missing or invalid");
        try {
            if (db.rows("Retrieve Token from DB", obj("token", header.substring(7), "currentTime", now())).isEmpty())
                return error(401, "invalid_token", "Invalid or expired access token");
        } catch (DataAccessException exc) { return error(401, "invalid_token", "Token validation failed"); }
        return null;
    }

    Reply oauth(Map<String, Object> data, String header) {
        Object client = data.get("client_id"), secret = data.get("client_secret");
        if (!header.isEmpty()) {
            String[] pair = new String(Base64.getDecoder().decode(header.substring(6)), StandardCharsets.UTF_8).split(":", -1);
            client = pair[0]; secret = pair[1];
        }
        if (db.rows("Validate Client Credentials", obj("clientId", client, "clientSecret", secret)).isEmpty())
            return error(401, "invalid_client", "Client authentication failed");
        String access = token("");
        Object url = header.isEmpty() ? data.get("callback_url") : null;
        db.update("Store Token in DB", obj("clientId", client, "clientSecret", secret, "accessToken", access, "expiresAt", now().plusHours(1), "callbackUrl", url));
        if (present(url)) {
            Object callbackClient = client;
            Thread thread = new Thread(() -> {
                try {
                    var request = HttpRequest.newBuilder(URI.create(url.toString())).timeout(java.time.Duration.ofSeconds(5))
                        .header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofByteArray(mapper.writeValueAsBytes(obj("token", access, "userId", callbackClient)))).build();
                    HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.discarding());
                } catch (Exception ignored) { }
            });
            thread.setDaemon(true);
            thread.start();
        }
        return new Reply(200, obj("access_token", access, "token_type", "Bearer", "expires_in", 3600, "scope", "read write"));
    }

    Reply auth(String path, Map<String, Object> d) {
        if (path.equals("/auth/register")) {
            if (!present(d.get("username")) || !present(d.get("password")) || !present(d.get("email")))
                return error(400, "missing_fields", "Username, password, and email are required");
            if (!db.rows("Check User Exists", obj("username", d.get("username"), "email", d.get("email"))).isEmpty())
                return error(409, "user_exists", "Username or email already exists");
            db.update("Insert New User", obj("username", d.get("username"), "email", d.get("email"), "firstName", d.getOrDefault("firstName", ""), "lastName", d.getOrDefault("lastName", ""), "passwordHash", hash(d.get("password"))));
            return new Reply(201, obj("message", "User created successfully", "username", d.get("username")));
        }
        if (path.equals("/auth/login")) {
            Object client = d.getOrDefault("clientId", d.getOrDefault("client_id", ""));
            if (!present(d.get("username")) || !present(d.get("password")) || !present(client))
                return error(400, "invalid_request", "Missing required fields: username, password, and clientId");
            var users = db.rows("Validate User Credentials", obj("username", d.get("username"), "passwordHash", hash(d.get("password"))));
            if (users.isEmpty()) return error(401, "invalid_credentials", "Invalid username or password");
            Object user = d.getOrDefault("userId", d.get("salesforce_user_id"));
            var clients = db.rows("Check Existing API Client", obj("userId", users.get(0).get("user_id")));
            if (!clients.isEmpty()) client = clients.get(0).get("client_id");
            else db.update("Create API Client", obj("clientId", client, "clientSecret", token(""), "userId", users.get(0).get("user_id"), "salesforceUserId", user));
            String access = token(""), refresh = token("refresh_");
            LocalDateTime expiry = now().plusHours(1);
            db.update("Update Token in DB", obj("clientId", client, "accessToken", access, "expiresAt", expiry, "tokenExpiresAt", expiry, "refreshToken", refresh, "refreshExpiresAt", now().plusDays(30), "salesforceUserId", user));
            return new Reply(200, obj("access_token", access, "refresh_token", refresh, "token_type", "Bearer", "expires_in", 3600, "user_id", user, "client_id", client, "scope", "read write"));
        }
        if (path.equals("/auth/refresh-token")) {
            if (!present(d.get("refresh_token"))) return error(400, "invalid_request", "Refresh token is required");
            var clients = db.rows("Validate Refresh Token", obj("refreshToken", d.get("refresh_token"), "currentTime", now()));
            if (clients.isEmpty()) return error(401, "invalid_grant", "Invalid or expired refresh token");
            String access = token(""), refresh = token("refresh_");
            db.update("Update Tokens", obj("clientId", clients.get(0).get("client_id"), "newAccessToken", access, "newRefreshToken", refresh, "tokenExpiresAt", now().plusHours(1), "refreshExpiresAt", now().plusDays(30)));
            return new Reply(200, obj("access_token", access, "refresh_token", refresh, "token_type", "Bearer", "expires_in", 3600));
        }
        Object user = d.getOrDefault("userId", d.getOrDefault("salesforce_user_id", ""));
        Object client = d.getOrDefault("clientId", d.getOrDefault("client_id", ""));
        if (!present(user) || !present(client)) return error(400, "invalid_request", "Missing required fields: userId and clientId");
        boolean changed = db.update("Deactivate User Connection", obj("salesforceUserId", user, "clientId", client)) != 0;
        return new Reply(changed ? 200 : 404, obj("status", changed ? "success" : "not_found", "userId", user, "clientId", client, "message", changed ? "API connection disconnected successfully" : "No active API connection found for this user", "timestamp", now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")) + "Z"));
    }

    Reply employee(String id, String endpoint, Map<String, Object> data, String header) {
        if (endpoint.equals("goals") || endpoint.equals("learning-status")) {
            Reply failure = authenticate(header);
            if (failure != null) return failure;
        }
        try {
            Map<String, Object> params = obj("employeeId", id);
            if (endpoint.equals("pto/schedule")) {
                Object date = data.get("endDate");
                params.put("endDate", new org.springframework.jdbc.core.SqlParameterValue(java.sql.Types.OTHER, date));
                db.update(QUERIES.get(endpoint), params);
                return new Reply(200, obj("employeeId", id, "startDate", data.get("startDate"), "endDate", date, "status", "success", "message", "PTO scheduled successfully"));
            }
            var rows = db.rows(QUERIES.get(endpoint), params);
            if (endpoint.equals("goals")) return new Reply(200, rows.isEmpty() ? obj("message", "No goals found for employee " + id) : rows.stream().map(r -> r.get("goal")).toList());
            if (rows.isEmpty()) return new Reply(404, obj("error", switch (endpoint) {
                case "learning-status" -> "Learning records not found"; case "next-pay-date" -> "Pay date not found"; default -> "Employee PTO record not found";
            }, "employeeId", id));
            Object value = switch (endpoint) {
                case "learning-status" -> rows;
                case "next-pay-date" -> rows.get(0).get("next_pay_date") == null ? null : rows.get(0).get("next_pay_date").toString();
                default -> rows.get(0).get("pto_balance") == null ? null : ((BigDecimal) rows.get(0).get("pto_balance")).doubleValue();
            };
            String field = switch (endpoint) { case "learning-status" -> "learningStatus"; case "next-pay-date" -> "nextPayDate"; default -> "ptoBalance"; };
            return new Reply(200, obj("employeeId", id, "status", "success", field, value));
        } catch (DataAccessException | IllegalArgumentException exc) {
            if (endpoint.equals("pto/schedule")) return new Reply(500, obj("error", "Failed to schedule PTO", "employeeId", id));
            if (endpoint.equals("goals") || endpoint.equals("pto/balance")) {
                boolean offline = exc instanceof DataAccessException dbError && connectivity(dbError);
                return new Reply(offline ? 503 : 500, obj("error", offline ? "Database connection failed" : "Database query failed", "employeeId", id, "details", offline ? "Unable to connect to database" : exc instanceof DataAccessException dbError ? dbError.getMostSpecificCause().getMessage() : exc.getMessage()));
            }
            return new Reply(500, obj("error", "Internal server error", "employeeId", id));
        }
    }
}
