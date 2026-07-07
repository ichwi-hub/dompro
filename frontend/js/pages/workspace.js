import { getExpertClientDetail, getExpertClients } from '../api.js';
import {
  checkAuth,
  formatDate,
  handleApiError,
  initLogoutButton,
} from '../common.js';

const routes = {
  feed: { title: 'Лента', subtitle: 'Статичная заглушка (Фаза 1a)' },
  clients: { title: 'Мои клиенты', subtitle: 'Клиенты из accepted-откликов' },
  contracts: { title: 'Договоры', subtitle: 'Секция будет реализована позже' },
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

async function renderFeed() {
  document.getElementById('workspaceContent').innerHTML = `
    <div class="workspace-grid">
      <article class="workspace-card">
        <h3>Новые заказы дня</h3>
        <p>Заглушка ленты. В следующем спринте добавим real-time подборку заказов.</p>
      </article>
      <article class="workspace-card">
        <h3>Рекомендации</h3>
        <p>Заглушка рекомендаций по категориям и откликам.</p>
      </article>
      <article class="workspace-card">
        <h3>Новости платформы</h3>
        <p>Заглушка для внутренних обновлений DomPro.</p>
      </article>
    </div>
  `;
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
