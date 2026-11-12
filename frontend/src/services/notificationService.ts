import { apiRequest } from './apiClient';

export interface AppNotification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: 'info' | 'appointment' | 'stock' | 'alert';
  is_read: boolean;
  link?: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: AppNotification[];
  total: number;
  unread_count: number;
}

export const notificationService = {
  async getNotifications(skip: number = 0, limit: number = 50): Promise<NotificationListResponse> {
    return await apiRequest<NotificationListResponse>(`/api/notifications?skip=${skip}&limit=${limit}`);
  },

  async markAsRead(id: string): Promise<AppNotification> {
    return await apiRequest<AppNotification>(`/api/notifications/${id}/read`, {
      method: 'PATCH',
    });
  },

  async markAllAsRead(): Promise<{ status: string; marked_read: number }> {
    return await apiRequest<{ status: string; marked_read: number }>(`/api/notifications/read-all`, {
      method: 'POST',
    });
  },
};
