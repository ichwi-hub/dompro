import {
  createOrderContract,
  downloadContract,
  getExpertClients,
  getExpertClientDetail,
  getExpertContracts,
  getExpertFeed,
} from '../api.js';
import {
  checkAuth,
  formatDate,
  formatMoney,
  handleApiError,
  initLogoutButton,
  orderStatusLabel,
  showNotification,
} from '../common.js';

const routes = {
  feed: { title: 'Лента', subtitle: 'Новые заказы и активная работа' },
  clients: { title: 'Мои клиенты', subtitle: 'Клиенты из accepted-откликов' },
  contracts: { title: 'Договоры', subtitle: 'PDF-договоры по заказам' },
  friends: { title: 'Друзья', subtitle: 'Секция будет реализована позже' },
  blogs: { title: 'Блоги', subtitle: 'Секция будет реализована позже' },
  laws: { title: 'Законодательство', subtitle: 'Секция будет реализована позже' },
};

let currentUser = null;

function getRoute() {
  const hash = window.location.hash.replace('#', '');
  return routes[hash] ? hash : 'feed';
}

function setHeader(routeKey) {
  const cfg = routes[routeKey];
  document.getElementById('workspaceTitle').textContent = cfg.title;
  document.getElementById('workspaceSubtitle').textContent = cfg.subtitle;

  document.querySelectorAll('.workspace-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.route === routeKey);
  });
}

function renderPlaceholder(text) {
  document.getElementById('workspaceContent').innerHTML = `
    <div class="workspace-card">
      <p>${text}</p>
    </div>
  `;
}

function feedBadge(item) {
  if (item.response_status === 'accepted') {
    return '<span class="badge badge-success">Ваш отклик принят</span>';
  }
  if (item.response_status === 'pending') {
    return '<span class="badge badge-warning">Ожидает решения</span>';
  }
  if (item.status === 'open' && !item.has_response) {
    return '<span class="badge">Можно откликнуться</span>';
  }
  return `<span class="badge">${orderStatusLabel(item.status)}</span>`;
}

function feedCardHtml(item) {
  return `
    <article class="workspace-client-card workspace-feed-card" data-order-id="${item.order_id}">
      <div class="list-item-header">
        <h3>${item.title}</h3>
        ${feedBadge(item)}
      </div>
      <p class="workspace-client-meta">
        ${item.budget ? formatMoney(item.budget) : 'Бюджет не указан'}
        ${item.deadline ? ' · до ' + formatDate(item.deadline) : ''}
      </p>
      <p>${item.description || ''}</p>
      <button class="btn btn-outline btn-sm" data-action="open-order">Открыть заказ</button>
    </article>
  `;
}

async function renderFeed() {
  const root = document.getElementById('workspaceContent');
  try {
    const items = await getExpertFeed();
    if (!items.length) {
      root.innerHTML = `
        <div class="workspace-card">
          <p>Нет новых заказов.</p>
          <p><a href="orders.html">Смотреть все заказы →</a></p>
        </div>
      `;
      return;
    }

    root.innerHTML = `
      <section class="workspace-list" id="feedList">
        ${items.map(feedCardHtml).join('')}
      </section>
    `;

    root.querySelectorAll('[data-action="open-order"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const card = btn.closest('[data-order-id]');
        const orderId = card?.getAttribute('data-order-id');
        if (orderId) {
          window.location.href = `order-detail.html?id=${orderId}`;
        }
      });
    });
  } catch (err) {
    handleApiError(err);
  }
}

function clientCardHtml(client) {
  return `
    <article class="workspace-client-card" data-client-id="${client.id}">
      <h3>${client.full_name}</h3>
      <p class="workspace-client-meta">Компания: ${client.company_name || '—'}</p>
      <p class="workspace-client-meta">Принятых заказов: ${client.accepted_orders_count}</p>
      <p class="workspace-client-meta">Последний заказ: ${client.last_order_title || '—'}</p>
      <p class="workspace-client-meta">Активность: ${formatDate(client.last_activity_at)}</p>
      <button class="btn btn-outline btn-sm" data-action="open-client">Открыть карточку</button>
    </article>
  `;
}

function clientDetailHtml(detail) {
  return `
    <div class="workspace-card">
      <h3>${detail.full_name}</h3>
      <p>Компания: ${detail.company_name || '—'}</p>
      <p>Принятые заказы: ${detail.accepted_orders_count}</p>
      <p>Принятые отклики: ${detail.accepted_responses_count}</p>
      <p>Последний заказ: ${detail.last_order_title || '—'}</p>
      <p>Последняя активность: ${formatDate(detail.last_activity_at)}</p>
    </div>
  `;
}

async function renderClients() {
  const root = document.getElementById('workspaceContent');
  try {
    const clients = await getExpertClients();
    if (!clients.length) {
      root.innerHTML = `
        <div class="workspace-card">
          <p>Пока нет клиентов. Клиент появится здесь после принятия вашего отклика.</p>
        </div>
      `;
      return;
    }

    root.innerHTML = `
      <section class="workspace-list" id="clientsList">
        ${clients.map(clientCardHtml).join('')}
      </section>
      <section id="clientDetailSection"></section>
    `;

    root.querySelectorAll('button[data-action="open-client"]').forEach((button) => {
      button.addEventListener('click', async () => {
        const parent = button.closest('[data-client-id]');
        if (!parent) return;
        const clientId = parent.getAttribute('data-client-id');
        try {
          const detail = await getExpertClientDetail(clientId);
          document.getElementById('clientDetailSection').innerHTML = clientDetailHtml(detail);
        } catch (err) {
          handleApiError(err);
        }
      });
    });
  } catch (err) {
    handleApiError(err);
  }
}

function contractStatusLabel(status) {
  const map = {
    draft: 'Черновик',
    signed: 'Подписан',
    cancelled: 'Отменён',
  };
  return map[status] || status;
}

function contractCardHtml(contract) {
  return `
    <article class="workspace-client-card">
      <h3>${contract.order_title}</h3>
      <p class="workspace-client-meta">Клиент: ${contract.client_name}</p>
      <p class="workspace-client-meta">Статус: ${contractStatusLabel(contract.status)}</p>
      <p class="workspace-client-meta">Создан: ${formatDate(contract.created_at)}</p>
      <button type="button" class="btn btn-outline btn-sm" data-action="download-contract" data-contract-id="${contract.id}">
        Скачать PDF
      </button>
    </article>
  `;
}

async function renderContracts() {
  const root = document.getElementById('workspaceContent');
  try {
    const contracts = await getExpertContracts();
    if (!contracts.length) {
      root.innerHTML = `
        <div class="workspace-card">
          <p>Договоров пока нет. Создайте договор на странице заказа после принятия отклика.</p>
        </div>
      `;
      return;
    }

    root.innerHTML = `
      <section class="workspace-list">
        ${contracts.map(contractCardHtml).join('')}
      </section>
    `;

    root.querySelectorAll('[data-action="download-contract"]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        try {
          await downloadContract(btn.dataset.contractId);
        } catch (err) {
          handleApiError(err);
        }
      });
    });
  } catch (err) {
    handleApiError(err);
  }
}

async function renderRoute() {
  const routeKey = getRoute();
  setHeader(routeKey);

  if (routeKey === 'feed') {
    await renderFeed();
    return;
  }
  if (routeKey === 'clients') {
    await renderClients();
    return;
  }
  if (routeKey === 'contracts') {
    await renderContracts();
    return;
  }
  renderPlaceholder('Раздел в разработке.');
}

async function bootstrap() {
  currentUser = await checkAuth('expert');
  if (!currentUser) return;
  document.getElementById('workspaceSubtitle').textContent = `${routes[getRoute()].subtitle} · ${currentUser.email}`;
  initLogoutButton();
  await renderRoute();
}

window.addEventListener('hashchange', renderRoute);
bootstrap();
