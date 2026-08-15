const tabs = [...document.querySelectorAll('[role="tab"]')];
const panels = [...document.querySelectorAll('[role="tabpanel"]')];

tabs.forEach((tab) => tab.addEventListener('click', () => {
  tabs.forEach((item) => item.setAttribute('aria-selected', String(item === tab)));
  panels.forEach((panel) => {
    const active = panel.id === tab.dataset.panel;
    panel.hidden = !active;
    panel.classList.toggle('active', active);
  });
}));

fetch('/api/node/get_info', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: '{}'
}).then((response) => {
  if (!response.ok) throw new Error('node unavailable');
  return response.json();
}).then((info) => {
  document.querySelector('#node-state').textContent = info.status === 'OK' ? 'Online' : info.status;
  document.querySelector('#height').textContent = Number(info.height).toLocaleString();
  document.querySelector('#peers').textContent = Number(info.incoming_connections_count || 0) + Number(info.outgoing_connections_count || 0);
}).catch(() => {
  document.querySelector('#node-state').textContent = 'Unavailable';
});
