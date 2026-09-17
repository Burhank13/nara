export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: Record<string, unknown>

  constructor(status: number, detail: Record<string, unknown>) {
    const message =
      typeof detail.message === 'string' ? detail.message : 'Something went wrong. Try again.'
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = typeof detail.code === 'string' ? detail.code : 'unknown_error'
    this.detail = detail
  }
}

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

type RequestOptions = {
  method?: string
  body?: unknown
  /** Set for the refresh call itself, so a failed refresh can't recurse. */
  skipRefresh?: boolean
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: Record<string, unknown> = {}
  try {
    const body = await response.json()
    // FastAPI wraps our structured errors in `detail`; validation errors put a list there instead.
    if (body && typeof body.detail === 'object' && !Array.isArray(body.detail)) {
      detail = body.detail
    } else if (Array.isArray(body?.detail)) {
      detail = { code: 'invalid_request', message: 'Check the details and try again.' }
    }
  } catch {
    detail = {}
  }
  return new ApiError(response.status, detail)
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, skipRefresh = false } = options

  const send = (): Promise<Response> =>
    fetch(path, {
      method,
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
    })

  let response = await send()

  // An expired access token is renewed once from the refresh cookie, then the call is retried.
  if (response.status === 401 && !skipRefresh && accessToken) {
    const renewed = await renewSession()
    if (renewed) response = await send()
  }

  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export type Session = {
  access_token: string
  user: {
    id: string
    email: string
    full_name: string
    role: 'owner' | 'manager' | 'employee'
    status: string
  }
  business: {
    id: string
    name: string
    timezone: string
    status: string
    trial_ends_at: string | null
    seat_limit: number
  }
}

export async function renewSession(): Promise<Session | null> {
  try {
    const session = await request<Session>('/auth/refresh', { method: 'POST', skipRefresh: true })
    setAccessToken(session.access_token)
    return session
  } catch {
    setAccessToken(null)
    return null
  }
}
