/** Date/time formatting helpers. Uses date-fns v4 with locale-aware defaults. */
import { format, formatDistanceToNow, isToday, isYesterday } from "date-fns";
import { enIN } from "date-fns/locale";

const LOCALE = enIN;

/** Short date, e.g. "12 Jan 2026". */
export function formatDate(value: string | Date): string {
  return format(new Date(value), "d MMM yyyy", { locale: LOCALE });
}

/** 24h time, e.g. "14:30". */
export function formatTime(value: string | Date): string {
  return format(new Date(value), "HH:mm", { locale: LOCALE });
}

/** Relative time for chat/list timestamps, e.g. "5 minutes ago". */
export function formatRelative(value: string | Date): string {
  return formatDistanceToNow(new Date(value), { addSuffix: true, locale: LOCALE });
}

/** Chat timestamp label: Today/Yesterday/HH:mm or a date. */
export function chatTimestamp(value: string | Date): string {
  const date = new Date(value);
  if (isToday(date)) return formatTime(date);
  if (isYesterday(date)) return "Yesterday";
  return formatDate(date);
}

/** INR money formatting, e.g. ₹12,500. */
export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Numeric distance, e.g. "2.4 km". */
export function formatDistanceKm(km: number): string {
  return km >= 10 ? `${Math.round(km)} km` : `${km.toFixed(1)} km`;
}
