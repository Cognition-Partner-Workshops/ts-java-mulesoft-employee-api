# Employee API — Spring Boot

Java 17 / Spring Boot 3.5.7 translation of `legacy-standin/app.py`, not a claim of licensed Mule runtime equivalence.

## Run and test

From the repository root:

```sh
docker compose -f employee-api-spring/compose.yaml up -d --build --wait
cd employee-api-spring
mvn -q verify
```

Compose uses project `mc1105-employee-spring`, its own PostgreSQL 15, and exposes only `127.0.0.1:8083`. The multi-stage image builds the jar with Maven 3.9.9. Local tests start a disposable Testcontainers PostgreSQL 15 and load `../legacy-standin/seed.sql`; Docker must be available. Maven 3.9.x and Java 17 are needed locally. Maven Central's Google mirror is configured in the build image; if Central rate-limits local Maven, set a `central` mirror to `https://maven-central.storage-download.googleapis.com/maven2/` in `~/.m2/settings.xml`.

For a standalone jar, run `mvn package`, then `DATABASE_URL=jdbc:postgresql://localhost:5432/employee_service DB_USER=fixture DB_PASSWORD=fixture_only java -jar target/employee-api-1.0.0.jar`. Default HTTP port is 8080 (`SERVER_PORT` overrides it). Static HTML is copied unchanged from `../src/main/resources/web`.

## Parity

```sh
python3 tools/parity/compare.py http://localhost:8082 http://localhost:8083 --output /home/ubuntu/parity/employee-parity.md
python3 tools/parity/compare.py http://localhost:8082 http://localhost:8083 --endpoints goals learning-status --output /home/ubuntu/parity/read-parity.md
python3 tools/parity/contract_cases.py http://localhost:8082 http://localhost:8083 --output /home/ubuntu/parity/contract-parity.md
```

Run these from the repository root against disposable seeded stacks. The scripts mutate tokens, users, and PTO. Reset with `docker compose -f <compose-file> down -v` and `up -d --build --wait` for each stack when a pristine fixture is needed.

`queries.json` contains every SQL statement extracted verbatim (including whitespace) from `src/main/mule/employee-services-api.xml`, with the same named parameters. JDBC lets PostgreSQL infer schedule endDate as a date (including its validation), and binds other dates as UTC local timestamps. NUMERIC balances serialize as floating-point JSON; null pay dates remain null.

Baseline security quirks are intentional: only goals/learning-status validate bearer tokens; tokens and passwords retain the fixture format/encoding, not production-grade password hashing; schedule ignores startDate and changes next_pay_date; disconnect only sets is_active. Do not use this parity fixture as a hardened production auth service.

## Known non-parity / boundaries

* JSON formatting/key order, HTTP server identification, Date, framing and connection-management headers differ. Comparators check normalized JSON, status and (in contract_cases) Content-Type plus CORS, not raw transport bytes.
* JDBC/PostgreSQL exception text in database query error `details` differs from psycopg/Mule. It is emitted honestly rather than fabricated; connection failures and error codes/bodies otherwise preserve the stand-in mapping.
* Generated UUIDs/timestamps differ. contract_cases validates shapes and masks only access_token, refresh_token, timestamp, and generated fixture username echoes in username/user_id/userId/client_id/clientId. Expiries remain unmasked. Tests check actual DB expiry intervals and expired-token rejection.
* The stand-in only implements GET, POST, OPTIONS; its HTTP server returns its own HTML 501 for other verbs. This Spring service routes other verbs through its JSON 405/404 handling. Servlet-level invalid HTTP/URI/oversized-request rejection is container-specific.
* Callback delivery is asynchronous, best effort, with a five-second HTTP timeout, as in the fixture. JUnit verifies a real local callback; the cross-service script does not depend on an external callback receiver.
* No browser visual check was performed; HTML bytes are checked unchanged by JUnit and the cross-service contract script.
