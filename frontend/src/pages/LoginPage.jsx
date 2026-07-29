import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, User, Sparkles, AlertCircle, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username || !password) {
      setError('Будь ласка, заповніть усі поля');
      return;
    }

    const result = await login(username, password);
    if (result.success) {
      navigate('/schedule');
    } else {
      setError(result.error || 'Невірний логін або пароль');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-amber-600/10 rounded-full blur-3xl pointer-events-none"></div>

      {/* Login Card */}
      <div className="w-full max-w-md bg-slate-900/80 border border-slate-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl relative z-10">
        <div className="text-center space-y-3 mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-yellow-500 to-amber-300 font-display text-3xl font-bold text-slate-950 shadow-xl shadow-yellow-500/20 mb-2">
            ET
          </div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100">
            Експрес Таксі
          </h1>
          <p className="text-sm text-slate-400">
            Адмін-панель диспетчера та власника
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle size={18} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Номер телефону
            </label>
            <div className="relative">
              <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="tel"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="+380XXXXXXXXX"
                className="w-full bg-slate-950/60 border border-slate-800 focus:border-yellow-400 rounded-xl py-3 pl-11 pr-4 text-slate-100 placeholder-slate-600 outline-none transition-colors text-sm font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Пароль
            </label>
            <div className="relative">
              <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950/60 border border-slate-800 focus:border-yellow-400 rounded-xl py-3 pl-11 pr-4 text-slate-100 placeholder-slate-600 outline-none transition-colors text-sm font-medium"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold py-3.5 px-6 rounded-xl shadow-lg shadow-yellow-500/20 flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-50 active:scale-[0.99]"
          >
            <span>{isLoading ? 'Зачекайте...' : 'Увійти в систему'}</span>
            <ArrowRight size={18} />
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-800/80 text-center text-xs text-slate-500">
          Львів — Дрогобич • Пасажирські перевезення
        </div>
      </div>
    </div>
  );
}
