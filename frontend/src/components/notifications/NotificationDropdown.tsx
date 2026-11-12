import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bell,
  CheckCheck,
  Calendar,
  AlertTriangle,
  Pill,
  Info,
  ChevronRight,
  Loader2,
  X,
  ExternalLink,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { notificationService, AppNotification } from '../../services/notificationService';
import { useTranslation } from '../../context/LanguageContext';

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHrs = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHrs / 24);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHrs < 24) return `${diffHrs}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return 'Recently';
  }
}

export const NotificationDropdown: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await notificationService.getNotifications(0, 30);
      setNotifications(data.items || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err: any) {
      console.warn('Could not fetch notifications:', err);
      setError('Unable to load notifications.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    // Refresh notifications every 60 seconds
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Handle outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleToggle = () => {
    if (!isOpen) {
      fetchNotifications();
    }
    setIsOpen(!isOpen);
  };

  const handleMarkAsRead = async (notification: AppNotification, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (notification.is_read) return;

    try {
      // Optimistic update
      setNotifications((prev) =>
        prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));

      await notificationService.markAsRead(notification.id);
    } catch (err) {
      console.error('Failed to mark notification read:', err);
      // Revert if needed
      fetchNotifications();
    }
  };

  const handleMarkAllAsRead = async () => {
    if (unreadCount === 0) return;
    try {
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      await notificationService.markAllAsRead();
    } catch (err) {
      console.error('Failed to mark all as read:', err);
      fetchNotifications();
    }
  };

  const handleNotificationClick = async (n: AppNotification) => {
    if (!n.is_read) {
      await handleMarkAsRead(n);
    }
    if (n.link) {
      setIsOpen(false);
      navigate(n.link);
    }
  };

  const getIconForType = (type: string) => {
    switch (type) {
      case 'appointment':
        return <Calendar className="w-4 h-4 text-emerald-600" />;
      case 'alert':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'stock':
        return <Pill className="w-4 h-4 text-sky-600" />;
      case 'info':
      default:
        return <Info className="w-4 h-4 text-teal-600" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isOpen}
        aria-label={t('notifications', 'Notifications')}
        className={`relative p-2 rounded-lg transition-colors ${
          isOpen
            ? 'bg-slate-100 text-slate-800'
            : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
        }`}
        title={t('notifications', 'Notifications')}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-emerald-600 rounded-full ring-2 ring-white shadow-xs animate-in fade-in zoom-in-75">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          role="region"
          aria-label={t('notifications', 'Notifications')}
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-white border border-slate-200/90 rounded-2xl shadow-xl shadow-slate-300/40 z-50 overflow-hidden flex flex-col max-h-[500px] animate-in fade-in slide-in-from-top-2 duration-150"
        >
          {/* Header */}
          <div className="px-4 py-3 bg-gradient-to-r from-slate-50 to-slate-100 border-b border-slate-200/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-800">{t('notifications', 'Notifications')}</h3>
              {unreadCount > 0 && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                  {unreadCount} {t('unread', 'unread')}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllAsRead}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-slate-600 hover:text-emerald-700 hover:bg-white rounded-md transition-colors"
                  title={t('markAllAsRead', 'Mark all as read')}
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>{t('markAllAsRead', 'Mark all read')}</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {loading && notifications.length === 0 ? (
              <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
                <span className="text-xs">{t('loadingNotifications', 'Loading alerts...')}</span>
              </div>
            ) : error && notifications.length === 0 ? (
              <div className="py-10 px-4 text-center">
                <AlertTriangle className="w-6 h-6 mx-auto text-amber-500 mb-2" />
                <p className="text-xs text-slate-600 mb-2">{error}</p>
                <button
                  onClick={fetchNotifications}
                  className="px-3 py-1 text-xs font-semibold rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
                >
                  {t('retry', 'Retry')}
                </button>
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-12 px-4 text-center">
                <Bell className="w-8 h-8 mx-auto text-slate-300 mb-2 stroke-[1.5]" />
                <p className="text-sm font-semibold text-slate-700">{t('noNotifications', 'No notifications yet')}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {t('noNotificationsDesc', "You're all caught up with healthcare alerts and reminders.")}
                </p>
              </div>
            ) : (
              notifications.map((n) => {
                return (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`px-4 py-3 flex items-start gap-3 transition-colors cursor-pointer text-left ${
                      n.is_read
                        ? 'bg-white hover:bg-slate-50'
                        : 'bg-emerald-50/50 hover:bg-emerald-50/80 border-l-4 border-emerald-500'
                    }`}
                  >
                    <div className="p-2 rounded-xl bg-white border border-slate-200/70 shadow-2xs flex-shrink-0 mt-0.5">
                      {getIconForType(n.type)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <h4
                          className={`text-xs text-slate-900 leading-snug line-clamp-1 ${
                            n.is_read ? 'font-medium' : 'font-bold'
                          }`}
                        >
                          {n.title}
                        </h4>
                        <span className="text-[10px] text-slate-400 whitespace-nowrap flex-shrink-0">
                          {formatRelativeTime(n.created_at)}
                        </span>
                      </div>

                      <p className="text-xs text-slate-600 mt-0.5 line-clamp-2 leading-relaxed">
                        {n.message}
                      </p>

                      <div className="flex items-center justify-between mt-1.5 pt-1">
                        {n.link ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 hover:text-emerald-800">
                            {t('viewDetails', 'View details')}
                            <ExternalLink className="w-3 h-3" />
                          </span>
                        ) : <span />}

                        {!n.is_read && (
                          <button
                            type="button"
                            onClick={(e) => handleMarkAsRead(n, e)}
                            className="text-[10px] text-slate-400 hover:text-slate-700 underline"
                          >
                            {t('markRead', 'Mark read')}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 bg-slate-50 border-t border-slate-200/80 flex items-center justify-between text-[11px] text-slate-500">
            <span>NALAM AI Alerts</span>
            <button
              type="button"
              onClick={fetchNotifications}
              className="text-emerald-700 hover:text-emerald-800 font-semibold"
            >
              {t('refresh', 'Refresh')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
