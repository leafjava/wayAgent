// 项目方后台（content gen）交互
const projectSelect = document.getElementById('projectSelect');
const contentResult = document.getElementById('contentResult');

projectSelect.addEventListener('change', () => {
  const url = new URL(location.href);
  url.searchParams.set('projectId', projectSelect.value);
  location.href = url.toString();
});

document.querySelectorAll('.templateBtn').forEach(b => {
  b.addEventListener('click', async () => {
    const projectId = projectSelect.value;
    const template = b.dataset.template;
    b.disabled = true;
    b.textContent = '生成中…';
    try {
      const r = await fetch('/api/content', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ projectId, template, audience: 'investor' })
      });
      const d = await r.json();
      renderContent(d);
    } catch (e) {
      contentResult.innerHTML = `<div class="text-rose-400 text-sm">生成失败：${e}</div>`;
    } finally {
      b.disabled = false;
      b.textContent = b.textContent.replace('生成中…', '');
    }
  });
});

function renderContent(d) {
  if (d.error) {
    contentResult.innerHTML = `<div class="text-rose-400 text-sm">${d.error}</div>`;
    return;
  }
  const sectionsHtml = (d.sections || []).map(s => `
    <div class="mt-2">
      <div class="text-slate-300 text-[11px] font-semibold">${s.heading}</div>
      <div class="text-slate-400 text-xs mt-1">${s.body}</div>
    </div>
  `).join('');
  const oc = d.onChain || {};
  contentResult.innerHTML = `
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-slate-100 text-sm font-semibold">${d.title}</div>
          <div class="text-slate-500 text-[10px] mt-0.5">${d.projectName} · ${d.audience}</div>
        </div>
        <button data-content='${JSON.stringify(d).replace(/'/g, "&#39;")}' class="copyBtn text-xs text-indigo-300 hover:text-indigo-200">复制全文</button>
      </div>
      <div class="mt-2">${sectionsHtml}</div>
      <div class="mt-2 text-amber-300 text-[10px]">${d.disclaimer || ''}</div>
      ${oc.txHash ? `<div class="mt-3 bg-indigo-900/20 border border-indigo-800/40 rounded p-2"><div class="text-indigo-300 text-xs font-semibold">✓ 已上链</div><div class="font-mono text-slate-500 text-[10px] break-all">tx: ${oc.txHash}</div><div class="font-mono text-slate-500 text-[10px] break-all">hash: ${oc.evidenceHash}</div><a href="/proof?hash=${oc.evidenceHash}" class="text-indigo-300 hover:underline text-[10px]">→ 验证</a></div>` : ''}
    </div>
  `;
  document.querySelector('.copyBtn').addEventListener('click', e => {
    const d = JSON.parse(e.target.dataset.content.replace(/&#39;/g, "'"));
    const text = (d.sections || []).map(s => `${s.heading}\n${s.body}`).join('\n\n');
    navigator.clipboard.writeText(text).then(() => alert('已复制'));
  });
}
