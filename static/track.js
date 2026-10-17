// 跟踪与执行交互
async function loadPlatforms() {
  try {
    const r = await fetch('/api/platforms');
    const d = await r.json();
    const select = document.getElementById('execPlatform');
    select.innerHTML = d.platforms.map(p => `<option value="${p.id}" data-category="${p.category}">${p.name}${p.requiresKyc ? ' 🔒KYC' : ''}</option>`).join('');
    filterPlatforms();
  } catch (e) { /* ignore */ }
}

function filterPlatforms() {
  const sel = document.getElementById('execPlatform');
  if (!sel) return;
  const projectSel = document.getElementById('execProjectId');
  const isRwa = projectSel && projectSel.value === 'demo-equityx';
  Array.from(sel.options).forEach(opt => {
    if (isRwa) {
      opt.disabled = opt.dataset.category !== 'rwa';
    } else {
      opt.disabled = opt.dataset.category === 'rwa';
    }
  });
}

document.getElementById('execProjectId').addEventListener('change', filterPlatforms);
loadPlatforms();

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
      <span>${it.project_id} ${it.note ? '· ' + it.note : ''}</span>
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

async function loadExecutions() {
  const r = await fetch('/api/executions');
  const d = await r.json();
  const list = document.getElementById('executionList');
  if (!d.executions || d.executions.length === 0) {
    list.innerHTML = '<li class="text-slate-500">暂无执行记录。</li>';
    return;
  }
  list.innerHTML = d.executions.map(c => `
    <li class="bg-slate-800/50 rounded px-2 py-1">
      <div class="flex items-center justify-between">
        <span>${c.projectId} · ${c.platform} · ${c.actionType} · ${c.amount || ''}</span>
        <span class="text-[10px] text-slate-500">${new Date(c.createdAt*1000).toLocaleTimeString()}</span>
      </div>
      <div class="text-[10px] font-mono text-slate-500 break-all">tx: ${c.txHash || '-'}</div>
      <div class="text-[10px] text-slate-400">status: ${c.status}</div>
      ${c.blockExplorer ? `<a href="${c.blockExplorer}" target="_blank" class="text-indigo-300 hover:underline text-[10px]">链上查询 →</a>` : ''}
    </li>
  `).join('');
}

document.getElementById('buyBtn').addEventListener('click', async () => {
  const projectId = document.getElementById('execProjectId').value;
  const platform = document.getElementById('execPlatform').value;
  const amount = document.getElementById('execAmount').value.trim();
  if (!amount) { alert('请输入数量'); return; }
  const result = document.getElementById('buyResult');
  result.textContent = '提交中…';
  try {
    const r = await fetch('/api/buy', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ projectId, platform, amount, userLabel: 'demo-user' })
    });
    const d = await r.json();
    if (d.error) {
      result.innerHTML = `<div class="text-rose-400">${d.error}</div>`;
      return;
    }
    const oc = d.consent.onChain || {};
    result.innerHTML = `
      <div class="bg-emerald-900/20 border border-emerald-800/40 rounded p-3 mt-2">
        <div class="text-emerald-300 font-semibold text-sm">✓ 授权记录已生成</div>
        <div class="text-xs text-slate-400 mt-1">${d.disclaimer}</div>
        <div class="font-mono text-[10px] text-slate-500 break-all mt-1">execution: ${d.execution.executionId}</div>
        <div class="font-mono text-[10px] text-slate-500 break-all">tx: ${oc.txHash || '-'}</div>
        <a href="${d.redirectUrl}" target="_blank" class="mt-1 inline-block text-indigo-300 hover:underline text-xs">跳转 ${platform} →</a>
      </div>
    `;
    loadExecutions();
  } catch (e) {
    result.innerHTML = `<div class="text-rose-400">失败：${e}</div>`;
  }
});

loadWatch();
loadExecutions();
