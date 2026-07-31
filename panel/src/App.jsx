import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Users from './pages/Users.jsx'
import Products from './pages/Products.jsx'
import Orders from './pages/Orders.jsx'
import Payments from './pages/Payments.jsx'
import Tickets from './pages/Tickets.jsx'
import Discounts from './pages/Discounts.jsx'
import Warranty from './pages/Warranty.jsx'
import Lock from './pages/Lock.jsx'
import Admins from './pages/Admins.jsx'
import Methods from './pages/Methods.jsx'
import Broadcast from './pages/Broadcast.jsx'
import Settings from './pages/Settings.jsx'
import ButtonLayout from './pages/ButtonLayout.jsx'
import Appearance from './pages/Appearance.jsx'
import BotTexts from './pages/BotTexts.jsx'
import MenuBuilder from './pages/MenuBuilder.jsx'
import ApiDocs from './pages/ApiDocs.jsx'
import { pathAllowed } from './auth.js'

function PrivateRoute({ children, path }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  // Admins only see sections their permissions allow
  if (path && !pathAllowed(path)) return <Navigate to="/" replace />
  return children
}

function Layout({ children }) {
  return (
    <div className="relative" style={{ background: 'var(--bg, #0f0f1a)', height: '100vh', overflow: 'hidden' }}>
      {/* Ambient glow blobs (Cursor-inspired) */}
      <div className="ambient-glow" style={{ width: '420px', height: '420px', top: '-120px', insetInlineStart: '15%', background: 'var(--primary)' }} />
      <div className="ambient-glow" style={{ width: '360px', height: '360px', bottom: '-100px', insetInlineEnd: '10%', background: 'var(--accent)', animationDelay: '3s' }} />
      {/* Sidebar is position:fixed (see Sidebar.jsx) so it never scrolls away or
          detaches -- main is offset by its live width via --sidebar-width and
          scrolls independently in its own box. */}
      <Sidebar />
      <main
        className="overflow-auto relative transition-all duration-300"
        style={{ marginInlineStart: 'var(--sidebar-width, 220px)', height: '100vh' }}
      >
        {/* Top gradient line */}
        <div
          className="h-px w-full"
          style={{ background: 'linear-gradient(90deg, transparent, var(--primary-30, rgba(99,102,241,0.30)), transparent)' }}
        />
        <div className="p-6 max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}

const pages = [
  { path: '/', element: <Dashboard /> },
  { path: '/users', element: <Users /> },
  { path: '/products', element: <Products /> },
  { path: '/orders', element: <Orders /> },
  { path: '/payments', element: <Payments /> },
  { path: '/tickets', element: <Tickets /> },
  { path: '/discounts', element: <Discounts /> },
  { path: '/warranty', element: <Warranty /> },
  { path: '/lock', element: <Lock /> },
  { path: '/admins', element: <Admins /> },
  { path: '/methods', element: <Methods /> },
  { path: '/broadcast', element: <Broadcast /> },
  { path: '/settings', element: <Settings /> },
  { path: '/buttons', element: <ButtonLayout /> },
  { path: '/appearance', element: <Appearance /> },
  { path: '/bot-texts', element: <BotTexts /> },
  { path: '/menu-builder', element: <MenuBuilder /> },
  { path: '/api-docs', element: <ApiDocs /> },
]

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        {pages.map(({ path, element }) => (
          <Route key={path} path={path} element={
            <PrivateRoute path={path}>
              <Layout>{element}</Layout>
            </PrivateRoute>
          } />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
