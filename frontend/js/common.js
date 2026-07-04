/**
 * Общие утилиты UI: авторизация, уведомления, форматирование.
 */

import { fetchMe } from './api.js';
import { getToken, getUser, getUserRole, logout, saveToken, saveUser } from './auth.js';

/** Форматирование даты для интерфейса. */
export function formatDate(dateString) {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

/** Форматирование суммы в рублях. */
export function formatMoney(value) {
  const num = Number(value);
  if (Number.isNaN(num)) return '—';
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(num);
}

/** Человекочитаемый статус верификации. */
export function verificationLabel(status) {
  const map = {
    unverified: 'Не верифицирован',
    verification_pending: 'На проверке',
    verified: 'Верифицирован',
    rejected: 'Отклонён',
  };
  return map[status] || status;
}

/** Статус заказа. */
export function orderStatusLabel(status) {
  const map = {
    open: 'Открыт',
    in_progress: 'В работе',
    completed: 'Завершён',
    cancelled: 'Отменён',
  };
  return map[status] || status;
}

/** Статус отклика. */
export function responseStatusLabel(status) {
  const map = {
    pending: 'Ожидает',
    accepted: 'Принят',
    rejected: 'Отклонён',
  };
  return map[status] || status;
}

/**
 * Показать всплывающее уведомление.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 */
export function showNotification(message, type = 'info') {
  let container = document.getElementById('notifications');
  if (!container) {
    container = document.createElement('div');
    container.id = 'notifications';
    container.className = 'notifications';
    document.body.appendChild(container);
  }

  const el = document.createElement('div');
  el.className = `notification notification-${type}`;
  el.textContent = message;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('notification-hide');
    setTimeout(() => el.remove(), 300);
  }, 4000);
}

/**
 * Проверка авторизации и роли. Редирект при необходимости.
 * @param {'expert'|'client'|null} requiredRole
 * @returns {Promise<object|null>} user
 */
export async function checkAuth(requiredRole = null) {
  if (!getToken()) {
    window.location.href = 'login.html';
    return null;
  }

  let user = getUser();
  if (!user) {
    try {
      user = await fetchMe();
    } catch {
      window.location.href = 'login.html';
      return null;
    }
  }

  if (requiredRole && getUserRole() !== requiredRole) {
    showNotification('Нет доступа к этой странице', 'error');
    const role = getUserRole();
    if (role === 'expert') window.location.href = 'expert-dashboard.html';
    else if (role === 'client') window.location.href = 'client-dashboard.html';
    else window.location.href = 'login.html';
    return null;
  }

  return user;
}

/** Обработка формы входа после успешного API-ответа. */
export async function handleLoginSuccess(data) {
  saveToken(data.access_token);
  if (data.user) saveUser(data.user);
  else await fetchMe();

  const role = getUserRole();
  if (role === 'expert') window.location.href = 'expert-dashboard.html';
  else if (role === 'client') window.location.href = 'client-dashboard.html';
  else window.location.href = 'login.html';
}

/** Мобильное меню в шапке. */
export function initMobileNav() {
  const toggle = document.getElementById('navToggle');
  const inner = document.querySelector('.header-inner');
  if (!toggle || !inner) return;

  toggle.addEventListener('click', () => {
    const open = inner.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
}

/** Открыть/закрыть модальное окно. */
export function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('modal-open');
}

export function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('modal-open');
}

/** Привязка закрытия модалок по data-close. */
export function initModals() {
  document.querySelectorAll('[data-close]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal');
      if (modal) modal.classList.remove('modal-open');
    });
  });

  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) backdrop.classList.remove('modal-open');
    });
  });
}

/** Кнопка выхода в шапке кабинета. */
export function initLogoutButton() {
  const btn = document.getElementById('logoutBtn');
  if (btn) btn.addEventListener('click', (e) => {
    e.preventDefault();
    logout();
  });
}

/** Показать ошибку API пользователю. */
export function handleApiError(err) {
  if (err.status === 403) {
    showNotification('Нет доступа', 'error');
  } else {
    showNotification(err.message || 'Произошла ошибка', 'error');
  }
}
