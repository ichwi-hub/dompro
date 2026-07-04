/** Кабинет клиента */
import { createOrder, getOrders } from '../api.js';
import {
  checkAuth,
  formatDate,
  formatMoney,
  handleApiError,
  initLogoutButton,
  orderStatusLabel,
  showNotification,
} from '../common.js';

async function loadDashboard() {
  const user = await checkAuth('client');
  if (!user) return;
  document.getElementById('userGreeting').textContent = user.full_name || user.email;
  await loadOrders();
}

async function loadOrders() {
  const data = await getOrders();
  const el = document.getElementById('ordersList');
  const items = data.items || data;

  if (!items.length) {
    el.innerHTML = '<li class="empty-state">Заказов пока нет. Создайте первый!</li>';
    return;
  }

  el.innerHTML = items.map((o) => `
    <li class="list-item">
      <a href="order-detail.html?id=${o.id}" style="text-decoration:none;color:inherit">
        <div class="list-item-header">
          <h3>${o.title}</h3>
          <span class="badge">${orderStatusLabel(o.status)}</span>
        </div>
        <p class="list-item-meta">${o.category} · ${o.budget ? formatMoney(o.budget) : 'Бюджет не указан'} · ${formatDate(o.created_at)}</p>
      </a>
    </li>
  `).join('');
}

document.getElementById('createOrderForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;

  const payload = {
    title: f.title.value.trim(),
    description: f.description.value.trim() || null,
    category: f.category.value,
    budget: f.budget.value ? Number(f.budget.value) : null,
    deadline: f.deadline.value || null,
  };

  try {
    await createOrder(payload);
    showNotification('Заказ опубликован', 'success');
    f.reset();
    await loadOrders();
  } catch (err) {
    handleApiError(err);
  }
});

initLogoutButton();
loadDashboard();
