const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('#site-nav');
const toast = document.querySelector('.toast');

// The Menu button is handled by site-nav.js on every page.

document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      toast.classList.add('show');
      window.setTimeout(() => toast.classList.remove('show'), 1600);
    } catch {
      button.textContent = 'Select manually';
    }
  });
});

document.querySelector('#year').textContent = new Date().getFullYear();

const number = new Intl.NumberFormat('en-GB');

const fields = {
  height: document.querySelector('#metric-height'),
  difficulty: document.querySelector('#metric-difficulty'),
  networkHashrate: document.querySelector('#metric-network-hashrate'),
  connections: document.querySelector('#metric-connections'),
  rpc: document.querySelector('#metric-rpc'),
  tipAge: document.querySelector('#metric-tip-age'),
  state: document.querySelector('#node-state'),
  dot: document.querySelector('#node-dot'),
};

async function updateNodeStatus() {
  try {
    const response = await fetch('/api/node-info/index.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const info = await response.json();
    // get_info height counts blocks; the newest block is one below it.
    fields.height.textContent = `#${number.format(Math.max(0, (info.height ?? 1) - 1))}`;
    const tipAge = Number(info.tip_age_seconds);
    fields.tipAge.textContent = Number.isFinite(tipAge) ? `Last block found ${formatAge(tipAge)} ago` : 'Last block time unavailable';
    fields.difficulty.textContent = number.format(info.difficulty ?? 0);
    const target = Number(info.target);
    const networkHashrate = target > 0 ? Number(info.difficulty ?? 0) / target : 0;
    fields.networkHashrate.textContent = formatHashrate(networkHashrate);
    const peerCount = info.peer_connections
      ?? ((info.incoming_connections_count ?? 0) + (info.outgoing_connections_count ?? 0));
    fields.connections.textContent = info.connections_hidden ? 'HIDDEN' : number.format(peerCount);
    fields.connections.title = info.connections_hidden
      ? 'Connection counts are intentionally hidden by the public restricted RPC.'
      : 'Current incoming and outgoing P2P peer nodes, not unique people.';
    fields.rpc.textContent = info.restricted ? 'RESTRICTED' : 'ONLINE';
    if (info.status !== 'OK') {
      fields.state.textContent = info.status || 'Node unavailable';
      fields.dot.className = 'status-dot offline';
    } else if (info.synchronized !== true) {
      fields.state.textContent = 'Node unsynchronized';
      fields.dot.className = 'status-dot offline';
    } else if (info.tip_fresh !== true) {
      fields.state.textContent = 'Network tip stale';
      fields.dot.className = 'status-dot offline';
    } else if (info.peer_ready !== true) {
      fields.state.textContent = 'Network under-peered';
      fields.dot.className = 'status-dot offline';
    } else {
      fields.state.textContent = 'Node synchronized';
      fields.dot.className = 'status-dot online';
    }
  } catch {
    fields.state.textContent = 'Status unavailable';
    fields.rpc.textContent = '—';
    fields.tipAge.textContent = 'Network data unavailable';
    fields.dot.className = 'status-dot offline';
  }
}

function formatAge(seconds) {
  const value = Math.max(0, Math.round(Number(seconds) || 0));
  if (value < 60) return `${value}s`;
  if (value < 3600) return `${Math.floor(value / 60)}m`;
  if (value < 86400) return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`;
  return `${Math.floor(value / 86400)}d`;
}

const chainStrip = document.querySelector('#chain-strip');

async function updateChainStrip() {
  try {
    const response = await fetch('explorer/api.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'blocks', limit: 8 }),
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const headers = (await response.json()).headers;
    if (!Array.isArray(headers) || !headers.length) throw new Error('No blocks');
    const now = Date.now() / 1000;
    chainStrip.replaceChildren(...headers.slice(0, 8).reverse().map((block) => {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = `explorer/#/block/${encodeURIComponent(block.height)}`;
      link.title = `Block ${number.format(block.height)} · ${number.format(block.num_txes || 0)} transactions`;
      const height = document.createElement('strong');
      height.textContent = `#${number.format(block.height)}`;
      const age = document.createElement('span');
      age.textContent = formatAge(now - Number(block.timestamp));
      link.append(height, age);
      item.append(link);
      return item;
    }));
    chainStrip.classList.add('loaded');
  } catch {
    chainStrip.classList.remove('loaded');
  }
}

function updateNetwork() {
  updateNodeStatus();
  updateChainStrip();
}

updateNetwork();
window.setInterval(updateNetwork, 30000);

function formatHashrate(value) {
  let rate = Number(value) || 0;
  const units = ['H/s', 'kH/s', 'MH/s', 'GH/s'];
  let unit = 0;
  while (rate >= 1000 && unit < units.length - 1) {
    rate /= 1000;
    unit += 1;
  }
  return `${rate.toLocaleString('en-GB', { maximumFractionDigits: rate < 10 ? 2 : 1 })} ${units[unit]}`;
}
