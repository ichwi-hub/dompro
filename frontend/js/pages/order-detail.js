/** Детали заказа: клиент или эксперт */
import {
  acceptResponse,
  createOrderContract,
  downloadContract,
  getOrder,
  getOrderContract,
  getOrderResponses,
  rejectResponse,
} from '../api.js';
import {
  checkAuth,
  formatDate,
  formatMoney,
  handleApiError,
  initLogoutButton,
  orderStatusLabel,
  responseStatusLabel,
  showNotification,
} from '../common.js';

const params = new URLSearchParams(window.location.search);
const orderId = params.get('id');

let userRole = null;

async function init() {
  const user = await checkAuth();
  if (!user) return;
  userRole = user.role;
  initLogoutButton();

  if (!orderId) {
    document.getElementById('orderInfo').innerHTML = '<p class="empty-state">Заказ не указан</p>';
    return;
  }

  await loadOrder();
  if (userRole === 'client') {
    await loadResponses();
  } else {
    const section = document.getElementById('responsesSection');
    if (section) section.style.display = 'none';
  }
  await loadContractSection();
}

async function loadOrder() {
  const order = await getOrder(orderId);
  document.getElementById('orderInfo').innerHTML = `
    <h1 class="page-title">${order.title}</h1>
    <p class="page-subtitle">
      <span class="badge">${orderStatusLabel(order.status)}</span>
      ${order.category} · ${order.budget ? formatMoney(order.budget) : 'Бюджет не указан'}
      ${order.deadline ? ' · до ' + formatDate(order.deadline) : ''}
    </p>
    <div class="card"><p>${order.description || 'Без описания'}</p></div>
  `;
}

async function loadContractSection() {
  const el = document.getElementById('contractSection');
  if (!el) return;

  if (userRole !== 'client' && userRole !== 'expert') {
    el.innerHTML = '';
    return;
  }

  try {
    const order = await getOrder(orderId);
    if (order.status !== 'in_progress') {
      el.innerHTML = '';
      return;
    }

    const contract = await getOrderContract(orderId);
    if (contract && contract.id) {
      el.innerHTML = `
        <section class="card">
          <h2>Договор</h2>
          <p class="list-item-meta">Статус: ${contract.status}</p>
          <button type="button" class="btn btn-outline btn-sm" id="downloadContractBtn">Скачать PDF</button>
        </section>
      `;
      document.getElementById('downloadContractBtn').addEventListener('click', async () => {
        try {
          await downloadContract(contract.id);
        } catch (err) {
          handleApiError(err);
        }
      });
      return;
    }

    el.innerHTML = `
      <section class="card">
        <h2>Договор</h2>
        <p class="list-item-meta">Сформируйте PDF-договор по принятому заказу.</p>
        <button class="btn btn-primary btn-sm" id="createContractBtn">Создать договор</button>
      </section>
    `;

    document.getElementById('createContractBtn').addEventListener('click', async () => {
      try {
        await createOrderContract(orderId);
        showNotification('Договор создан', 'success');
        await loadContractSection();
      } catch (err) {
        handleApiError(err);
      }
    });
  } catch (err) {
    handleApiError(err);
  }
}

async function loadResponses() {
  const items = await getOrderResponses(orderId);
  const el = document.getElementById('responsesList');

  if (!items.length) {
    el.innerHTML = '<li class="empty-state">Откликов пока нет. Эксперты увидят заказ в ленте.</li>';
    return;
  }

  el.innerHTML = items.map((r) => `
    <li class="list-item" data-response-id="${r.id}">
      <div class="list-item-header">
        <div>
          <h3>${r.expert.full_name || 'Эксперт'}</h3>
          <p class="list-item-meta">${r.expert.specialization || ''} · ⭐ ${r.expert.rating} · ${r.expert.experience_years} лет</p>
        </div>
        <span class="badge">${responseStatusLabel(r.status)}</span>
      </div>
      <p>${r.message || '—'}</p>
      ${r.status === 'pending' ? `
        <div class="card-actions">
          <button class="btn btn-primary btn-sm btn-accept">Принять</button>
          <button class="btn btn-outline btn-sm btn-danger btn-reject">Отклонить</button>
        </div>
      ` : ''}
    </li>
  `).join('');

  el.querySelectorAll('.btn-accept').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.closest('[data-response-id]').dataset.responseId;
      try {
        await acceptResponse(id);
        showNotification('Эксперт выбран, заказ в работе', 'success');
        await loadOrder();
        await loadResponses();
        await loadContractSection();
      } catch (err) {
        handleApiError(err);
      }
    });
  });

  el.querySelectorAll('.btn-reject').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.closest('[data-response-id]').dataset.responseId;
      try {
        await rejectResponse(id);
        showNotification('Отклик отклонён', 'info');
        await loadResponses();
      } catch (err) {
        handleApiError(err);
      }
    });
  });
}

init();
