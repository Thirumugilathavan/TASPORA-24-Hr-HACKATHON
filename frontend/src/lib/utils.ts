import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString?: string): string {
  if (!dateString) return 'Date unavailable';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export function formatTime(timeString?: string): string {
  if (!timeString) return '';
  if (timeString.includes('AM') || timeString.includes('PM')) return timeString;
  const parts = timeString.split(':');
  if (parts.length >= 2) {
    const hours = parseInt(parts[0], 10);
    const minutes = parts[1];
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const formattedHours = hours % 12 || 12;
    return `${formattedHours.toString().padStart(2, '0')}:${minutes} ${ampm}`;
  }
  return timeString;
}

export function formatDistance(distanceKm?: number): string {
  if (distanceKm === undefined || distanceKm === null) {
    return 'Distance unavailable';
  }
  return `${distanceKm} km away`;
}

export function formatCurrency(amount?: number): string {
  if (amount === undefined || amount === null) return '';
  return `₹${amount}`;
}
