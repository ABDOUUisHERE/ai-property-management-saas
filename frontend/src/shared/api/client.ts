import { QueryClient } from '@tanstack/react-query';
import type { components } from '../../generated/api';

type Health = components['schemas']['Health'];
type Problem = components['schemas']['Problem'];

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly requestId: string | null = null,
  ) {
    super(code);
    this.name = 'ApiError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isProblem(value: unknown): value is Problem {
  return (
    isRecord(value) &&
    typeof value.code === 'string' &&
    typeof value.status === 'number' &&
    typeof value.request_id === 'string' &&
    typeof value.title === 'string' &&
    typeof value.detail === 'string' &&
    typeof value.type === 'string' &&
    typeof value.instance === 'string'
  );
}

export type RequestContext = Readonly<{ organizationId: string; signal?: AbortSignal }>;

export function tenantQueryKey(context: RequestContext, ...parts: readonly string[]) {
  return ['organization', context.organizationId, ...parts] as const;
}

export async function request<T>(
  path: string,
  validate: (body: unknown) => body is T,
  options: Readonly<{
    method?: 'GET' | 'POST';
    context?: RequestContext;
    signal?: AbortSignal;
  }> = {},
): Promise<T> {
  // Tenant selection is captured per call; the backend must still authorize it.
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Relative API path required');
  const headers = new Headers({ Accept: 'application/json' });
  if (options.context) headers.set('X-Organization-ID', options.context.organizationId);
  const callerSignal = options.signal ?? options.context?.signal;
  const timeout = AbortSignal.timeout(5000);
  const signal = callerSignal ? AbortSignal.any([callerSignal, timeout]) : timeout;
  const response = await fetch(path, {
    method: options.method ?? 'GET',
    credentials: 'same-origin',
    headers,
    signal,
  });
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(response.status, 'invalid_response');
  }
  if (!response.ok) {
    if (isProblem(body) && body.status === response.status) {
      throw new ApiError(response.status, body.code, body.request_id);
    }
    throw new ApiError(response.status, 'request_failed');
  }
  if (!validate(body)) throw new ApiError(response.status, 'invalid_response');
  return body;
}

export function getHealth(signal?: AbortSignal): Promise<Health> {
  return request(
    '/health/ready',
    (body): body is Health => isRecord(body) && body.status === 'ok',
    signal ? { signal } : {},
  );
}

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (count, error) => count < 1 && !(error instanceof ApiError && error.status < 500),
        staleTime: 15000,
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}

export async function clearOrganizationCache(client: QueryClient) {
  await client.cancelQueries({ queryKey: ['organization'] });
  client.removeQueries({ queryKey: ['organization'] });
}
