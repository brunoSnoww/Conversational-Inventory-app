-- +goose Up
-- +goose StatementBegin
-- Timestamp-embedded BIGINT IDs.
-- See postgrespatterns.md: time filter via PK index, no separate created_at index needed.
--
-- Layout (64 bits):
--   high 52 bits = microsecond timestamp (shifted << 11)
--   next 0-11 bits = per-table sequence (collision safety in bulk insert)
--   low bits = random (non-enumerable IDs)

CREATE FUNCTION generate_id_for_timestamp(input_timestamp TIMESTAMP WITH TIME ZONE) RETURNS BIGINT AS $$
DECLARE
    timestamp_part BIGINT;
BEGIN
    IF input_timestamp IS NULL THEN
        RETURN NULL;
    END IF;

    timestamp_part := (
        1000000 * (
            extract(epoch from input_timestamp - '1000000000 seconds'::interval)::numeric(20, 6)
            + 1000000000
        )
    )::bigint;
    RETURN timestamp_part << 11;
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- clock_timestamp() not NOW(): same-transaction inserts get distinct timestamp parts.
CREATE FUNCTION gen_random_with_timestamp_id(sequence_name TEXT, sequence_bits INT DEFAULT 4) RETURNS BIGINT AS $$
DECLARE
    id BIGINT;
    timestamp_part BIGINT;
    sequence_part BIGINT;
    random_bits INT;
    random_part BIGINT;
BEGIN
    IF sequence_bits < 0 OR sequence_bits > 11 THEN
        RAISE EXCEPTION 'sequence_bits must be between 0 and 11, got %', sequence_bits;
    END IF;

    random_bits := 11 - sequence_bits;
    random_part := ((1 << random_bits) * RANDOM())::INT & ((1 << random_bits) - 1);
    sequence_part := (nextval(sequence_name) % (1 << sequence_bits)) << random_bits;
    timestamp_part := generate_id_for_timestamp(clock_timestamp());
    id := timestamp_part | sequence_part | random_part;
    RETURN id;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE FUNCTION updated_at_trigger_function() RETURNS trigger
    LANGUAGE plpgsql AS
$$BEGIN
    NEW.updated_at := current_timestamp;
    RETURN NEW;
END;$$;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP FUNCTION IF EXISTS updated_at_trigger_function();
DROP FUNCTION IF EXISTS gen_random_with_timestamp_id(TEXT, INT);
DROP FUNCTION IF EXISTS generate_id_for_timestamp(TIMESTAMP WITH TIME ZONE);
-- +goose StatementEnd
