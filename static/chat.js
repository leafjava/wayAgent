// 问得明白（chat）交互
const projectSelect = document.getElementById('projectSelect');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const anchorCheck = document.getElementById('anchorCheck');
const preferLlmCheck = document.getElementById('preferLlmCheck');
const llmBadge = document.getElementById('llmBadge');
const answerArea = document.getElementById('answerArea');

projectSelect.addEventListener('change', () => {
  const url = new URL(location.href);
  url.searchParams.set('projectId', projectSelect.value);
  location.href = url.toString();
});

document.querySelectorAll('.suggestedBtn').forEach(b => {
  b.addEventListener('click', () => {
    questionInput.value = b.textContent.trim();
    ask();
  });
});

askBtn.addEventListener('click', ask);
questionInput.addEventListener('keypress', e => { if (e.key === 'Enter') ask(); });

// LLM 状态
async function refreshLlmStatus() {
  try {
    const r = await fetch('/api/llm/status');
    const d = await r.json();
    if (d.enabled) {
      llmBadge.textContent = 'LLM: ' + d.model;
      llmBadge.className = 'text-[10px] px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-300 border border-emerald-800/40';
    } else {
      llmBadge.textContent = 'LLM: 本地引擎';
      llmBadge.className = 'text-[10px] px-2 py-0.5 rounded bg-amber-900/30 text-amber-300 border border-amber-800/40';
    }
  } catch (e) { /* ignore */ }
}
refreshLlmStatus();

async function ask() {
  const q = questionInput.value.trim();
  if (!q) return;
  const projectId = projectSelect.value;
  const anchor = anchorCheck.checked;
  const preferLlm = preferLlmCheck.checked;
  askBtn.disabled = true;
  askBtn.textContent = '生成中…';
  try {
    const r = await fetch('/api/qa', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ projectId, question: q, anchorOnChain: anchor, preferLlm })
    });
    const d = await r.json();
    renderAnswer(d, anchor);
  } catch (e) {
    answerArea.innerHTML = `<div class="text-rose-400 text-sm">请求失败：${e}</div>`;
  } finally {
    askBtn.disabled = false;
    askBtn.textContent = '提问';
  }
}

const TRUST_COLOR = { official: '#10b981', market: '#38bdf8', news: '#f59e0b', community: '#a78bfa', ai: '#94a3b8' };
const CONFIDENCE_LABEL = { high: '高', medium: '中', low: '低' };
const CONFIDENCE_COLOR = { high: '#10b981', medium: '#f59e0b', low: '#94a3b8' };

function renderAnswer(d, anchored) {
  const ocHtml = anchored && d.onChain ? `
    <div class="mt-3 p-3 rounded-lg bg-indigo-900/20 border border-indigo-800/40 text-xs">
      <div class="text-indigo-300 font-semibold"><i class="fa fa-link"></i> 链上存证</div>
      <div class="font-mono text-slate-500 text-[10px] break-all mt-1">tx: ${d.onChain.txHash || '-'}</div>
      <div class="font-mono text-slate-500 text-[10px] break-all">hash: ${d.onChain.evidenceHash || '-'}</div>
      <a href="/proof?hash=${d.onChain.evidenceHash}" class="mt-1 inline-block text-indigo-300 hover:underline">→ 验证</a>
    </div>
  ` : '';
  const llmTag = d.llmUsed ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900/40 text-emerald-300">LLM ${d.llmModel || ''}</span>` : `<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/30 text-amber-300">本地引擎</span>`;
  const citationsHtml = (d.citations || []).map(c => {
    const color = TRUST_COLOR[c.trustLevel] || '#94a3b8';
    return `
      <div class="border-l-2 pl-3 py-1" style="border-color: ${color}">
        <div class="flex items-center gap-2 text-[10px]">
          <span class="px-1.5 py-0.5 rounded" style="background: ${color}33; color: ${color}">${c.trustLevel}</span>
          <span class="text-slate-400">${c.docType} · ${c.version}</span>
        </div>
        <div class="text-slate-200 text-sm mt-0.5">${c.title}</div>
        <div class="text-slate-500 text-xs mt-1 line-clamp-2">${c.excerpt}</div>
      </div>
    `;
  }).join('');
  const confColor = CONFIDENCE_COLOR[d.confidence] || '#94a3b8';
  const html = `
    <div class="bg-slate-900/70 border border-slate-800 rounded-2xl p-5">
      <div class="text-slate-500 text-xs">Q · ${d.question}</div>
      <div class="mt-2 flex items-center gap-2 text-xs">
        <span class="px-2 py-0.5 rounded" style="background: ${confColor}33; color: ${confColor}">置信度 ${CONFIDENCE_LABEL[d.confidence] || d.confidence}</span>
        ${llmTag}
      </div>
      <div class="mt-3 text-slate-100 text-sm whitespace-pre-wrap leading-relaxed">${d.conclusion}</div>
      <div class="mt-3 text-xs text-slate-500"><b>推理：</b>${d.reasoning || ''}</div>
      ${(d.risks && d.risks.length) ? `<div class="mt-2 text-xs text-amber-300"><b>风险提示：</b><ul class="list-disc pl-5 mt-1">${d.risks.map(r => `<li>${r}</li>`).join('')}</ul></div>` : ''}
      ${citationsHtml ? `<div class="mt-4"><div class="text-xs text-slate-500 mb-2">引用来源（${d.citations.length}）</div><div class="space-y-2">${citationsHtml}</div></div>` : ''}
      ${d.suggestedFollowups && d.suggestedFollowups.length ? `<div class="mt-3 flex flex-wrap gap-1 text-xs">${d.suggestedFollowups.map(s => `<button class="followupBtn px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded">${s}</button>`).join('')}</div>` : ''}
      ${ocHtml}
    </div>
  `;
  answerArea.insertAdjacentHTML('afterbegin', html);
  document.querySelectorAll('.followupBtn').forEach(b => {
    b.addEventListener('click', () => { questionInput.value = b.textContent.trim(); ask(); });
  });
}
