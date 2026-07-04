/** Страница входа */
import { login } from '../api.js';
import { handleApiError, handleLoginSuccess, showNotification } from '../common.js';

const roleButtons = document.querySelectorAll('.role-switch button');
let selectedRole = 'expert';

roleButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    roleButtons.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    selectedRole = btn.dataset.role;
  });
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const loginValue = form.login.value.trim();
  const password = form.password.value;

  try {
    const data = await login(loginValue, password);
    const role = data.user?.role;

    if (role && role !== selectedRole) {
      showNotification(`Вы вошли как ${role === 'expert' ? 'эксперт' : 'клиент'}`, 'info');
    }

    await handleLoginSuccess(data);
  } catch (err) {
    handleApiError(err);
  }
});
