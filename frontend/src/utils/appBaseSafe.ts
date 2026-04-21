/**
 * App base-path helpers
 *
 * VITE_APP_BASE  - router + Vite asset base (e.g. /zszngl/ for prod, / for local)
 * VITE_API_BASE  - axios baseURL prefix (e.g. /zszngl for prod, '' for local via proxy)
 */

function normalizeBase(value: string | undefined, fallback = '/'): string {
  const raw = (value || fallback).trim()
  if (!raw || raw === '/') return '/'
  return `/${raw.replace(/^\/+|\/+$/g, '')}/`
}

export function getRouterBase(): string {
  return normalizeBase(import.meta.env.VITE_APP_BASE, '/')
}

export function getApiBase(): string {
  const explicit = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (explicit !== undefined && explicit !== '') return explicit
  const base = getRouterBase()
  return base === '/' ? '' : base.replace(/\/$/, '')
}

export function buildSsoLoginUrl(next = '/dashboard'): string {
  const apiBase = getApiBase()
  return `${apiBase}/api/users/sso/login/?next=${encodeURIComponent(next)}`
}

const SSO_ERROR_MESSAGES: Record<string, string> = {
  disabled: '云南中烟单点登录当前未启用',
  origin_untrusted: '当前地址不是受信任来源，请改用 HTTPS 或 localhost 访问后再发起单点登录',
  state_invalid: '登录状态已失效，请重新发起单点登录',
  token_exchange_failed: '统一认证返回异常，请稍后重试',
  userinfo_failed: '未能获取统一认证用户信息',
  employee_id_missing: '统一认证未返回工号，无法完成登录',
  account_disabled: '本系统账号已被禁用，请联系管理员',
  code_missing: '统一认证未返回授权码，请重试',
}

export function getSsoErrorMessage(code: string | null): string | null {
  if (!code) return null
  return SSO_ERROR_MESSAGES[code] ?? `单点登录失败：${code}`
}
