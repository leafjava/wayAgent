// 跟踪与执行交互
async function loadWatch() {
  const r = await fetch('/api/watchlist');
  const d = await r.json();
  const list = document.getElementById('watchList');
  if (!d.items || d.items.length === 0) {
    list.innerHTML = '<li class="text-slate-500">暂无关注项，输入 projectId 加入。</li>';
    return;
  }
  list.innerHTML = d.items.map(it => `
    <li class="flex items-center justify-between bg-slate-800/50 rounded px-2 py-1">
      <span>${it.projectId} ${it.note ? '· ' + it.note : ''}</span>
      <button data-id="${it.id}" class="removeBtn text-rose-400 hover:text-rose-300 text-xs">移除</button>
    </li>
  `).join('');
  document.querySelectorAll('.removeBtn').forEach(b => {
    b.addEventListener('click', async () => {
      await fetch('/api/watchlist/' + b.dataset.id, { method: 'DELETE' });
      loadWatch();
    });
  });
}

document.getElementById('addBtn').addEventListener('click', async () => {
  const projectId = document.getElementById('projectIdInput').value.trim();
  if (!projectId) return;
  await fetch('/api/watchlist', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ projectId, note: '', budget: 0 }) });
  document.getElementById('projectIdInput').value = '';
  loadWatch();
});

document.getElementById('savePlanBtn').addEventListener('click', async () => {
  const projectId = document.getElementById('planProjectId').value.trim();
  if (!projectId) { alert('请输入 projectId'); return; }
  const r = await fetch('/api/plan', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      projectId,
      budget: parseFloat(document.getElementById('planBudget').value || 0),
      riskPreference: document.getElementById('planRisk').value,
      trackingFrequency: document.getElementById('planFreq').value,
      notes: document.getElementById('planNotes').value,
    })
  });
  const d = await r.json();
  alert(`计划已保存：${d.planId.slice(0, 12)}…\n预算 ${d.budget} · 风险偏好 ${d.riskPreference} · 跟踪 ${d.trackingFrequency}`);
});

async function loadConsents() {
  const r = await fetch('/api/consent');
  const d = await r.json();
  const list = document.getElementById('consentList');
  if (!d.consents || d.consents.length === 0) {
    list.innerHTML = '<li class="text-slate-500">暂无授权记录。</li>';
    return;
  }
  list.innerHTML = d.consents.map(c => `
    <li class="bg-slate-800/50 rounded px-2 py-1">
      <div class="flex items-center justify-between">
        <span>${c.project_id} · ${c.platform} · ${c.action_type}</span>
        <span class="text-[10px] text-slate-500">${new Date(c.created_at*1000).toLocaleTimeString()}</span>
      </div>
      <div class="text-[10px] font-mono text-slate-500 break-all">tx: ${c.tx_hash || '-'}</div>
      <div class="text-[10px] text-slate-400">${c.chain_status}</div>
      <a href="${c.redirectUrl}" target="_blank" class="text-indigo-300 hover:underline text-[10px]">跳转 ${c.platform} →</a>
    </li>
  `).join('');
}

document.getElementById('execBtn').addEventListener('click', async () => {
  const projectId = document.getElementById('execProjectId').value.trim();
  const platform = document.getElementById('execPlatform').value;
  const actionType = document.getElementById('execAction').value;
  if (!projectId) { alert('请输入 projectId'); return; }
  const r = await fetch('/api/consent', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ projectId, platform, actionType, userLabel: 'demo-user' })
  });
  const d = await r.json();
  loadConsents();
  if (d.onChain) {
    alert(`已生成授权记录 + 上链\ntx: ${d.onChain.txHash.slice(0,18)}…\n即将跳转 ${platform}`);
    if (d.redirectUrl) window.open(d.redirectUrl, '_blank');
  }
});

loadWatch();
loadConsents();
