"use strict";

const $ = (id) => document.getElementById(id);
const ui = {
  app: $("app"), list: $("problem-list"), search: $("search"), filters: $("filters"),
  topic: $("topic-filter"), level: $("level-filter"),
  count: $("problem-count"), progress: $("progress"), progressCount: $("progress-count"),
  body: $("problem-body"), prompt: $("prompt-tab"), solution: $("solution-tab"),
  editor: $("editor"), highlight: $("highlight"), numbers: $("line-numbers"),
  runtime: $("runtime"), name: $("file-name"), save: $("save-status"), reset: $("reset"),
  run: $("run"), submit: $("submit"), results: $("results"), connection: $("connection"),
};

function element(tag, classes, value) {
  const node = document.createElement(tag);
  if (classes) node.className = classes;
  if (value !== undefined) node.textContent = value;
  return node;
}

const STORE_KEY = "gradient-lab-v1";
const usesBrowserJudge = document.documentElement.dataset.judge === "browser";
function readProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY));
    if (saved && typeof saved.drafts === "object" && saved.drafts && Array.isArray(saved.solved)) return saved;
  } catch {
    // Practice stays available in browsers with storage disabled.
  }
  return { drafts: {}, solved: [], last: null };
}

const saved = readProgress();
const results = new Map();
let problems = [];
let current;
let filter = "全部";
let tab = "prompt";
let showingSolution = false;
let running = null;
let browserWorker = null;

const topicAliases = {
  张量基础: "张量与数值", 损失函数: "损失与评估", 多模态: "损失与评估",
  Attention: "Transformer 与解码", 流式记忆: "数据与流式系统",
};

function topicFor(problem) {
  return topicAliases[problem.topic] ?? problem.topic;
}

function prepareFilters() {
  for (const topic of new Set(problems.map(topicFor))) {
    ui.topic.add(new Option(topic, topic));
  }
  for (const button of ui.filters.querySelectorAll("button:not([data-filter='全部'])")) {
    button.hidden = !problems.some((problem) => problem.runtime === button.dataset.filter);
  }
}

function persist() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(saved));
    ui.save.textContent = "草稿自动保存";
  } catch {
    ui.save.textContent = "浏览器存储不可用";
  }
}

function renderLibrary() {
  const term = ui.search.value.trim().toLowerCase();
  const matching = problems.filter((p) => (filter === "全部" || p.runtime === filter) &&
    (!ui.topic.value || topicFor(p) === ui.topic.value) && (!ui.level.value || p.level === ui.level.value) &&
    [p.title, p.topic, topicFor(p), p.runtime, p.level, p.summary].join(" ").toLowerCase().includes(term));
  ui.count.textContent = (matching.length === problems.length ? matching.length : matching.length + " / " + problems.length) + " 题";
  ui.list.replaceChildren();
  for (const problem of matching) {
    const done = saved.solved.includes(problem.id);
    const item = element("button", "problem-link");
    item.type = "button";
    if (problem === current) item.setAttribute("aria-current", "page");
    const status = element("span", "problem-index" + (done ? " complete" : ""), done ? "✓" : "○");
    status.setAttribute("aria-label", done ? "已完成" : "未完成");
    const label = element("span");
    label.append(element("span", "problem-title", problem.title),
      element("span", "problem-meta", problem.runtime + " · " + problem.level));
    item.append(status, label);
    item.onclick = () => select(problem.id);
    ui.list.append(item);
  }
  if (!matching.length) ui.list.append(element("p", "quiet", "没有匹配的题目。"));
  const completed = problems.filter((p) => saved.solved.includes(p.id)).length;
  ui.progress.max = problems.length || 1;
  ui.progress.value = completed;
  ui.progressCount.textContent = completed + " / " + problems.length;
}

const difficulty = { 入门: "easy", 进阶: "medium", 挑战: "hard" };

function renderProblem() {
  ui.prompt.setAttribute("aria-selected", String(tab === "prompt"));
  ui.solution.setAttribute("aria-selected", String(tab === "solution"));
  ui.body.setAttribute("aria-labelledby", tab === "prompt" ? ui.prompt.id : ui.solution.id);

  const pills = element("div", "pills");
  pills.append(element("span", "pill " + difficulty[current.level], current.level),
    element("span", "pill", current.topic));
  if (saved.solved.includes(current.id)) pills.append(element("span", "pill easy", "已通过"));
  ui.body.replaceChildren(pills, element("h2", "", current.title));

  if (tab === "solution") {
    if (showingSolution) {
      ui.body.append(element("p", "", current.explanation), element("pre", "example", current.solution));
    } else {
      const reveal = element("button", "reveal", "显示参考代码");
      reveal.onclick = () => {
        showingSolution = true;
        renderProblem();
      };
      ui.body.append(reveal);
    }
  } else {
    const rules = element("ul");
    for (const rule of current.rules) rules.append(element("li", "", rule));
    const hint = element("details", "hint");
    hint.append(element("summary", "", "查看提示"), element("p", "", current.hint));
    ui.body.append(element("p", "", current.summary), element("h3", "", "要求"), rules,
      element("h3", "", "示例"), element("pre", "example", current.example), hint);
  }
  ui.body.scrollTop = 0;
}

const tokens = /#[^\n]*|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|\b(?:from|import|as|def|class|return|pass|if|elif|else|for|while|in|not|and|or|is|with|raise|continue|break|True|False|None|try|except|yield|lambda)\b|\b\d+(?:\.\d+)?(?:e-?\d+)?\b/g;
function syncScroll() {
  ui.highlight.scrollTop = ui.editor.scrollTop;
  ui.highlight.scrollLeft = ui.editor.scrollLeft;
  ui.numbers.parentElement.scrollTop = ui.editor.scrollTop;
}

function paintCode() {
  const source = ui.editor.value;
  const fragment = document.createDocumentFragment();
  let offset = 0;
  for (const match of source.matchAll(tokens)) {
    const word = match[0];
    const kind = word[0] === "#" ? "comment" : /^['"]/.test(word) ? "string" : /^\d/.test(word) ? "number" : "key";
    fragment.append(source.slice(offset, match.index), element("span", "token-" + kind, word));
    offset = match.index + word.length;
  }
  fragment.append(source.slice(offset), "\n");
  ui.highlight.replaceChildren(fragment);
  ui.numbers.textContent = source.split("\n").map((_, i) => i + 1).join("\n");
  syncScroll();
}

function onEdit() {
  if (!current) return;
  saved.drafts[current.id] = ui.editor.value;
  persist();
  paintCode();
}

function renderActions() {
  ui.run.disabled = ui.submit.disabled = !current || Boolean(running);
  ui.reset.disabled = !current || running?.id === current.id;
  ui.editor.disabled = !current;
}

function renderResults() {
  if (!current) return;

  const id = current.id;
  const result = results.get(id);
  ui.results.replaceChildren();
  if (running?.id === id) {
    const message = running.loading ? "首次加载浏览器 Python 环境，随后会自动执行测试…"
      : "正在执行 " + current.runtime + " 测试…";
    ui.results.append(element("p", "quiet", message));
    return;
  }
  if (!result) {
    ui.results.append(element("p", "quiet", "运行执行 " + current.previews.length +
      " 个公开用例。提交执行全部 " + current.total + " 个用例。"));
    return;
  }

  if (result.error) {
    ui.results.append(element("p", "result-heading fail", "运行错误"),
      element("pre", "problem-error", result.error));
  } else {
    const pass = result.passed === result.total;
    const action = result.mode === "submit" ? "提交" : "运行";
    ui.results.append(element("p", "result-heading " + (pass ? "pass" : "fail"),
      action + (pass ? "通过" : "未通过") + " · " + result.passed + " / " + result.total));
    for (const test of result.tests) {
      const line = element("details", "test-case " + (test.ok ? "pass" : "fail"));
      const title = element("summary");
      title.append(element("span", "case-mark", test.ok ? "✓" : "×"), test.name,
        element("span", "timing", test.ms + " ms"));
      line.open = !test.ok;
      line.append(title, element("pre", "", test.error || "输出符合预期。"));
      ui.results.append(line);
    }
  }
  if (result.log) {
    const log = element("details", "test-case log");
    log.append(element("summary", "", "标准输出"), element("pre", "", result.log));
    ui.results.append(log);
  }
}

function select(id) {
  const problem = problems.find((p) => p.id === id);
  if (!problem || (problem === current && ui.editor.value)) return;
  current = problem;
  saved.last = id;
  persist();
  history.replaceState(null, "", "#" + id);
  tab = "prompt";
  showingSolution = false;
  ui.name.textContent = id.replaceAll("-", "_") + ".py";
  ui.runtime.textContent = problem.runtime;
  ui.editor.value = saved.drafts[id] ?? problem.starter;
  ui.editor.setSelectionRange(0, 0);
  ui.editor.scrollTop = ui.editor.scrollLeft = 0;
  paintCode();
  renderLibrary();
  renderProblem();
  renderResults();
  renderActions();
}

async function run(mode) {
  if (!current || running) return;
  const problem = current;
  const id = problem.id;
  running = { id, loading: usesBrowserJudge && !browserWorker };
  renderActions();
  renderResults();
  const payload = { id, mode, code: ui.editor.value };
  try {
    if (payload.code.length > 40000) throw new Error("代码超过 40,000 字符。");
    const result = usesBrowserJudge ? await runInBrowser(payload, problem) : await runLocally(payload);
    results.set(id, { ...result, mode });
    if (mode === "submit" && result.total > 0 && result.passed === result.total && !saved.solved.includes(id)) {
      saved.solved.push(id);
      persist();
      renderLibrary();
      if (current.id === id) renderProblem();
    }
  } catch (error) {
    results.set(id, { error: error.message });
  } finally {
    running = null;
    renderActions();
    renderResults();
  }
}

async function runLocally(payload) {
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Gradient-Lab": "practice" },
      body: JSON.stringify(payload),
    });
    return await response.json();
  } catch {
    throw new Error("无法连接本地判题服务器。重新打开启动器后再试。");
  }
}

function runInBrowser(payload, problem) {
  return new Promise((resolve, reject) => {
    if (!browserWorker) browserWorker = new Worker("./judge-worker.js", { type: "module" });
    const worker = browserWorker;
    let timer;
    function clear() {
      clearTimeout(timer);
      worker.onmessage = worker.onerror = null;
    }
    function fail(message) {
      clear();
      worker.terminate();
      browserWorker = null;
      reject(new Error(message));
    }
    timer = setTimeout(() => fail("浏览器 Python 加载超过 60 秒。请检查网络连接后重试。"), 60000);
    worker.onerror = () => fail("无法加载浏览器判题环境。请刷新页面或使用本机版。");
    worker.onmessage = ({data}) => {
      if (data.phase === "ready") {
        running.loading = false;
        renderResults();
        clearTimeout(timer);
        timer = setTimeout(() => fail("运行超过 15 秒，判题进程已停止。"), 15000);
      } else if (data.error) {
        fail(data.error);
      } else if (data.result) {
        clear();
        resolve(data.result);
      }
    };
    worker.postMessage({ payload, problem });
  });
}

ui.search.addEventListener("input", renderLibrary);
ui.topic.addEventListener("change", renderLibrary);
ui.level.addEventListener("change", renderLibrary);
ui.filters.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  filter = button.dataset.filter;
  for (const candidate of ui.filters.querySelectorAll("button")) {
    candidate.setAttribute("aria-pressed", String(candidate === button));
  }
  renderLibrary();
});
for (const button of ui.app.querySelectorAll(".compact-nav button")) {
  button.onclick = () => {
    ui.app.dataset.view = button.dataset.view;
    for (const sibling of button.parentElement.querySelectorAll("button")) {
      sibling.setAttribute("aria-pressed", String(sibling === button));
    }
  };
}
ui.prompt.onclick = () => { if (current) { tab = "prompt"; renderProblem(); } };
ui.solution.onclick = () => { if (current) { tab = "solution"; renderProblem(); } };
ui.editor.addEventListener("input", onEdit);
ui.editor.addEventListener("scroll", syncScroll);
ui.run.onclick = () => run("run");
ui.submit.onclick = () => run("submit");
ui.reset.onclick = () => {
  if (!current || !window.confirm("将这题的草稿恢复为初始模板？")) return;
  delete saved.drafts[current.id];
  results.delete(current.id);
  ui.editor.value = current.starter;
  ui.editor.setSelectionRange(0, 0);
  persist();
  paintCode();
  renderResults();
  ui.editor.focus();
};

ui.editor.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    run(event.shiftKey ? "submit" : "run");
    return;
  }
  if (event.isComposing || event.metaKey || event.ctrlKey || event.altKey) return;
  const start = ui.editor.selectionStart;
  const end = ui.editor.selectionEnd;
  if (event.key === "Tab" && !event.shiftKey) {
    event.preventDefault();
    ui.editor.setRangeText("    ", start, end, "end");
    onEdit();
  } else if (event.key === "Enter" && start === end) {
    const before = ui.editor.value.slice(0, start).split("\n").at(-1);
    const padding = before.match(/^\s*/)[0];
    const indent = before.trimEnd().endsWith(":") ? "    " : "";
    if (padding || indent) {
      event.preventDefault();
      ui.editor.setRangeText("\n" + padding + indent, start, end, "end");
      onEdit();
    }
  }
});

async function start() {
  try {
    if (usesBrowserJudge) ui.connection.replaceChildren(element("span"), "浏览器判题");
    const response = await fetch(usesBrowserJudge ? "./questions.json" : "/api/problems");
    if (!response.ok) throw new Error();
    problems = await response.json();
    prepareFilters();
    const preferred = [location.hash.slice(1), saved.last].find((id) => problems.some((p) => p.id === id));
    select(preferred || "masked-attention");
  } catch {
    ui.connection.classList.add("offline");
    ui.connection.replaceChildren(element("span"), "连接失败");
    const message = usesBrowserJudge ? "题库加载失败。请稍后刷新页面。" : "题库加载失败。请确认本地服务已启动，再刷新页面。";
    ui.body.replaceChildren(element("p", "quiet", message));
  } finally {
    ui.app.setAttribute("aria-busy", "false");
  }
}

start();
