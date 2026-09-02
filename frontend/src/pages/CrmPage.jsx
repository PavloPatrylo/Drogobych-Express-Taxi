import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Users,
  Search,
  RefreshCw,
  AlertCircle,
  Star,
  Phone,
  Copy,
  Check,
  ExternalLink,
  MessageSquare,
  Bot,
  Smartphone,
  Globe,
  Filter,
  Calendar,
} from 'lucide-react';

export default function CrmPage() {
  const [passengers, setPassengers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortOption, setSortOption] = useState('name_asc');

  const fetchPassengers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/passengers');
      setPassengers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch passengers:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPassengers();
  }, []);

  const handleRoleChange = async (user, newRole) => {
    if (newRole === user.role) return;
    try {
      await api.post(`/passengers/${user.id}/role`, { role: newRole });
      fetchPassengers();
    } catch (err) {
      alert(`Помилка зміни ролі: ${err.message}`);
    }
  };

  const handleToggleBlock = async (user) => {
    try {
      const endpoint = user.is_active ? `/passengers/${user.id}/block` : `/passengers/${user.id}/unblock`;
      await api.post(endpoint);
      fetchPassengers();
    } catch (err) {
      alert(`Помилка зміни статусу: ${err.message}`);
    }
  };

  const handleCopyPhone = (phone, id) => {
    if (!phone) return;
    navigator.clipboard.writeText(phone);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredPassengers = passengers
    .filter((p) => {
      const query = search.toLowerCase();
      const name = (p.full_name || p.name || '').toLowerCase();
      const phone = (p.phone || '').toLowerCase();
      const telegramId = String(p.telegram_id || '');
      const matchesSearch = name.includes(query) || phone.includes(query) || telegramId.includes(query);

      const source = p.registration_source || (p.telegram_id ? 'Telegram-бот' : 'Телефонний дзвінок');
      if (sourceFilter !== 'all') {
        if (sourceFilter === 'bot' && source !== 'Telegram-бот') return false;
        if (sourceFilter === 'phone' && source !== 'Телефонний дзвінок') return false;
        if (sourceFilter === 'instagram' && source !== 'Instagram') return false;
      }

      if (statusFilter !== 'all') {
        if (statusFilter === 'active' && !p.is_active) return false;
        if (statusFilter === 'blocked' && p.is_active) return false;
      }

      return matchesSearch;
    })
    .sort((a, b) => {
      if (sortOption === 'name_asc') {
        const nameA = (a.full_name || a.name || '').toLowerCase();
        const nameB = (b.full_name || b.name || '').toLowerCase();
        return nameA.localeCompare(nameB, 'uk');
      }
      if (sortOption === 'name_desc') {
        const nameA = (a.full_name || a.name || '').toLowerCase();
        const nameB = (b.full_name || b.name || '').toLowerCase();
        return nameB.localeCompare(nameA, 'uk');
      }
      if (sortOption === 'trips_desc') {
        return (b.total_trips || 0) - (a.total_trips || 0);
      }
      if (sortOption === 'trust_desc') {
        return (b.trust_score ?? 100) - (a.trust_score ?? 100);
      }
      if (sortOption === 'trust_asc') {
        return (a.trust_score ?? 100) - (b.trust_score ?? 100);
      }
      if (sortOption === 'last_trip_desc') {
        if (!a.last_trip_date) return 1;
        if (!b.last_trip_date) return -1;
        const parseDate = (dStr) => {
          const parts = dStr.split('.');
          if (parts.length === 3) return new Date(parts[2], parts[1] - 1, parts[0]).getTime();
          return 0;
        };
        return parseDate(b.last_trip_date) - parseDate(a.last_trip_date);
      }
      if (sortOption === 'last_trip_asc') {
        if (!a.last_trip_date) return 1;
        if (!b.last_trip_date) return -1;
        const parseDate = (dStr) => {
          const parts = dStr.split('.');
          if (parts.length === 3) return new Date(parts[2], parts[1] - 1, parts[0]).getTime();
          return 0;
        };
        return parseDate(a.last_trip_date) - parseDate(b.last_trip_date);
      }
      return 0;
    });

  const getSourceBadge = (source) => {
    switch (source) {
      case 'Telegram-бот':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-500/20">
            <Bot size={12} /> Telegram-бот
          </span>
        );
      case 'Instagram':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 bg-purple-500/10 px-2.5 py-0.5 rounded-full border border-purple-500/20">
            <Smartphone size={12} /> Instagram
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2.5 py-0.5 rounded-full border border-amber-500/20">
            <Phone size={12} /> Телефонний дзвінок
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <Users className="text-yellow-400" size={28} />
            <span>База клієнтів (CRM)</span>
          </h1>
          <p className="text-sm text-slate-400">
            Керування профілями пасажирів, зв'язок у 1 клік та перевірка надійності за Київським часом
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={fetchPassengers}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>

          {/* Status Access Filter Select */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-medium text-emerald-400 font-semibold outline-none focus:border-yellow-400 cursor-pointer"
          >
            <option value="all">Усі статуси</option>
            <option value="active">🟢 Тільки активні</option>
            <option value="blocked">🔴 Тільки заблоковані</option>
          </select>

          {/* Source Filter Select */}
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-medium text-slate-200 outline-none focus:border-yellow-400"
          >
            <option value="all">Усі джерела</option>
            <option value="bot">🤖 Telegram-бот</option>
            <option value="phone">📞 Телефонний дзвінок</option>
            <option value="instagram">📱 Instagram</option>
          </select>

          {/* Sort Option Select */}
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-medium text-yellow-400 font-semibold outline-none focus:border-yellow-400 cursor-pointer"
          >
            <option value="name_asc">🔤 За ім'ям (А ➔ Я)</option>
            <option value="name_desc">🔤 За ім'ям (Я ➔ А)</option>
            <option value="trips_desc">👥 Спочатку найактивніші (за поїздками)</option>
            <option value="trust_desc">⭐ Найвищий рейтинг довіри (100% ➔ 0%)</option>
            <option value="trust_asc">⚠️ Найнижчий рейтинг довіри (0% ➔ 100%)</option>
            <option value="last_trip_desc">📅 За останньою поїздкою (найновіші)</option>
            <option value="last_trip_asc">📅 За останньою поїздкою (найдавніші)</option>
          </select>

          {/* Search Input */}
          <div className="relative min-w-[260px]">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Пошук за ім'ям, телефоном чи ID..."
              className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl py-2 pl-10 pr-4 text-xs text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження клієнтської бази з бази даних...</span>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>Помилка: {error}</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && filteredPassengers.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <Users size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="font-semibold text-slate-200">Пасажирів не знайдено</p>
          <p className="text-xs text-slate-500 mt-1">База даних поки порожня або немає збігів за пошуком</p>
        </div>
      )}

      {/* Passengers Table */}
      {!isLoading && !error && filteredPassengers.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="p-4">Клієнт (ПІБ / Нікнейм)</th>
                  <th className="p-4">Телефон (Дзвінок / Копіювання)</th>
                  <th className="p-4">Telegram Чат / ID</th>
                  <th className="p-4">Джерело реєстрації</th>
                  <th className="p-4 text-center">Поїздок</th>
                  <th className="p-4 text-center">Пропущено</th>
                  <th className="p-4 text-center">Остання поїздка</th>
                  <th className="p-4 text-center">Рейтинг довіри</th>
                  <th className="p-4 text-right">Статус доступу</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPassengers.map((p) => {
                  const displayName = p.full_name || p.name || 'Пасажир';
                  const regSource = p.registration_source || (p.telegram_id ? 'Telegram-бот' : 'Телефонний дзвінок');
                  const isPhoneCopied = copiedId === p.id;

                  return (
                    <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                      {/* 1. Client Identity Name & Avatar */}
                      <td className="p-4 font-semibold text-slate-100 flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center font-bold text-yellow-400 text-sm shrink-0">
                          {displayName[0]?.toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-slate-100 text-sm">{displayName}</div>
                          <div className="text-[10px] text-slate-500">ID клієнта: #{p.id}</div>
                        </div>
                      </td>

                      {/* 2. Phone Number with 1-click Call and 1-click Copy */}
                      <td className="p-4 font-mono">
                        {p.phone ? (
                          <div className="flex items-center gap-2">
                            <a
                              href={`tel:${p.phone}`}
                              className="inline-flex items-center gap-1.5 text-yellow-400 hover:text-yellow-300 font-bold hover:underline transition-colors"
                              title="Подзвонити в 1 клік"
                            >
                              <Phone size={13} className="text-yellow-400" />
                              <span>{p.phone}</span>
                            </a>
                            <button
                              onClick={() => handleCopyPhone(p.phone, p.id)}
                              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                              title="Копіювати номер телефону"
                            >
                              {isPhoneCopied ? (
                                <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-bold">
                                  <Check size={12} /> Скопійовано
                                </span>
                              ) : (
                                <Copy size={12} />
                              )}
                            </button>
                          </div>
                        ) : (
                          <span className="text-slate-500 font-sans">Телефон відсутній</span>
                        )}
                      </td>

                      {/* 3. Telegram Чат / ID */}
                      <td className="p-4">
                        {(() => {
                          const hasTelegram = Boolean(p.telegram_id || p.username);
                          if (!hasTelegram) {
                            return <span className="text-slate-500 font-medium italic">Невідомо</span>;
                          }

                          const cleanPhone = p.phone ? p.phone.replace(/\D/g, '').replace(/^0/, '380') : null;
                          const tgLink = p.username
                            ? `https://t.me/${p.username.replace('@', '')}`
                            : cleanPhone
                            ? `https://t.me/+${cleanPhone}`
                            : `tg://user?id=${p.telegram_id}`;

                          const labelText = p.username
                            ? `@${p.username.replace('@', '')}`
                            : `ID: ${p.telegram_id}`;

                          return (
                            <a
                              href={tgLink}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1.5 text-sky-400 hover:text-sky-300 font-mono font-bold hover:underline transition-colors bg-sky-500/10 px-2.5 py-1 rounded-lg border border-sky-500/20"
                              title="Відкрити чат у Telegram"
                            >
                              <MessageSquare size={13} />
                              <span>{labelText}</span>
                              <ExternalLink size={11} className="ml-0.5 opacity-70" />
                            </a>
                          );
                        })()}
                      </td>

                      {/* 4. Registration Source */}
                      <td className="p-4">
                        {getSourceBadge(regSource)}
                      </td>

                      {/* 5. Trips & No-shows Stats */}
                      <td className="p-4 text-center font-bold text-slate-200">{p.total_trips || 0}</td>
                      <td className="p-4 text-center font-bold text-red-400">{p.total_noshows || 0}</td>

                      {/* Last Trip Date */}
                      <td className="p-4 text-center">
                        {p.last_trip_date ? (
                          <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                            <Calendar size={12} /> {p.last_trip_date}
                          </span>
                        ) : (
                          <span className="text-slate-500 text-xs italic">Не їздив</span>
                        )}
                      </td>

                      {/* Trust Score */}
                      <td className="p-4 text-center">
                        <span className={`inline-flex items-center gap-1 font-mono font-bold px-2.5 py-1 rounded-full text-xs ${
                          (p.trust_score ?? 100) >= 80 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                        }`}>
                          <Star size={12} fill="currentColor" /> {p.trust_score ?? 100}%
                        </span>
                      </td>

                      {/* Status / Toggle Block */}
                      <td className="p-4 text-right">
                        <button
                          onClick={() => handleToggleBlock(p)}
                          className={`px-3 py-1.5 rounded-xl border font-bold text-xs transition-all cursor-pointer ${
                            p.is_active
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30'
                              : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-emerald-500/10 hover:text-emerald-400'
                          }`}
                        >
                          {p.is_active ? '🟢 Активний (Заблокувати)' : '🔴 Заблокований (Розблокувати)'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
