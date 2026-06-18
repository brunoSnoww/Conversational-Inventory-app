import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import { createPowerSyncFetch } from './powersync-fetch';

const NGROK = 'https://canine-scrambled-reseller.ngrok-free.dev';

vi.mock('../api/base-url', () => ({
  getApiBaseUrl: () => NGROK,
}));

describe('createPowerSyncFetch', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockClear();
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('rewrites ngrok write-checkpoint to Django proxy', async () => {
    const psFetch = createPowerSyncFetch();
    await psFetch(
      'https://canine-scrambled-reseller.ngrok-free.dev/write-checkpoint2.json?client_id=abc-123',
      {
        headers: {
          Authorization: 'Token ps-jwt',
          'x-user-agent': 'powersync-js/1.0',
        },
      },
    );

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${NGROK}/api/sync/write-checkpoint/?client_id=abc-123`);
    expect(new Headers(init.headers).get('Authorization')).toBe('Token ps-jwt');
    expect(new Headers(init.headers).get('x-user-agent')).toBeNull();
    expect(new Headers(init.headers).get('ngrok-skip-browser-warning')).toBe('true');
  });

  it('leaves localhost PowerSync URLs unchanged', async () => {
    const psFetch = createPowerSyncFetch();
    const target = 'http://localhost:2000/write-checkpoint2.json?client_id=local';
    await psFetch(target);

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]?.[0]).toBe(target);
  });
});
