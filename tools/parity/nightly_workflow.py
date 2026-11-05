"""Nightly employee API parity: MuleSoft stand-in vs Spring Boot, one worker per endpoint."""
import asyncio
import datetime
import json
import os
from pathlib import Path

REPO = "Cognition-Partner-Workshops/ts-java-mulesoft-employee-api"
# Branch holding legacy-standin/ and employee-api-spring/. Override with EMPLOYEE_PARITY_REF.
REF = os.environ.get("EMPLOYEE_PARITY_REF", "devin/1793850388-spring-boot-employee-api")
OUT_DIR = Path(os.environ.get("EMPLOYEE_PARITY_OUT", str(Path.home() / "parity")))

SETUP = f"""Repository: https://github.com/{REPO} . Clone it (or use the existing checkout), `git fetch origin` and
`git checkout --detach origin/{REF}`. Report the commit SHA you tested.
Start two DISPOSABLE fixture stacks from a fresh seed (they are local docker compose fixtures, never a shared/prod DB):
  docker compose -f legacy-standin/compose.yaml down -v; docker compose -f legacy-standin/compose.yaml up -d --build --wait
  docker compose -f employee-api-spring/compose.yaml down -v; docker compose -f employee-api-spring/compose.yaml up -d --build --wait
Old path (Mule stand-in) = http://localhost:8082, new path (Spring Boot) = http://localhost:8083.
Read .agents/skills/employee-api-parity/SKILL.md first; it explains the comparator and the baseline quirks.
Do NOT edit any source file, do NOT push, do NOT open PRs. Report honestly: a failed check stays failed."""

DISCOVERY_SCHEMA = {"type": "object", "properties": {
    "commit": {"type": "string"},
    "endpoints_json": {"type": "string", "description": "JSON array of {endpoint, method, path, reason}"},
    "employees_json": {"type": "string", "description": "JSON array of {id, reason}"},
}, "required": ["commit", "endpoints_json", "employees_json"]}

WORKER_SCHEMA = {"type": "object", "properties": {
    "commit": {"type": "string"},
    "rows_json": {"type": "string", "description": "JSON array of {employee, old_status, new_status, result, old_body, new_body}"},
    "report_markdown": {"type": "string"},
    "notes": {"type": "string"},
}, "required": ["commit", "rows_json", "report_markdown"]}

CHECK_SCHEMA = {"type": "object", "properties": {
    "tables_identical": {"type": "boolean"},
    "token_flow_ok": {"type": "boolean"},
    "verdicts_json": {"type": "string", "description": "JSON array of {employee, verdict, reason}; verdict is CONFIRMED_DRIFT, FIXTURE_STATE, TOKEN_FLOW or NOT_REPRODUCED"},
    "evidence": {"type": "string"},
}, "required": ["tables_identical", "token_flow_ok", "verdicts_json", "evidence"]}


async def discover():
    return await agent(
        SETUP.split("Start two")[0] + """
Task: DISCOVER the nightly parity inventory; you do not need to start any stack.
1. Endpoints: read the API specification src/main/resources/api/employee-services-api.raml. List every
   method+resource under /employee/{employeeId} (baseUri /api). For each give `endpoint` exactly as accepted by
   `python3 tools/parity/compare.py --endpoints` (check its ENDPOINTS list, e.g. goals, pto/balance), `method`,
   full `path` (/api/employee/{employeeId}/...), and `reason` citing the RAML line it came from. If the RAML has a
   resource compare.py cannot exercise, include it with endpoint "UNSUPPORTED:<path>" and say why.
2. Employees: read legacy-standin/seed.sql and list every distinct employee_id inserted into employee_goals,
   employee_learning or employee_pto, with `reason` naming the tables/rows that seed it (e.g. "pto 0.00, null pay date").
Return both lists as JSON strings (json.dumps of arrays).""",
        phase="discover", label="discover-endpoints", schema=DISCOVERY_SCHEMA, soft_time_limit_minutes=10)


def worker_prompt(ep, employees):
    ids = " ".join(e["id"] for e in employees)
    return SETUP + f"""

Task: parity WORKER for endpoint `{ep['endpoint']}` ({ep['method']} {ep['path']}) only.
Run: python3 tools/parity/compare.py http://localhost:8082 http://localhost:8083 --endpoints {ep['endpoint']} \\
     --employees {ids} --output /tmp/parity-{ep['endpoint'].replace('/', '-')}.md
Keep its exit code and table. Then, for EVERY employee row, capture the raw status and JSON body from both sides
yourself (same request the comparator makes: fresh token from POST /oauth/token with demo_client/demo_secret
immediately before each call; POST body {{"startDate":"2024-02-05","endDate":"2024-02-09"}} for pto/schedule —
recreate both stacks with down -v/up before re-sending a POST so each side gets it once on a fresh seed).
Return rows_json = json.dumps of [{{"employee","old_status","new_status","result" ("MATCH"/"MISMATCH" exactly as the
comparator reported),"old_body","new_body"}}], report_markdown = the comparator table, notes = anything abnormal
(build failures, transport errors). If a stack does not start, return result "MISMATCH" with the error in notes."""


def check_prompt(ep, employees, work):
    return SETUP + f"""

Task: parity CHECKER for endpoint `{ep['endpoint']}` ({ep['method']} {ep['path']}).
The worker's results (JSON, from a separate machine on commit {work.get('commit')}):
{work['rows_json']}
Worker notes: {work.get('notes', '')}
1. Shared tables: on both fresh stacks run, via `docker compose -f <compose> exec -T db psql -U fixture -d employee_service`,
   SELECT * FROM employee_goals, employee_learning, employee_pto ORDER BY 1,2 and SELECT client_id, client_secret,
   is_active FROM api_clients. tables_identical = both sides hold identical rows (before any POST).
2. Token flow on BOTH sides: POST /oauth/token (JSON demo_client/demo_secret) -> 200 with expires_in 3600; GET
   /api/employee/EMP001/goals with that token -> 200; issue a second token, the first must now give 401
   invalid_token; no Authorization -> 401 missing_token; also run
   `python3 tools/parity/contract_cases.py http://localhost:8082 http://localhost:8083` and record its summary line.
   token_flow_ok = the token steps above plus the token/auth rows of contract_cases.py (goals/learning-status token
   cases, oauth, login, refresh) behave identically on both sides. List any other contract_cases mismatch in evidence
   without failing token_flow_ok: it belongs to the endpoint worker that owns it.
3. For each MISMATCH row, re-issue that request against both sides and classify: CONFIRMED_DRIFT (tables identical,
   token flow ok, difference reproduces — quote the differing field), FIXTURE_STATE (seed/table rows differ),
   TOKEN_FLOW (difference caused by token issuance/validation), NOT_REPRODUCED. If there are no mismatches return [].
Return verdicts_json = json.dumps of [{{"employee","verdict","reason"}}] and evidence = the psql/contract outputs, trimmed."""


async def main():
    await register_workflow({
        "name": "employee-api-nightly-parity",
        "description": f"Mule stand-in (8082) vs Spring Boot (8083) on {REPO}@{REF}: per-endpoint workers, per-worker checker, one table.",
        "soft_time_limit_minutes": 30,
        "phases": [
            {"title": "discover", "detail": "endpoints from the RAML spec, employees from seed.sql", "count": 1, "soft_time_limit_minutes": 10},
            {"title": "compare", "detail": "one worker per endpoint runs every seeded employee on both paths"},
            {"title": "check", "detail": "verify each worker's mismatches against shared tables and the token flow"},
        ],
    })
    found = await discover()
    endpoints = json.loads(found["endpoints_json"])
    employees = json.loads(found["employees_json"])
    log(f"Discovered {len(endpoints)} endpoints at {found['commit']}: " +
        "; ".join(f"{e['endpoint']} ({e['reason']})" for e in endpoints))
    log(f"Seeded employees {len(employees)}: " + "; ".join(f"{e['id']} ({e['reason']})" for e in employees))

    async def compare_stage(ep):
        if ep["endpoint"].startswith("UNSUPPORTED"):
            return ep, None, "UNSUPPORTED"
        try:
            work = await agent(worker_prompt(ep, employees), phase="compare",
                               label=f"compare {ep['endpoint']}", schema=WORKER_SCHEMA)
            log(f"{ep['endpoint']}: worker done")
            return ep, work, None
        except WorkflowAgentError as exc:
            return ep, None, f"WORKER FAILED: {exc}"

    async def check_stage(prev):
        ep, work, err = prev
        if err:
            return ep, work, None, err
        try:
            chk = await agent(check_prompt(ep, employees, work), phase="check",
                              label=f"check {ep['endpoint']}", schema=CHECK_SCHEMA, soft_time_limit_minutes=25)
            return ep, work, chk, None
        except WorkflowAgentError as exc:
            return ep, work, None, f"CHECK FAILED: {exc}"

    results = await pipeline(endpoints, compare_stage, check_stage)

    lines = ["| Endpoint | Employee | Old HTTP | New HTTP | Worker | Checker | Tables identical | Token flow |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    total = matched = 0
    details = []
    for ep, work, chk, err in results:
        verdicts = {v["employee"]: v for v in json.loads(chk["verdicts_json"])} if chk else {}
        rows = json.loads(work["rows_json"]) if work else []
        if not rows:
            total += 1
            lines.append(f"| {ep['endpoint']} | all | - | - | FAILED | {err or 'no rows'} | - | - |")
            continue
        for r in rows:
            total += 1
            ok = r["result"] == "MATCH" and chk is not None and chk["tables_identical"] and chk["token_flow_ok"]
            matched += ok
            v = verdicts.get(r["employee"])
            checker = err or (v["verdict"] if v else ("OK" if ok else "FAILED"))
            lines.append(f"| {ep['endpoint']} | {r['employee']} | {r['old_status']} | {r['new_status']} | "
                         f"{r['result']} | {checker} | {chk['tables_identical'] if chk else '-'} | "
                         f"{chk['token_flow_ok'] if chk else '-'} |")
            if r["result"] != "MATCH":
                details.append(f"- {ep['endpoint']} {r['employee']}: old {json.dumps(r['old_body'], sort_keys=True)} "
                               f"new {json.dumps(r['new_body'], sort_keys=True)}"
                               + (f" — {v['reason']}" if v else ""))
    status = "GREEN" if matched == total else "RED"
    summary = f"{status}: {matched}/{total} rows match on {REF}@{found['commit']}."
    report = "\n".join(lines + ["", summary] + (["", "Mismatches:"] + details if details else []))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"nightly-parity-{datetime.date.today().isoformat()}-{REF.replace('/', '_')}.md"
    out.write_text(report + "\n")
    log(f"Report written to {out}\n{report}")
    if status == "RED":
        raise RuntimeError(summary)

asyncio.run(main())
