import axios from 'axios'

export interface Place { id: number; code: string; name: string; description: string; latitude: number | null; longitude: number | null; verification_status: 'demo_only' }
export interface Road { id: number; start_id: number; end_id: number; distance_m: number; bidirectional: boolean }
export interface Route { distance_m: number; path: Place[]; segments: { road_id: number; start_id: number; end_id: number; distance_m: number }[]; real_navigation_ready: boolean }
const http = axios.create({ baseURL: '/api', timeout: 10000 })
export const fetchPlaces = () => http.get<{ items: Place[] }>('/places').then(r => r.data.items)
export const fetchRoads = () => http.get<{ items: Road[] }>('/roads').then(r => r.data.items)
export const fetchRoute = (start: number, end: number) => http.get<Route>('/routes/shortest', { params: { start, end } }).then(r => r.data)
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) return '输入数据不符合要求，请检查编号、名称、道路端点与坐标。'
    return typeof detail === 'string' ? detail : '连接暂时中断，请稍后重试。'
  }
  return '加载失败，请重试。'
}
