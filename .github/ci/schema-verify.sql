-- Fails (non-zero psql exit) if database-setup.sql did not produce the
-- expected objects. Uses ON_ERROR_STOP, set by the workflow.

DO $$
DECLARE
    missing text;
BEGIN
    SELECT string_agg(t, ', ') INTO missing
    FROM unnest(ARRAY['users', 'api_clients', 'employee_goals', 'employee_learning', 'employee_pto']) AS t
    WHERE to_regclass('public.' || t) IS NULL;

    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'missing tables: %', missing;
    END IF;

    SELECT string_agg(c, ', ') INTO missing
    FROM unnest(ARRAY['user_id', 'access_token', 'refresh_token', 'callback_url',
                      'salesforce_user_id', 'token_expires_at', 'is_active']) AS c
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'api_clients' AND column_name = c
    );

    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'api_clients is missing columns: %', missing;
    END IF;

    IF to_regclass('public.idx_api_clients_salesforce_user_id') IS NULL THEN
        RAISE EXCEPTION 'missing index idx_api_clients_salesforce_user_id';
    END IF;
END
$$;

-- Smoke-test the updated_at trigger created by database-setup.sql.
INSERT INTO api_clients (client_id, client_secret, client_name, is_active)
VALUES ('ci_client', 'ci_secret', 'CI Smoke Test', TRUE);

UPDATE api_clients SET client_name = 'CI Smoke Test (updated)' WHERE client_id = 'ci_client';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM api_clients WHERE client_id = 'ci_client' AND updated_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'update_api_clients_updated_at trigger did not set updated_at';
    END IF;
END
$$;
