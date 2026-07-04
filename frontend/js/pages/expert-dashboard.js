/** Кабинет эксперта */
import {
  getExpertProfile,
  getExpertResponses,
  getVerificationStatus,
  getWalletBalance,
  getWalletTransactions,
  submitVerification,
  topupWallet,
  updateExpertProfile,
} from '../api.js';
import {
  checkAuth,
  closeModal,
  formatDate,
  formatMoney,
  handleApiError,
  initLogoutButton,
  initModals,
  openModal,
  orderStatusLabel,
  responseStatusLabel,
  showNotification,
  verificationLabel,
} from '../common.js';

let profile = null;

async function loadDashboard() {
  const user = await checkAuth('expert');
  if (!user) return;

  document.getElementById('userGreeting').textContent = user.email;

  const pendingName = sessionStorage.getItem('dompro_pending_profile_name');
  if (pendingName) {
    showNotification('Заполните профиль и загрузите документы для верификации', 'info');
    sessionStorage.removeItem('dompro_pending_profile_name');
  }

  await Promise.all([
    loadProfile(),
    loadVerification(),
    loadWallet(),
    loadTransactions(),
    loadResponses(),
  ]);
}

async function loadProfile() {
  profile = await getExpertProfile();
  const el = document.getElementById('profileInfo');
  el.innerHTML = `
    <p><strong>${profile.full_name || 'Не указано'}</strong></p>
    <p class="list-item-meta">${profile.specialization || 'Специализация не указана'}</p>
    <p class="list-item-meta">Стаж: ${profile.experience_years} лет · Рейтинг: ${profile.rating}</p>
    <p>${profile.description || '—'}</p>
    ${!profile.is_profile_complete ? '<p class="badge badge-warning">Профиль не заполнен</p>' : ''}
  `;
}

async function loadVerification() {
  const status = await getVerificationStatus();
  const el = document.getElementById('verificationInfo');
  const badgeClass = status.verification_status === 'verified' ? 'badge-success' : 'badge-warning';
  el.innerHTML = `<span class="badge ${badgeClass}">${verificationLabel(status.verification_status)}</span>`;

  const actions = document.getElementById('verificationActions');
  actions.innerHTML = '';
  if (status.can_submit && profile?.is_profile_complete) {
    const btn = document.createElement('button');
    btn.className = 'btn btn-outline btn-sm';
    btn.textContent = 'Загрузить документы';
    btn.onclick = () => openModal('verificationModal');
    actions.appendChild(btn);
  } else if (!profile?.is_profile_complete) {
    actions.innerHTML = '<p class="list-item-meta">Сначала заполните профиль</p>';
  }
}

async function loadWallet() {
  const data = await getWalletBalance();
  document.getElementById('balanceValue').textContent = formatMoney(data.balance);
}

async function loadTransactions() {
  const items = await getWalletTransactions();
  const el = document.getElementById('transactionsList');
  if (!items.length) {
    el.innerHTML = '<p class="empty-state">Транзакций пока нет</p>';
    return;
  }
  el.innerHTML = `<table class="tx-table"><thead><tr><th>Тип</th><th>Сумма</th><th>Дата</th></tr></thead><tbody>
    ${items.map((t) => `<tr>
      <td>${t.type === 'deposit' ? 'Пополнение' : 'Отклик'}</td>
      <td>${formatMoney(t.amount)}</td>
      <td>${formatDate(t.created_at)}</td>
    </tr>`).join('')}
  </tbody></table>`;
}

async function loadResponses() {
  const items = await getExpertResponses();
  const el = document.getElementById('responsesList');
  if (!items.length) {
    el.innerHTML = '<li class="empty-state">Откликов пока нет</li>';
    return;
  }
  el.innerHTML = items.map((r) => `
    <li class="list-item">
      <div class="list-item-header">
        <h3>${r.order.title}</h3>
        <span class="badge">${responseStatusLabel(r.status)}</span>
      </div>
      <p class="list-item-meta">${r.order.category} · ${orderStatusLabel(r.order.status)} · ${formatMoney(r.cost)}</p>
      <p>${r.message || '—'}</p>
    </li>
  `).join('');
}

document.getElementById('editProfileBtn').addEventListener('click', () => {
  const form = document.getElementById('profileForm');
  if (profile) {
    form.full_name.value = profile.full_name || '';
    form.specialization.value = profile.specialization || '';
    form.experience_years.value = profile.experience_years || 0;
    form.description.value = profile.description || '';
  }
  openModal('profileModal');
});

document.getElementById('profileForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await updateExpertProfile({
      full_name: f.full_name.value.trim(),
      specialization: f.specialization.value.trim(),
      experience_years: Number(f.experience_years.value),
      description: f.description.value.trim(),
    });
    closeModal('profileModal');
    showNotification('Профиль обновлён', 'success');
    await loadProfile();
    await loadVerification();
  } catch (err) {
    handleApiError(err);
  }
});

document.getElementById('topupBtn').addEventListener('click', () => openModal('topupModal'));

document.getElementById('topupForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const amount = e.target.amount.value;
    const res = await topupWallet(amount);
    closeModal('topupModal');
    document.getElementById('balanceValue').textContent = formatMoney(res.balance);
    showNotification(res.message || 'Баланс пополнен', 'success');
    await loadTransactions();
  } catch (err) {
    handleApiError(err);
  }
});

document.getElementById('verificationForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  const fd = new FormData();
  fd.append('inn', f.inn.value.trim());
  fd.append('diploma_file', f.diploma_file.files[0]);
  fd.append('self_employment_file', f.self_employment_file.files[0]);
  if (f.bar_association_file.files[0]) {
    fd.append('bar_association_file', f.bar_association_file.files[0]);
  }
  try {
    await submitVerification(fd);
    closeModal('verificationModal');
    showNotification('Заявка на верификацию отправлена', 'success');
    await loadVerification();
  } catch (err) {
    handleApiError(err);
  }
});

initModals();
initLogoutButton();
loadDashboard();
