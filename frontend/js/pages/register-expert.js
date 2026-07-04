/** Регистрация эксперта */
import { registerExpert } from '../api.js';
import { saveToken } from '../auth.js';
import { handleApiError, showNotification } from '../common.js';

document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  try {
    const data = await registerExpert({
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      password: form.password.value,
    });

    saveToken(data.access_token);
    sessionStorage.setItem('dompro_pending_profile_name', form.full_name.value.trim());

    showNotification('Аккаунт создан! Заполните профиль и загрузите документы для верификации.', 'success');
    setTimeout(() => {
      window.location.href = 'expert-dashboard.html';
    }, 1200);
  } catch (err) {
    handleApiError(err);
  }
});
