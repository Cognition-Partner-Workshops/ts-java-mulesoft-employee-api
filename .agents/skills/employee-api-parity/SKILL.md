---
name: employee-api-parity
description: Compare employee API status codes and JSON contracts between a local legacy stand-in and a replacement service.
---

# Employee API parity

1. Start the local baseline: `docker compose -f legacy-standin/compose.yaml up -d --build --wait`.
   Start the Java 17 / Spring Boot 3 replacement in `employee-api-spring/`: `docker compose -f employee-api-spring/compose.yaml up -d --build --wait`. It owns a separate PostgreSQL 15 and publishes port 8083; `cd employee-api-spring && mvn -q verify` runs JUnit contracts with Testcontainers.
2. Exercise all five endpoints: `legacy-standin/smoke.sh http://localhost:8082`.
3. Compare two URLs: `python3 tools/parity/compare.py http://localhost:8082 http://localhost:8083 --output /path/to/report.md`.
4. Read the Markdown table: each seeded employee and endpoint must MATCH on HTTP status and normalized JSON. The process exits 1 on any mismatch or transport/authentication failure. Object key order/whitespace are ignored; arrays, nulls, numbers, messages and dates remain significant.
5. Use `--employees EMP001 EMP002 EMP003` to specify fixture employees. `OLD_CLIENT_ID`, `OLD_CLIENT_SECRET`, `NEW_CLIENT_ID`, `NEW_CLIENT_SECRET` override the local synthetic client credentials. Never put live credentials in reports or source.
6. Use `--endpoints goals learning-status` to filter the five routes. Default remains all five; pto/schedule is always last, even if listed first.
7. Run `python3 tools/parity/contract_cases.py http://localhost:8082 http://localhost:8083 --output /path/to/contract-parity.md` for non-employee and edge contracts, static HTML, Content-Type and CORS. It exits 1 on mismatch or failure. Only shape-validated tokens, timestamps and generated username echoes are masked; the report lists exact fields. This script also mutates users/tokens and schedules ABSENT after its missing GETs.

Self-check today: `python3 tools/parity/compare.py http://localhost:8082 http://localhost:8082 --output /path/to/self-check.md` must show 15/15 matches. This validates the comparison mechanics, not equivalence with a live Mule runtime.

The script POSTs the fixed PTO schedule last for each employee; it changes next_pay_date to 2024-02-09 on both sides. Compare disposable fixture databases, not production. Do not reset a shared database without approval. A same-URL comparison obtains each token immediately before use because issuing another token for the same client replaces the previous token.

Routes come from the RAML: `/api/employee/{employeeId}/...`, not the shorter README examples. Source XML applies bearer validation only to goals and learning-status; next-pay-date, PTO balance/schedule and disconnect have no token-validation call. Preserve that baseline for parity, and raise security changes separately. Empty goals return HTTP 200 with a message; other missing employee GETs return 404. Scheduling updates next_pay_date, not PTO balance, and ignores startDate in SQL.

The stand-in executes SQL extracted directly from `src/main/mule/employee-services-api.xml`; schema/seed corrections live only in `legacy-standin/seed.sql`. EMP001 uses the README's sample goal/course/balance; EMP002 adds a zero-balance/null-pay-date case; EMP003 has PTO but no goals or learning records. The stand-in translates declared httpStatus values and DataWeave response shapes; it does not emulate Mule connector exception descriptions, APIKit parser internals, HTTP attribute replacement, or listener default-status quirks. Validate these against a licensed Mule runtime before claiming wire-level Mule equivalence. Static login/register HTML is served unchanged.
