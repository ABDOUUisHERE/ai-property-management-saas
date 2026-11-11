import { describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  clearOrganizationCache,
  createQueryClient,
  getHealth,
  request,
  tenantQueryKey,
} from './client';

describe('API contracts', () => {
  it('rejects malformed successful responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'maybe' }))),
    );
    await expect(getHealth()).rejects.toMatchObject({ code: 'invalid_response' });
  });
  it('reports expiration without reflecting provider details', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            type: 'about:blank',
            title: 'Expired',
            detail: 'secret',
            instance: '/',
            status: 401,
            code: 'session_expired',
            request_id: 'trace-id',
          }),
          { status: 401 },
        ),
      ),
    );
    await expect(getHealth()).rejects.toEqual(new ApiError(401, 'session_expired', 'trace-id'));
  });
  it('passes cancellation and captured organization to fetch', async () => {
    const controller = new AbortController();
    const fetcher = vi.fn(
      (_url, options: RequestInit) =>
        new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          );
        }),
    );
    vi.stubGlobal('fetch', fetcher);
    const pending = request('/api/v1/example', (body): body is string => typeof body === 'string', {
      context: { organizationId: 'organization-a', signal: controller.signal },
    });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    expect(new Headers(fetcher.mock.calls[0]?.[1].headers).get('X-Organization-ID')).toBe(
      'organization-a',
    );
  });
  it('isolates keys and clears organization caches', async () => {
    const client = createQueryClient();
    const a = tenantQueryKey({ organizationId: 'a' }, 'properties');
    const b = tenantQueryKey({ organizationId: 'b' }, 'properties');
    expect(a).not.toEqual(b);
    client.setQueryData(a, ['private-a']);
    client.setQueryData(b, ['private-b']);
    await clearOrganizationCache(client);
    expect(client.getQueryData(a)).toBeUndefined();
    expect(client.getQueryData(b)).toBeUndefined();
    client.clear();
  });
  it('never retries a mutation automatically', async () => {
    const client = createQueryClient();
    const operation = vi.fn().mockRejectedValue(new ApiError(503, 'unavailable'));
    const mutation = client.getMutationCache().build(client, { mutationFn: operation });
    await expect(mutation.execute(undefined)).rejects.toThrow();
    expect(operation).toHaveBeenCalledTimes(1);
    client.clear();
  });
});
