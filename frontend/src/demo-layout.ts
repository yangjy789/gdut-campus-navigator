// 人工排布的平面示意坐标（y、x），不是经纬度，也不代表实际建筑位置。
export const demoLayout: Record<string, [number, number]> = {
  NG: [600, 180], LIB: [600, 440], ADM: [600, 700], LAK: [600, 960],
  TA: [370, 180], LAB: [370, 440], SP: [370, 700], SC: [370, 960],
  TB: [120, 180], DIN: [120, 440], DOR: [120, 700], SG: [120, 960],
}
export const labels: Record<string, string> = { NG: '北门', LIB: '图书馆', TA: '教学楼 A', TB: '教学楼 B', LAB: '实验楼', SC: '学生活动中心', DIN: '食堂', DOR: '宿舍区', SP: '运动场', ADM: '行政楼', SG: '南门', LAK: '湖畔花园' }
export const categories: Record<string, string> = { NG: '出入口', SG: '出入口', LIB: '学习', TA: '学习', TB: '学习', LAB: '学习', SC: '生活', DIN: '生活', DOR: '生活', SP: '休闲', LAK: '休闲', ADM: '服务' }

const originalNames: Record<string,string> = { NG:'NorthGate', LIB:'Library', TA:'TeachingA', TB:'TeachingB', LAB:'LabBuilding', SC:'StudentCenter', DIN:'DiningHall', DOR:'Dormitory', SP:'SportsField', ADM:'Administration', SG:'SouthGate', LAK:'LakeGarden' }
export function displayName(place: {code:string;name:string}) {
  // 管理员改名后显示新名称；仅原始英文示例名称使用中文别名。
  return originalNames[place.code] === place.name ? labels[place.code] ?? place.name : place.name
}
