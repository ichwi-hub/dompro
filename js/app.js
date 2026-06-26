const addStageBtn = document.getElementById('addStageBtn');
const stageList = document.getElementById('stageList');
const stagesCount = document.getElementById('stagesCount');
const progressValue = document.getElementById('progressValue');

addStageBtn.addEventListener('click', () => {
  const name = prompt('Название нового этапа:');
  if (!name) return;

  const li = document.createElement('li');
  li.className = 'stage-item';
  li.innerHTML = `
    <span class="stage-name">${name}</span>
    <span class="stage-status">Ожидает</span>
  `;
  stageList.appendChild(li);

  const total = stageList.children.length;
  const done = stageList.querySelectorAll('.done').length;
  stagesCount.textContent = total;
  progressValue.textContent = Math.round((done / total) * 100) + '%';
});
