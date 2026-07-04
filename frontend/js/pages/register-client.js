/** Регистрация клиента */
import { registerClient } from '../api.js';
import { handleApiError, handleLoginSuccess } from '../common.js';

document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  try {
    const data = await registerClient({
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      password: form.password.value,
      full_name: form.full_name.value.trim(),
    });
    await handleLoginSuccess(data);
  } catch (err) {
    handleApiError(err);
  }
});
