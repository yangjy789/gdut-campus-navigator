import axios from 'axios'
export const adminHttp = axios.create({ baseURL: '/api/admin', timeout: 15000 })
let csrf = ''
adminHttp.interceptors.request.use(config => {
  config.headers.set('X-Admin-Request', '1')
  if (csrf) config.headers.set('X-CSRF-Token', csrf)
  return config
})
export function setCsrf(value: string) { csrf = value }
export async function whoAmI() { return (await adminHttp.get<{username: string; csrf_token: string}>('/auth/me')).data }
export async function loginAdmin(username: string, password: string) {
  return (await adminHttp.post<{username: string; csrf_token: string}>('/auth/login', {username, password})).data
}
