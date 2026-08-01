import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Megaphone,
  Send,
  Calendar,
  Users,
  CheckCircle2,
  Clock,
  Bus,
  ShieldCheck,
  AlertCircle,
  FileText,
  DollarSign,
  User,
} from 'lucide-react';

export default function BroadcastPage() {
  const [activeTab, setActiveTab] = useState('schedule'); // 'schedule' або 'general'

  // General Broadcast State
  const [targetGroup, setTargetGroup] = useState('all');
  const [message, setMessage] = useState('');
  const [generalSentSuccess, setGeneralSentSuccess] = useState(null);
  const [generalRecipientsCount, setGeneralRecipientsCount] = useState(null);
  const [isSendingGeneral, setIsSendingGeneral] = useState(false);

  // Driver Schedule Publish State
  const [schedulePreset, setSchedulePreset] = useState('week'); // 'today', 'tomorrow', 'week', 'custom'
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedDriverId, setSelectedDriverId] = useState('all');
  const [scheduleComment, setScheduleComment] = useState('');

  const [driversList, setDriversList] = useState([]);
  const [schedulePreview, setSchedulePreview] = useState(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishSuccessMessage, setPublishSuccessMessage] = useState(null);

  const getKyivDateString = (offsetDays = 0) => {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    return d.toLocaleDateString('sv-SE', { timeZone: 'Europe/Kyiv' });
  };

  useEffect(() => {
    updateDatesByPreset('week');
    loadDrivers();
  }, []);

  const fetchGeneralPreview = async (group) => {
    try {
      const res = await api.post('/broadcast/preview', {
        target_group: group,
        text: 'preview',
      });
      setGeneralRecipientsCount(res.recipients_count);
    } catch (err) {
      console.error('Failed to fetch general preview:', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'general') {
      fetchGeneralPreview(targetGroup);
    }
  }, [activeTab, targetGroup]);

  const loadDrivers = async () => {
    try {
      const staff = await api.get('/auth/staff').catch(() => []);
      const driverUsers = (staff || []).filter((s) => s.role === 'driver' || s.is_driver);
      setDriversList(driverUsers);
    } catch (err) {
      console.error('Failed to load drivers:', err);
    }
  };

  const updateDatesByPreset = (preset) => {
    setSchedulePreset(preset);
    const todayStr = getKyivDateString(0);
    if (preset === 'today') {
      setDateFrom(todayStr);
      setDateTo(todayStr);
    } else if (preset === 'tomorrow') {
      const tomorrowStr = getKyivDateString(1);
      setDateFrom(tomorrowStr);
      setDateTo(tomorrowStr);
    } else if (preset === 'week') {
      setDateFrom(todayStr);
      setDateTo(getKyivDateString(6));
    }
  };

  const fetchSchedulePreview = async (dFrom, dTo, drvId) => {
    if (!dFrom || !dTo) return;
    setIsLoadingPreview(true);
    try {
      const payload = {
        date_from: dFrom,
        date_to: dTo,
        driver_id: drvId === 'all' ? null : Number(drvId),
      };
      const res = await api.post('/broadcast/publish-schedule/preview', payload);
      setSchedulePreview(res);
    } catch (err) {
      console.error('Failed to fetch schedule preview:', err);
    } finally {
      setIsLoadingPreview(false);
    }
  };

  useEffect(() => {
    if (dateFrom && dateTo) {
      fetchSchedulePreview(dateFrom, dateTo, selectedDriverId);
    }
  }, [dateFrom, dateTo, selectedDriverId]);

  const handleGeneralSend = async (e) => {
    e.preventDefault();
    if (!message.trim()) {
      alert('Будь ласка, введіть текст повідомлення');
      return;
    }
    setIsSendingGeneral(true);
    setGeneralSentSuccess(null);
    try {
      const res = await api.post('/broadcast/send', {
        target_group: targetGroup,
        text: message,
      });
      setGeneralSentSuccess(res.recipients_count ?? 0);
      setMessage('');
      setTimeout(() => {
        setGeneralSentSuccess(null);
      }, 6000);
    } catch (err) {
      alert(`Помилка надсилання оголошення: ${err.message}`);
    } finally {
      setIsSendingGeneral(false);
    }
  };

  const handlePublishScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!dateFrom || !dateTo) {
      alert('Будь ласка, вкажіть діапазон дат');
      return;
    }
    setIsPublishing(true);
    setPublishSuccessMessage(null);
    try {
      const res = await api.post('/broadcast/publish-schedule', {
        date_from: dateFrom,
        date_to: dateTo,
        driver_id: selectedDriverId === 'all' ? null : Number(selectedDriverId),
        comment: scheduleComment,
      });
      setPublishSuccessMessage(res.message);
      setTimeout(() => {
        setPublishSuccessMessage(null);
      }, 5000);
    } catch (err) {
      alert(`Помилка публікації графіку: ${err.message}`);
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl tracking-wide uppercase text-slate-100 flex items-center gap-3">
          <Megaphone className="text-yellow-400" size={28} />
          <span>Центр сповіщень та публікації графіків</span>
        </h1>
        <p className="text-sm text-slate-400">
          Публікація персональних графіків рейсів для водіїв та масові оголошення в Telegram
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 bg-slate-900 p-1.5 rounded-2xl border border-slate-800 w-fit">
        <button
          onClick={() => setActiveTab('schedule')}
          className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'schedule'
              ? 'bg-yellow-400 text-slate-950 shadow-md'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar size={16} />
          <span>📅 Публікація графіку водіям</span>
        </button>

        <button
          onClick={() => setActiveTab('general')}
          className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'general'
              ? 'bg-yellow-400 text-slate-950 shadow-md'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Megaphone size={16} />
          <span>📢 Загальні оголошення</span>
        </button>
      </div>

      {/* TAB 1: PUBLISH DRIVER SCHEDULE */}
      {activeTab === 'schedule' && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6 animate-fade-in">
          
          {publishSuccessMessage && (
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-400 text-sm font-medium animate-fade-in">
              <CheckCircle2 size={20} className="shrink-0 text-emerald-400" />
              <span>{publishSuccessMessage}</span>
            </div>
          )}

          <form onSubmit={handlePublishScheduleSubmit} className="space-y-6">
            
            {/* Date Range Selection & Presets */}
            <div className="space-y-3">
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider">
                1. Оберіть періoд графіку рейсів
              </label>

              {/* Quick Presets */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => updateDatesByPreset('today')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    schedulePreset === 'today'
                      ? 'bg-yellow-400/20 text-yellow-300 border-yellow-400/50 font-bold'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Сьогодні
                </button>

                <button
                  type="button"
                  onClick={() => updateDatesByPreset('tomorrow')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    schedulePreset === 'tomorrow'
                      ? 'bg-yellow-400/20 text-yellow-300 border-yellow-400/50 font-bold'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Завтра
                </button>

                <button
                  type="button"
                  onClick={() => updateDatesByPreset('week')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    schedulePreset === 'week'
                      ? 'bg-yellow-400/20 text-yellow-300 border-yellow-400/50 font-bold'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  На тиждень (7 днів)
                </button>

                <button
                  type="button"
                  onClick={() => setSchedulePreset('custom')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    schedulePreset === 'custom'
                      ? 'bg-yellow-400/20 text-yellow-300 border-yellow-400/50 font-bold'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Довільний період
                </button>
              </div>

              {/* Custom Date Pickers */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                  <span className="block text-[11px] text-slate-500 font-semibold mb-1">Дата З (початок):</span>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => {
                      setSchedulePreset('custom');
                      setDateFrom(e.target.value);
                    }}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 font-mono outline-none"
                    required
                  />
                </div>

                <div>
                  <span className="block text-[11px] text-slate-500 font-semibold mb-1">Дата ПО (кінець):</span>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => {
                      setSchedulePreset('custom');
                      setDateTo(e.target.value);
                    }}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 font-mono outline-none"
                    required
                  />
                </div>
              </div>
            </div>

            {/* Target Driver Selection */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider">
                2. Отримувач графіку
              </label>
              <select
                value={selectedDriverId}
                onChange={(e) => setSelectedDriverId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none font-medium"
              >
                <option value="all">👨‍✈️ Усім активним водіям</option>
                {driversList.map((d) => (
                  <option key={d.id} value={d.id}>
                    Водій: {d.full_name || d.name} ({d.phone || 'без тел.'})
                  </option>
                ))}
              </select>
            </div>

            {/* Schedule Calculation Preview Card */}
            {schedulePreview && (
              <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800 space-y-3">
                <div className="text-xs font-bold text-yellow-400 uppercase tracking-wider flex items-center justify-between">
                  <span>📊 Попередній розрахунок графіку ({schedulePreview.date_from} — {schedulePreview.date_to})</span>
                  {isLoadingPreview && <span className="text-slate-500 font-normal">Оновлення...</span>}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
                  <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase">Рейсів за період:</span>
                    <span className="font-mono font-bold text-slate-100 text-base">{schedulePreview.trips_count}</span>
                  </div>

                  <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase">Задіяно водіїв:</span>
                    <span className="font-mono font-bold text-yellow-400 text-base">{schedulePreview.drivers_count}</span>
                  </div>

                  <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase">Сумарно місць:</span>
                    <span className="font-mono font-bold text-amber-300 text-base">{schedulePreview.total_seats_limit}</span>
                  </div>

                  <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase">Розрахункова каса:</span>
                    <span className="font-mono font-bold text-emerald-400 text-base">{schedulePreview.total_revenue} ₴</span>
                  </div>
                </div>
              </div>
            )}

            {/* Comments / Instructions for Driver */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider">
                3. Примітка / Інструкція Диспетчера водіям (необов'язково)
              </label>
              <input
                type="text"
                value={scheduleComment}
                onChange={(e) => setScheduleComment(e.target.value)}
                placeholder="Наприклад: Прибути на посадку за 15 хв. Перевірити пальне!"
                className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none"
              />
            </div>

            {/* Submit Publish Button */}
            <button
              type="submit"
              disabled={isPublishing || !dateFrom || !dateTo}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-6 py-3.5 rounded-xl shadow-lg shadow-yellow-500/10 transition-all text-xs uppercase tracking-wider cursor-pointer disabled:opacity-50"
            >
              <Send size={16} />
              <span>{isPublishing ? 'Публікація...' : '🚀 Опублікувати графік для водіїв у Telegram MiniApp'}</span>
            </button>

          </form>
        </div>
      )}

      {/* TAB 2: GENERAL ANNOUNCEMENT BROADCAST */}
      {activeTab === 'general' && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6 animate-fade-in">
          {generalSentSuccess !== null && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-400 text-sm font-medium animate-fade-in">
              <CheckCircle2 size={20} className="shrink-0 text-emerald-400" />
              <span>Оголошення успішно надіслано в чергу для {generalSentSuccess} осіб у Telegram!</span>
            </div>
          )}

          <form onSubmit={handleGeneralSend} className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Аудиторія отримувачів
                </label>
                {generalRecipientsCount !== null && (
                  <span className="text-xs font-mono font-bold text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-500/20">
                    Отримають {generalRecipientsCount} осіб у Telegram
                  </span>
                )}
              </div>
              <select
                value={targetGroup}
                onChange={(e) => setTargetGroup(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-3 text-xs text-slate-200 outline-none"
              >
                <option value="all">📢 Усі підписані пасажири</option>
                <option value="today_passengers">🚕 Пасажири на сьогоднішні рейси</option>
                <option value="drivers">👮 Усі водії</option>
              </select>
            </div>

            {/* Quick Templates */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Швидкі шаблони оголошень
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setMessage("⚠️ ШАНОВНІ ПАСАЖИРИ! Посадку на рейс перенесено на платформу №3. Будь ласка, прибудьте за 10 хвилин до відправлення.")}
                  className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium transition-colors cursor-pointer"
                >
                  ⚠️ Зміна платформи посадки
                </button>
                <button
                  type="button"
                  onClick={() => setMessage("❄️ УВАГА! У зв'язку з погодними умовами та ситуацією на дорозі можлива незначна затримка рейсу на 10-15 хвилин. Перепрошуємо за незручності.")}
                  className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium transition-colors cursor-pointer"
                >
                  ❄️ Погодні умови / Затримка
                </button>
                <button
                  type="button"
                  onClick={() => setMessage("🚌 ОНОВЛЕННЯ РОЗКЛАДУ! Додано нові вечірні рейси за маршрутом Дрогобич ⇄ Львів. Перегляньте актуальний розклад у боті.")}
                  className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 font-medium transition-colors cursor-pointer"
                >
                  🚌 Оновлення розкладу рейсів
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Текст повідомлення
              </label>
              <textarea
                rows={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Введіть текст оголошення для Telegram бота..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl p-4 text-sm text-slate-100 placeholder-slate-600 outline-none resize-none font-sans"
              />
            </div>

            <button
              type="submit"
              disabled={isSendingGeneral || !message.trim()}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-bold px-6 py-3.5 rounded-xl shadow-lg shadow-yellow-500/10 transition-all text-xs uppercase tracking-wider cursor-pointer disabled:opacity-50"
            >
              <Send size={16} />
              <span>{isSendingGeneral ? 'Надсилання...' : '🚀 Надіслати сповіщення в Telegram'}</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
