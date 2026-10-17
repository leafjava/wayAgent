// 帮我分析（analyze）交互
const projectSelect = document.getElementById('projectSelect');
const summary = document.getElementById('summary');
const fundamentals = document.getElementById('fundamentals');
const market = document.getElementById('market');
const risk = document.getElementById('risk');

projectSelect.addEventListener('change', () => {
  const url = new URL(location.href);
  url.searchParams.set('projectId', projectSelect.value);
  location.href = url.toString();
});

document.getElementById('analyzeBtn').addEventListener('click', async () => {
  const projectId = projectSelect.value;
  const r = await fetch(`/api/analyze?projectId=${projectId}`);
  const d = await r.json();
  renderAnalysis(d);
});

document.getElementById('riskBtn').addEventListener('click', async () => {
  const projectId = projectSelect.value;
  const r = await fetch(`/api/risk?projectId=${projectId}`);
  const d = await r.json();
  renderRisk(d);
});

function renderAnalysis(d) {
  summary.innerHTML = `<div class="text-slate-300">${d.summary || ''}</div>`;
  // 基本面
  const fund = d.fundamentals || {};
  const teamHtml = (fund.team || []).map(t => `<div class="text-slate-300">· ${t.info || JSON.stringify(t)}</div>`).join('') || '<div class="text-slate-500">未提取到团队信息</div>';
  const fundingHtml = (fund.funding && fund.funding.rounds && fund.funding.rounds.length) ? fund.funding.rounds.map(r => `<div class="text-slate-300">· ${r}</div>`).join('') : '<div class="text-slate-500">未提取到融资信息</div>';
  const useCasesHtml = (fund.useCases || []).map(c => `<div class="text-slate-300">· ${c}</div>`).join('') || '<div class="text-slate-500">未提取到应用场景</div>';
  fundamentals.innerHTML = `
    <div><span class="text-slate-500">资料完整度：</span><span class="text-slate-200">${((fund.dataCompleteness || 0) * 100).toFixed(0)}%</span></div>
    <div class="mt-2"><span class="text-slate-500">团队：</span>${teamHtml}</div>
    <div class="mt-2"><span class="text-slate-500">融资：</span>${fundingHtml}</div>
    <div class="mt-2"><span class="text-slate-500">用例：</span>${useCasesHtml}</div>
  `;
  // 市场 + 社区
  const m = d.market || {};
  const c = d.community || {};
  market.innerHTML = `
    <div><span class="text-slate-500">赛道：</span><span class="text-slate-200">${m.sector || '-'}</span></div>
    <div><span class="text-slate-500">Tier：</span><span class="text-slate-200">${m.tier || '-'}</span></div>
    <div><span class="text-slate-500">流通：</span><span class="text-slate-200">${m.circulatingSupply || '-'}</span></div>
    <div class="mt-2 text-amber-300 text-[10px]">${m.note || ''}</div>
    <div class="mt-2 text-slate-400">新闻 ${c.newsCount || 0} 条 · 社区 ${c.communityPostCount || 0} 条</div>
    <div class="text-slate-400">情绪：<span class="text-slate-200">${c.sentiment || '-'}</span></div>
  `;
  // 风险
  const rf = d.riskFactors || [];
  if (rf.length === 0) {
    risk.innerHTML = `<div class="text-emerald-300">✓ 未发现明显风险</div>`;
  } else {
    risk.innerHTML = rf.map(f => {
      const color = f.severity === 'high' ? '#ef4444' : f.severity === 'medium' ? '#f59e0b' : '#64748b';
      return `<div class="border-l-2 pl-2 py-1" style="border-color: ${color}"><span class="text-slate-200">${f.factor}</span><div class="text-slate-500 text-[10px]">${f.note || ''}</div></div>`;
    }).join('');
  }
}

function renderRisk(d) {
  const status = d.status || '?';
  const score = d.score || 0;
  const color = status === 'HEALTHY' ? '#10b981' : status === 'NEEDS_REVIEW' ? '#f59e0b' : '#ef4444';
  const factors = d.factors || {};
  const factorStr = Object.entries(factors).map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}`).join(' · ');
  const oc = d.onChain || {};
  risk.innerHTML = `
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div class="text-2xl font-bold" style="color: ${color}">${status}</div>
      <div class="text-xs text-slate-500">score ${score.toFixed(1)}</div>
      <div class="text-xs text-slate-400 mt-2">${factorStr}</div>
      ${d.changed ? `<div class="text-xs text-amber-300 mt-2">状态变更：${d.fromStatus} → ${status}</div>` : ''}
      ${oc.txHash ? `<div class="mt-2 text-[10px] font-mono text-slate-500 break-all">tx: ${oc.txHash}</div><a href="/proof?hash=${oc.evidenceHash}" class="text-indigo-300 hover:underline">→ 验证</a>` : ''}
    </div>
  `;
}

document.getElementById('analyzeBtn').click();
