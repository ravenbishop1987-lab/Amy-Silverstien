import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { MessageCircle, Brain, History, Settings, LogOut } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'

const navItems = [
  { to: '/chat', icon: MessageCircle, label: 'Chat' },
  { to: '/memory', icon: Brain, label: 'Memory Bank' },
  { to: '/history', icon: History, label: 'History' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-cream-100 flex">
      <aside className="hidden sm:flex w-16 bg-white border-r border-cream-300 flex-col items-center py-4 shrink-0">
        <div className="mb-5 h-9 w-9 rounded-xl bg-sage-100 text-sage-700 flex items-center justify-center font-serif text-lg">
          A
        </div>

        <nav className="flex-1 space-y-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              title={label}
              className={({ isActive }) =>
                `h-10 w-10 flex items-center justify-center rounded-xl transition-all duration-150 ${
                  isActive
                    ? 'bg-sage-100 text-sage-700'
                    : 'text-stone-500 hover:bg-cream-200 hover:text-charcoal-800'
                }`
              }
            >
              <Icon size={18} />
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-cream-300 pt-3">
          <button
            onClick={handleLogout}
            className="h-10 w-10 flex items-center justify-center rounded-xl text-stone-400 hover:text-charcoal-800 hover:bg-cream-200 transition-all"
            title={`Sign out${user?.email ? ` (${user.email})` : ''}`}
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden pb-16 sm:pb-0">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-cream-300 bg-white sm:hidden">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `h-14 flex flex-col items-center justify-center gap-1 text-[10px] font-medium ${
                isActive ? 'text-sage-700 bg-sage-50' : 'text-stone-500'
              }`
            }
          >
            <Icon size={17} />
            <span>{label === 'Memory Bank' ? 'Memory' : label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
