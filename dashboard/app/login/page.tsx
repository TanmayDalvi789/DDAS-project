/**
 * Login Page
 * Authentication entry point (UI only, no form handling)
 */

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl p-8 shadow-md">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">DDAS</h1>
          <p className="text-sm text-slate-500">
            Distributed Duplicate Asset Scanner
          </p>
        </div>

        {/* Login Form */}
        <form className="space-y-4">
          {/* Email Input */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              type="email"
              placeholder="name@company.com"
              className="input-field"
            />
          </div>

          {/* Password Input */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Password
            </label>
            <input
              type="password"
              placeholder="••••••••"
              className="input-field"
            />
          </div>

          {/* Submit Button */}
          <button
            type="button"
            className="w-full btn-primary"
          >
            Sign In
          </button>
        </form>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-500">
            Contact your administrator for access
          </p>
        </div>
      </div>
    </div>
  );
}
