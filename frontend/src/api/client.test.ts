import { describe, expect, it } from 'vitest';

import { ApiError, formatError, parseApiErrorBody } from './client';

describe('parseApiErrorBody', () => {
  it('extracts non_field_errors from DRF login failure', () => {
    expect(
      parseApiErrorBody({ non_field_errors: ['Invalid email or password.'] }),
    ).toBe('Invalid email or password.');
  });

  it('extracts detail string', () => {
    expect(parseApiErrorBody({ detail: 'Not found.' })).toBe('Not found.');
  });

  it('extracts field-level errors', () => {
    expect(parseApiErrorBody({ email: ['Enter a valid email address.'] })).toBe(
      'Email: Enter a valid email address.',
    );
  });

  it('parses JSON string bodies', () => {
    expect(parseApiErrorBody('{"non_field_errors":["Invalid email or password."]}')).toBe(
      'Invalid email or password.',
    );
  });
});

describe('formatError', () => {
  it('formats ApiError with DRF body', () => {
    const err = new ApiError('raw', 400, { non_field_errors: ['Invalid email or password.'] });
    expect(formatError(err)).toBe('Invalid email or password.');
  });

  it('falls back for unknown errors', () => {
    expect(formatError(null, 'Login failed')).toBe('Login failed');
  });
});
