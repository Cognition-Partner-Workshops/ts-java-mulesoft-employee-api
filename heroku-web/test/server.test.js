const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { spawn } = require('node:child_process');

const PORT = 3999;
const BASE = `http://127.0.0.1:${PORT}`;

let server;

async function waitForServer(timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        try {
            const res = await fetch(`${BASE}/health`);
            if (res.ok) return;
        } catch (err) {
            // server not up yet
        }
        await new Promise((resolve) => setTimeout(resolve, 200));
    }
    throw new Error('server did not start in time');
}

test.before(async () => {
    server = spawn(process.execPath, [path.join(__dirname, '..', 'server.js')], {
        env: { ...process.env, PORT: String(PORT) },
        stdio: 'ignore'
    });
    await waitForServer();
});

test.after(() => {
    if (server) server.kill();
});

test('health endpoint reports healthy', async () => {
    const res = await fetch(`${BASE}/health`);
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.status, 'healthy');
});

test('login page renders', async () => {
    const res = await fetch(`${BASE}/`);
    assert.strictEqual(res.status, 200);
    const html = await res.text();
    assert.match(html, /<form/i);
});

test('registration page renders', async () => {
    const res = await fetch(`${BASE}/register`);
    assert.strictEqual(res.status, 200);
    assert.match(await res.text(), /<form/i);
});

test('authenticate rejects missing credentials', async () => {
    const res = await fetch(`${BASE}/authenticate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    assert.ok(res.status >= 400, `expected an error status, got ${res.status}`);
});
