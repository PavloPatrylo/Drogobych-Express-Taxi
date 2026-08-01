import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  ShieldAlert,
  Plus,
  RefreshCw,
  AlertCircle,
  Search,
  Phone,
  Copy,
  Check,
  Pencil,
  Trash2,
  X,
  UserCheck,
  UserX,
  Lock,
  Key,
  Shield,
  Truck,
  Headphones,
  MessageCircle,
} from 'lucide-react';

export default function StaffPage() {
  const [staff, setStaff] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Search
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [copiedId, setCopiedId] = useState(null);

  // Modal State for Add / Edit
  const [showModal, setShowModal] = useState(false);
  const [editingMember, setEditingMember] = useState(null); // null if creating, user object if editing
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    role: 'driver',
    password: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchStaff = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get('/auth/staff');
      setStaff(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch staff:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStaff();
  }, []);

  const handleCopyPhone = (phone, id) => {
    if (!phone) return;
    navigator.clipboard.writeText(phone);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleOpenAddModal = () => {
    setEditingMember(null);
    setFormData({
      full_name: '',
      phone: '',
      role: 'driver',
      password: '',
    });
    setShowModal(true);
  };

  const handleOpenEditModal = (member) => {
    setEditingMember(member);
    setFormData({
      full_name: member.full_name || member.name || '',
      phone: member.phone || '',
      role: member.role || 'driver',
      password: '',
    });
    setShowModal(true);
  };

  const handleToggleBlock = async (member) => {
    try {
      const endpoint = member.is_active ? `/auth/staff/${member.id}/block` : `/auth/staff/${member.id}/unblock`;
      await api.post(endpoint);
      fetchStaff();
    } catch (err) {
      alert(`Помилка зміни статусу: ${err.message}`);
    }
  };

  const handleDeleteStaff = async (member) => {
    if (!confirm(`⚠️ Ви дійсно бажаєте видалити співробітника ${member.full_name || member.phone}?`)) {
      return;
    }
    try {
      await api.delete(`/auth/staff/${member.id}`);
      fetchStaff();
    } catch (err) {
      alert(`Помилка видалення: ${err.message}`);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!formData.full_name.trim()) {
      alert('Будь ласка, вкажіть ПІБ співробітника');
      return;
    }
    let digits = formData.phone.replace(/\D/g, '');
    if (digits.startsWith('380') && digits.length === 12) {
      digits = digits.slice(2);
    }
    if (digits.length !== 10 || !digits.startsWith('0')) {
      alert('⚠️ Номер телефону повинен містити рівно 10 цифр і починатися з 0 (наприклад: 0971234567)!');
      return;
    }

    if (!editingMember && formData.role !== 'driver' && !formData.password.trim()) {
      alert('Будь ласка, вкажіть пароль для входу Диспетчера / Адміна у веб-панель');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingMember) {
        // Edit existing
        const payload = {
          full_name: formData.full_name,
          phone: formData.phone,
          role: formData.role,
        };
        if (formData.password.trim()) {
          payload.password = formData.password;
        }
        await api.put(`/auth/staff/${editingMember.id}`, payload);
      } else {
        // Create new
        await api.post('/auth/staff', {
          full_name: formData.full_name,
          phone: formData.phone,
          role: formData.role,
          password: formData.password,
        });
      }
      setShowModal(false);
      fetchStaff();
    } catch (err) {
      alert(`Помилка збереження даних: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredStaff = staff.filter((member) => {
    const query = search.toLowerCase();
    const name = (member.full_name || member.name || '').toLowerCase();
    const phone = (member.phone || '').toLowerCase();
    const matchesQuery = name.includes(query) || phone.includes(query);

    if (roleFilter !== 'all') {
      if (roleFilter === 'driver' && member.role !== 'driver') return false;
      if (roleFilter === 'dispatcher' && member.role !== 'dispatcher') return false;
      if (roleFilter === 'admin' && (member.role !== 'admin' && member.role !== 'owner')) return false;
    }

    if (statusFilter !== 'all') {
      if (statusFilter === 'active' && !member.is_active) return false;
      if (statusFilter === 'blocked' && member.is_active) return false;
    }

    return matchesQuery;
  });

  const getRoleBadge = (role) => {
    switch (role) {
      case 'admin':
      case 'owner':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-yellow-400 bg-yellow-500/10 px-2.5 py-1 rounded-lg border border-yellow-500/20">
            <Shield size={12} /> Власник / Адмін
          </span>
        );
      case 'dispatcher':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 bg-purple-500/10 px-2.5 py-1 rounded-lg border border-purple-500/20">
            <Headphones size={12} /> Диспетчер
          </span>
        );
      case 'driver':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-400 bg-sky-500/10 px-2.5 py-1 rounded-lg border border-sky-500/20">
            <Truck size={12} /> Водій
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
            <ShieldAlert className="text-yellow-400" size={28} />
            <span>Управління персоналом</span>
          </h1>
          <p className="text-sm text-slate-400">
            Керування командами водіїв, диспетчерів та системними ролями доступу
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={fetchStaff}
            disabled={isLoading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            title="Оновити список"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin text-yellow-400' : ''} />
          </button>

          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-yellow-400 outline-none focus:border-yellow-400 cursor-pointer"
          >
            <option value="all">Усі ролі</option>
            <option value="driver">🚚 Водії</option>
            <option value="dispatcher">🎧 Диспетчери</option>
            <option value="admin">👑 Власники / Адміни</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-emerald-400 outline-none focus:border-yellow-400 cursor-pointer"
          >
            <option value="all">Усі статуси</option>
            <option value="active">🟢 Тільки активні</option>
            <option value="blocked">🔴 Тільки заблоковані</option>
          </select>

          {/* Search Input */}
          <div className="relative min-w-[240px]">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Пошук за ім'ям або телефоном..."
              className="w-full bg-slate-900 border border-slate-800 focus:border-yellow-400 rounded-xl py-2 pl-10 pr-4 text-xs text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>

          {/* Add Staff Button */}
          <button
            onClick={handleOpenAddModal}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/10 text-xs uppercase tracking-wider transition-all cursor-pointer"
          >
            <Plus size={18} />
            <span>Додати співробітника</span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="animate-spin text-yellow-400" size={32} />
          <span>Завантаження персоналу з бази даних...</span>
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
      {!isLoading && !error && filteredStaff.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <ShieldAlert size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="font-semibold text-slate-200">Співробітників не знайдено</p>
          <p className="text-xs text-slate-500 mt-1">Змініть параметри пошуку або додайте першого співробітника</p>
        </div>
      )}

      {/* Staff Table */}
      {!isLoading && !error && filteredStaff.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="p-4">Співробітник (ПІБ)</th>
                  <th className="p-4">Роль у системі</th>
                  <th className="p-4">Телефон (Дзвінок / Копіювання)</th>
                  <th className="p-4">Telegram Чат / ID</th>
                  <th className="p-4 text-center">Статус доступу</th>
                  <th className="p-4 text-right">Дії</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredStaff.map((member) => {
                  const displayName = member.full_name || member.name || 'Співробітник';
                  const isPhoneCopied = copiedId === member.id;

                  return (
                    <tr key={member.id} className="hover:bg-slate-800/40 transition-colors">
                      {/* Name & Avatar */}
                      <td className="p-4 font-semibold text-slate-100 flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center font-bold text-yellow-400 text-sm shrink-0">
                          {displayName[0]?.toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-slate-100 text-sm">{displayName}</div>
                          <div className="text-[10px] text-slate-500">ID: #{member.id}</div>
                        </div>
                      </td>

                      {/* Role Badge */}
                      <td className="p-4">
                        {getRoleBadge(member.role)}
                      </td>

                      {/* Phone */}
                      <td className="p-4 font-mono">
                        {member.phone ? (
                          <div className="flex items-center gap-2">
                            <a
                              href={`tel:${member.phone}`}
                              className="inline-flex items-center gap-1.5 text-yellow-400 hover:text-yellow-300 font-bold hover:underline transition-colors"
                              title="Подзвонити у 1 клік"
                            >
                              <Phone size={13} />
                              <span>{member.phone}</span>
                            </a>
                            <button
                              onClick={() => handleCopyPhone(member.phone, member.id)}
                              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                              title="Копіювати номер"
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

                      {/* Telegram Chat Link */}
                      <td className="p-4">
                        {member.telegram_id ? (
                          <a
                            href={`tg://user?id=${member.telegram_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-sky-400 hover:text-sky-300 font-bold hover:underline transition-colors bg-sky-500/10 px-2.5 py-1 rounded-lg border border-sky-500/20"
                            title="Відкрити чат у Telegram"
                          >
                            <MessageCircle size={13} />
                            <span>Чат (# {member.telegram_id})</span>
                          </a>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">Невідомо</span>
                        )}
                      </td>

                      {/* Status / Toggle Block */}
                      <td className="p-4 text-center">
                        <button
                          onClick={() => handleToggleBlock(member)}
                          className={`px-3 py-1 rounded-xl border font-bold text-xs transition-all cursor-pointer ${
                            member.is_active
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30'
                              : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-emerald-500/10 hover:text-emerald-400'
                          }`}
                        >
                          {member.is_active ? '🟢 Активний' : '🔴 Заблокований'}
                        </button>
                      </td>

                      {/* Actions */}
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenEditModal(member)}
                            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-yellow-400 transition-colors cursor-pointer"
                            title="Редагувати співробітника"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteStaff(member)}
                            className="p-2 rounded-lg bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                            title="Видалити співробітника"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE / EDIT STAFF MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-bold text-slate-100 text-base">
                <ShieldAlert size={20} className="text-yellow-400" />
                <span>{editingMember ? 'Редагувати співробітника' : 'Додати нового співробітника'}</span>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="space-y-4">
              {/* Full Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  ПІБ Співробітника *
                </label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="Наприклад: Ковальчук Іван Олександрович"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-100 outline-none"
                  required
                />
              </div>

              {/* Phone */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Номер телефону (10 цифр) *
                </label>
                <input
                  type="text"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="0971234567"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs font-mono text-yellow-400 outline-none"
                  required
                />
              </div>

              {/* Role Selection */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Системна роль *
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-100 font-semibold outline-none cursor-pointer"
                >
                  <option value="driver">🚚 Водій</option>
                  <option value="dispatcher">🎧 Диспетчер</option>
                  <option value="admin">👑 Власник / Адмін</option>
                </select>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  {formData.role === 'driver'
                    ? "Пароль (не потрібен для водія у Telegram-боті)"
                    : editingMember
                    ? "Пароль (залиште порожнім, щоб не змінювати)"
                    : "Пароль для входу у веб-панель *"}
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder={formData.role === 'driver' ? "Водій входить через Telegram без паролю" : "••••••••"}
                  disabled={formData.role === 'driver'}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-100 outline-none font-mono disabled:opacity-40 disabled:cursor-not-allowed"
                  required={!editingMember && formData.role !== 'driver'}
                />
                {formData.role === 'driver' && (
                  <p className="text-[11px] text-sky-400 font-medium mt-1">
                    💡 Водій ідентифікується в Telegram-боті за вказаним номером телефону.
                  </p>
                )}
              </div>

              {/* Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 font-bold text-xs cursor-pointer"
                >
                  Скасувати
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-yellow-500/10 cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? 'Збереження...' : editingMember ? 'Зберегти зміни' : 'Створити співробітника'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
