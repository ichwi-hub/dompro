const navToggle = document.getElementById('navToggle');
const headerInner = document.querySelector('.header-inner');
const heroSearch = document.getElementById('heroSearch');
const searchInput = document.getElementById('searchInput');
const categoryTags = document.getElementById('categoryTags');

if (navToggle && headerInner) {
  navToggle.addEventListener('click', () => {
    const isOpen = headerInner.classList.toggle('nav-open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });
}

if (categoryTags && searchInput) {
  categoryTags.addEventListener('click', (event) => {
    const tag = event.target.closest('.tag');
    if (!tag) return;

    const query = tag.dataset.query || '';
    searchInput.value = query;
    searchInput.focus();

    categoryTags.querySelectorAll('.tag').forEach((item) => {
      item.classList.toggle('active', item === tag);
    });
  });
}

if (heroSearch && searchInput) {
  heroSearch.addEventListener('submit', (event) => {
    event.preventDefault();
    const query = searchInput.value.trim();

    if (!query) {
      searchInput.focus();
      return;
    }

    alert(`Поиск экспертов: «${query}»\n\nВ прототипе поиск пока демонстрационный.`);
  });
}
