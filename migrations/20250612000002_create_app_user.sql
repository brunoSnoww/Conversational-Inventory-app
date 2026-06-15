-- +goose Up
-- Standalone user table (before Django). Django later: AUTH_USER_MODEL pointing here.

CREATE SEQUENCE app_user_id_seq MINVALUE 0 MAXVALUE 2048 CYCLE;

CREATE TABLE app_user (
    user_id BIGINT PRIMARY KEY
        CHECK (user_id > 0)
        DEFAULT gen_random_with_timestamp_id('app_user_id_seq'),
    email TEXT NOT NULL
        CHECK (char_length(email) BETWEEN 3 AND 320
               AND email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    password_hash TEXT NOT NULL
        CHECK (char_length(password_hash) >= 1),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX app_user_email_lower_unique ON app_user (lower(email));

CREATE TRIGGER app_user_updated_at_trigger
    BEFORE UPDATE ON app_user
    FOR EACH ROW EXECUTE PROCEDURE updated_at_trigger_function();

-- +goose Down
DROP TRIGGER IF EXISTS app_user_updated_at_trigger ON app_user;
DROP INDEX IF EXISTS app_user_email_lower_unique;
DROP TABLE IF EXISTS app_user;
DROP SEQUENCE IF EXISTS app_user_id_seq;
