import { Link } from 'react-router-dom'
import LoginForm from '@/components/auth/LoginForm'

export default function Login() {
  return (
    <div className="min-h-screen bg-cream-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link to="/">
            <h1 className="font-serif text-3xl text-sage-600 mb-1">Amy</h1>
          </Link>
          <p className="text-stone-500 text-sm">Good to have you back</p>
        </div>
        <div className="card">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}
