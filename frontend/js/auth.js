/**
 * Управление JWT-токеном и данными пользователя в localStorage.
 */

const TOKEN_KEY = 'dompro_token';
const USER_KEY = 'dompro_user';

/** Сохранить access-токен. */
export function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/** Получить access-токен или null. */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/** Удалить токен и данные пользователя (выход). */
export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Есть ли сохранённый токен. */
export function isAuthenticated() {
  return Boolean(getToken());
}

/** Сохранить данные пользователя из /auth/me. */
export function saveUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/** Получить кэшированные данные пользователя. */
export function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/** Роль текущего пользователя (expert | client | admin). */
export function getUserRole() {
  return getUser()?.role ?? null;
}

/** Выйти из аккаунта. */
export function logout() {
  removeToken();
  window.location.href = 'login.html';
}
