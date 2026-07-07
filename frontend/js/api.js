/**
 * Обёртки fetch для DomPro API v1.
 */

import { getToken, removeToken, saveUser } from './auth.js';
  window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000/api/v1'
    : '/api/v1';

/**
 * Базовый запрос к API с обработкой ошибок.
 * @param {string} path — путь относительно /api/v1
 * @param {RequestInit} options
 * @param {boolean} auth — добавить Authorization
 */
async function request(path, options = {}, auth = true) {
  const headers = { ...(options.headers || {}) };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401 && auth) {
    removeToken();
    window.location.href = 'login.html';
    throw new Error('Требуется авторизация');
  }

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const message = data?.detail
      ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      : `Ошибка ${response.status}`;
    const err = new Error(message);
    err.status = response.status;
    err.data = data;
    throw err;
  }

  return data;
}

// ——— Auth ———

export async function login(login, password) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ login, password }),
  }, false);
}

export async function registerExpert({ email, phone, password }) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, phone, password }),
  }, false);
}

export async function registerClient({ email, phone, password, full_name }) {
  return request('/auth/register-client', {
    method: 'POST',
    body: JSON.stringify({ email, phone, password, full_name }),
  }, false);
}

export async function fetchMe() {
  const user = await request('/auth/me');
  saveUser(user);
  return user;
}

// ——— Expert profile ———

export async function getExpertProfile() {
  return request('/expert/profile');
}

export async function updateExpertProfile(data) {
  return request('/expert/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ——— Verification ———

export async function getVerificationStatus() {
  return request('/expert/verification/status');
}

export async function submitVerification(formData) {
  return request('/expert/verification/submit', {
    method: 'POST',
    body: formData,
    headers: {},
  });
}

// ——— Wallet ———

export async function getWalletBalance() {
  return request('/wallet/balance');
}

export async function getWalletTransactions() {
  const data = await request('/wallet/transactions');
  return data.items || data;
}

export async function topupWallet(amount) {
  return request('/wallet/topup', {
    method: 'POST',
    body: JSON.stringify({ amount: Number(amount) }),
  });
}

// ——— Orders ———

export async function createOrder(data) {
  return request('/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getOrders(params = {}) {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', params.page);
  if (params.limit) qs.set('limit', params.limit);
  if (params.category) qs.set('category', params.category);
  if (params.budget_min) qs.set('budget_min', params.budget_min);
  const query = qs.toString();
  return request(`/orders${query ? `?${query}` : ''}`);
}

export async function getOrder(orderId) {
  return request(`/orders/${orderId}`);
}

export async function updateOrderStatus(orderId, status) {
  return request(`/orders/${orderId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  });
}

// ——— Responses ———

export async function createResponse(orderId, message) {
  return request(`/orders/${orderId}/responses`, {
    method: 'POST',
    body: JSON.stringify({ message: message || null }),
  });
}

export async function getOrderResponses(orderId) {
  return request(`/orders/${orderId}/responses`);
}

export async function acceptResponse(responseId) {
  return request(`/responses/${responseId}/accept`, { method: 'PUT' });
}

export async function rejectResponse(responseId) {
  return request(`/responses/${responseId}/reject`, { method: 'PUT' });
}

export async function getExpertResponses() {
  return request('/expert/responses');
}

// --- Expert clients (workspace) ---

export async function getExpertClients() {
  const data = await request('/expert/clients');
  return data.items || [];
}

export async function getExpertClientDetail(clientId) {
  return request(`/expert/clients/${clientId}`);
}

// --- Expert feed ---

export async function getExpertFeed() {
  const data = await request('/expert/feed');
  return data.items || [];
}

// --- Contracts ---

export async function getExpertContracts() {
  const data = await request('/expert/contracts');
  return data.items || [];
}

export async function createOrderContract(orderId) {
  return request(`/orders/${orderId}/contract`, { method: 'POST' });
}

export async function getOrderContract(orderId) {
  return request(`/orders/${orderId}/contract`);
}

export async function downloadContract(contractId) {
  const token = getToken();
  const response = await fetch(`${API_BASE}/contracts/${contractId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    let message = `Ошибка ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `contract_${contractId}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
