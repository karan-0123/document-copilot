import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export const Signup: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
    });

    if (signUpError) {
      setError(signUpError.message);
      setLoading(false);
    } else {
      navigate('/', { replace: true });
    }
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-zinc-50 px-4 py-8 text-zinc-900 font-sans overflow-y-auto">
      <div className="w-full max-w-[480px] rounded-2xl border border-zinc-200 bg-white p-8 md:p-10 shadow-sm">
        <h2 className="text-2xl font-semibold tracking-tight text-center mb-1">Create account</h2>
        <p className="text-zinc-500 text-sm text-center mb-8">
          Register for an account to access Document Copilot.
        </p>
        
        {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-3.5 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSignup} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-zinc-900 mb-2">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3.5 py-2.5 text-sm text-zinc-900 placeholder-zinc-400 focus:border-zinc-400 focus:outline-none transition-colors"
              placeholder="you@driftwood.com"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-zinc-900 mb-2">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3.5 py-2.5 text-sm text-zinc-900 placeholder-zinc-400 focus:border-zinc-400 focus:outline-none transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#18181b] py-3 text-sm font-semibold text-white transition hover:bg-[#27272a] disabled:opacity-50 mt-2 shadow-sm"
          >
            {loading ? 'Creating...' : 'Sign up'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-zinc-500">
          Already have an account?{' '}
          <Link to="/login" className="text-zinc-900 hover:underline font-semibold">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
