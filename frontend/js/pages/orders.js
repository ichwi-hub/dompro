/** Лента заказов для эксперта */
import { createResponse, getOrders, getWalletBalance } from '../api.js';
import {
  checkAuth,
  closeModal,
  formatDate,
  formatMoney,
  handleApiError,
  initLogoutButton,
  initModals,
  openModal,
  showNotification,
} from '../common.js';

let currentOrderId = null;
let balance = 0;

async function init() {
  await checkAuth('expert');
  initLogoutButton();
  initModals();
  await loadBalance();
  await loadOrders();
}

async function loadBalance() {
  const data = await getWalletBalance();
  balance = Number(data.balance);
  document.getElementById('balanceBadge').textContent = formatMoney(balance);
}

async function loadOrders() {
  const data = await getOrders({ limit: 50 });
  const items = data.items || [];
  const el = document.getElementById('ordersList');

  if (!items.length) {
    el.innerHTML = '<li class="empty-state">Открытых заказов нет</li>';
    return;
  }

  el.innerHTML = items.map((o) => `
    <li class="list-item">
      <div class="list-item-header">
        <h3>${o.title}</h3>
        <button class="btn btn-primary btn-sm" data-order-id="${o.id}" data-title="${o.title.replace(/"/g, '&quot;')}">Откликнуться</button>
      </div>
      <p class="list-item-meta">${o.category} · ${o.budget ? formatMoney(o.budget) : 'Бюджет не указан'} · ${o.deadline ? 'до ' + formatDate(o.deadline) : ''}</p>
      <p>${o.description || ''}</p>
      ${o.client_display_name ? `<p class="list-item-meta">Заказчик: ${o.client_display_name}</p>` : ''}
    </li>
  `).join('');

  el.querySelectorAll('[data-order-id]').forEach((btn) => {
    btn.addEventListener('click', () => openResponseModal(btn.dataset.orderId, btn.dataset.title));
  });
}

function openResponseModal(orderId, title) {
  if (balance < 150) {
    showNotification('Недостаточно средств. Пополните баланс (минимум 150 ₽)', 'error');
    return;
  }
  currentOrderId = orderId;
  document.getElementById('responseOrderTitle').textContent = title;
  document.getElementById('responseForm').reset();
  openModal('responseModal');
}

document.getElementById('responseForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!currentOrderId) return;

  try {
    await createResponse(currentOrderId, e.target.message.value.trim());
    closeModal('responseModal');
    showNotification('Отклик отправлен, списано 150 ₽', 'success');
    await loadBalance();
  } catch (err) {
    handleApiError(err);
  }
});

init();
