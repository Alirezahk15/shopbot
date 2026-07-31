// ── Panel auth helpers: current admin info + section permissions ──

export function getAdminInfo() {
  try {
    return JSON.parse(localStorage.getItem('admin_info') || 'null')
  } catch {
    return null
  }
}

export function setAdminInfo(info) {
  if (info) localStorage.setItem('admin_info', JSON.stringify(info))
  else localStorage.removeItem('admin_info')
}

export function clearAuth() {
  localStorage.removeItem('token')
  localStorage.removeItem('admin_info')
}

// Permission key required for each panel route (mirrors the API's PERM_MAP).
// Routes not listed here are open to every logged-in admin.
export const PATH_PERMS = {
  '/users': 'users',
  '/admins': '__super__',
  '/products': 'products',
  '/orders': 'products',
  '/discounts': 'discounts',
  '/payments': 'payments',
  '/methods': 'payments',
  '/tickets': 'tickets',
  '/warranty': 'warranty',
  '/lock': 'settings',
  '/broadcast': 'broadcast',
  '/settings': 'settings',
  '/buttons': 'settings',
  '/bot-texts': 'settings',
  '/menu-builder': 'settings',
}

export function hasPerm(perm) {
  if (!perm) return true
  const a = getAdminInfo()
  if (!a) return true // legacy session (old token without admin info)
  if (a.is_super || a.perms === 'all') return true
  if (perm === '__super__') return false
  return String(a.perms || '')
    .split(',')
    .map((s) => s.trim())
    .includes(perm)
}

export function pathAllowed(path) {
  return hasPerm(PATH_PERMS[path])
}
