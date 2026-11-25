/* ============================================================
   学迹 · 初中学习档案 — 纯静态前端（无构建依赖）
    数据：data/index.json（契约 v1.5 schema）+ data/ 下的图片与讲解 md
   路由（hash）：
     #/                     学习近况 · 数据叙事 + 里程碑 + 最近讲解/切题
     #/growth               成长 · 月度活动 / 知识覆盖 / 科目与错题结构 / 学习阶梯
     #/teach                讲解查阅 · 题目列表（?subject=&expl=&kp=&kw=&sort=）
     #/teach/q/<id>         题目详情（题图 + OCR + 讲解 md + v1/v2）
     #/crop                 切题库 · 按日期会话列表
     #/crop/s/<session>     会话内题目网格
     #/crop/s/<session>/<i> 单题大图
      #/accum                积累册 · 按册列表
      #/accum/b/<name>       积累册阅读（iframe 内嵌书 html，书名 encodeURIComponent）
      #/kp                   知识点 · 受控概念列表（按科目分组）
      #/kp/c/<concept>       概念页 · 该概念下的题目（概念名 encodeURIComponent）
    ============================================================ */
(() => {
  'use strict';

  var DATA_URL = 'data/index.json';

  var CONTRACT_VERSION = 'v1.5';

  var CONTRACT_COMPAT_VERSIONS = ['v1.5', 'v1.4'];

  /* 切题库附图的最小展示边长（px，按图片实际加载尺寸计，原图像素量级）：
     YOLO 偶把手写笔迹误检成 figure，产出极小附图（主会话实测 95×42、92×58 原图 px），
     而真实附图都是数百 px 量级（样本实测最小 439px）——100 落在两档之间，
     最小边低于此值的附图判定为误报，加载后摘除、不展示。 */
  var FIG_MIN_SIDE = 100;

  var SUBJECT_CN = { math: '数学', physics: '物理', chemistry: '化学', biology: '生物', english: '英语', chinese: '语文' };
  var SUBJECT_SEAL = { math: '数', physics: '理', chemistry: '化', biology: '生', english: '英', chinese: '语' };

  /* 模块注册表：二期模块在此登记，置 enabled:true 即出现在导航与首页。
     v1.5.0 起重排：近况/成长（体验）在前，讲解查阅/切题库/积累册/知识点（档案）在后；
     label 为宽屏全标签，short 为窄屏短标签（<560px 时由 CSS 切换，防六项撑破 390）。 */
  var MODULES = [
    { id: 'home',   path: '/',       label: '近况',     short: '近况',   enabled: true },
    { id: 'growth', path: '/growth', label: '成长',     short: '成长',   enabled: true },
    { id: 'teach',  path: '/teach',  label: '讲解查阅', short: '讲解',   enabled: true },
    { id: 'crop',   path: '/crop',   label: '切题库',   short: '切题',   enabled: true },
    { id: 'accum',  path: '/accum',  label: '积累册',   short: '积累册', enabled: true },
    { id: 'plot',   path: '/plot',   label: '绘图库',   short: '绘图',   enabled: false },
    { id: 'kp',     path: '/kp',     label: '知识点',   short: '知识点', enabled: true },
    { id: 'review', path: '/review', label: '复习路径', short: '复习',   enabled: false }
  ];

  var state = {
    data: null,
    explCache: {},
    explSel: {},
    filters: { subject: 'all', expl: 'all', kps: {}, kw: '', sort: 'new' },
    kpSearch: '',
    qIndex: {},
    route: { path: '/', query: {} },
    contractMismatch: false,
    booted: false
  };

  var $app = document.getElementById('app');
  var $tabs = document.getElementById('tabs');
  var $footMeta = document.getElementById('foot-meta');
  var $themeBtn = document.getElementById('theme-btn');
  var $themeLabel = document.getElementById('theme-btn-label');

  /* ------------------------------------------------ 工具 */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function subjCN(s) { return SUBJECT_CN[s] || s || '未知'; }
  function subjSeal(s) { return SUBJECT_SEAL[s] || '其'; }
  function sealCls(s) { return SUBJECT_SEAL[s] ? '' : ' other'; }

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function fmtDT(s) {
    if (!s) return '';
    var m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    return m ? m[2] + '-' + m[3] + ' ' + m[4] + ':' + m[5] : String(s);
  }
  function fmtDay(s) {
    var m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? m[2] + '-' + pad2(parseInt(m[3], 10)) : String(s || '');
  }
  function fmtDateCN(d) {
    var m = String(d || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return m ? parseInt(m[2], 10) + '月' + parseInt(m[3], 10) + '日' : String(d || '');
  }
  function fmtDateTimeCN(s) {
    var m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    return m ? parseInt(m[2], 10) + '月' + parseInt(m[3], 10) + '日 ' + m[4] + ':' + m[5] : String(s || '');
  }
  function fmtTimeCN(s) {
    var m = String(s || '').match(/[T ](\d{2}):(\d{2})/);
    return m ? m[1] + ':' + m[2] : String(s || '');
  }
  function clampText(s, n) {
    s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
    return s.length > n ? s.slice(0, n) + '…' : s;
  }
  /* 数字统一走等宽刻度（档案坐标），不放大成装饰大字 */
  function num(n) { return '<span class="num">' + n + '</span>'; }

  /* ------------------------------------------------ Markdown 渲染（先转义再转换，防 XSS） */

  var EMOJI_HEADS = ['🎯', '🧠', '✍️', '💡', '⚠️', '📎', '📌', '🔍', '📖', '📝', '🧩', '🔑'];

  function inlineMD(s) {
    s = s.replace(/`([^`\n]+)`/g, function (m, c) { return '<code>' + c + '</code>'; });
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    s = s.replace(/~~([^~]+)~~/g, '<del>$1</del>');
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    return s;
  }

  /* 解析 md 头部的 HTML 注释元信息，返回 {meta, body} */
  function splitExplMeta(src) {
    var s = String(src == null ? '' : src);
    var meta = {};
    var re = /<!--\s*([\s\S]*?)-->/g, m;
    while ((m = re.exec(s)) !== null) {
      var line = m[1];
      var ver = line.match(/版本[::]\s*(v\d+)/);
      if (ver) meta.version = ver[1];
      var gen = line.match(/生成时间[::]\s*([0-9T:\-.Z]+)/);
      if (gen) meta.generated_at = gen[1];
      var mdl = line.match(/模型[::]\s*([\w.\-]+)/);
      if (mdl) meta.model = mdl[1];
      var idm = line.match(/(?:条目\s*)?id\s*[::]\s*(\d+)/);
      if (idm) meta.id = idm[1];
      var ocr = line.match(/ocr_verified\s*=\s*(\d)/);
      if (ocr) meta.ocr_verified = ocr[1];
    }
    s = s.replace(/<!--[\s\S]*?-->/g, '');
    return { meta: meta, body: s };
  }

  /* 结尾的「**元信息**：id=… · 学科=… …」整理成档案注记。
     题号 / 学科 / 年级页面上已有，注记只留版本、体量、耗时与 provenance。 */
  function normalizeNote(line) {
    var out = {};
    String(line).split('·').forEach(function (p) {
      p = p.trim();
      if (!p) return;
      var m = p.match(/^([^=:]+)[=:]\s*(.+)$/);
      if (!m) { out[p] = ''; return; }
      var k = m[1].trim(), v = m[2].trim();
      if (k === '学科') v = subjCN(v);
      else if (k === '字数') v = v + ' 字';
      else if (k === '耗时') v = v + ' 秒';
      else if (k === '生成时间') v = fmtDT(v);
      out[k] = v;
    });
    return out;
  }

  var NOTE_DROP = { id: 1, 学科: 1, 年级: 1 };

  function noteHtml(noteObj, meta) {
    var parts = [];
    var keys = Object.keys(noteObj);
    keys.forEach(function (k) {
      if (NOTE_DROP[k]) return;
      var v = noteObj[k];
      parts.push(v ? '<span class="np"><span class="k">' + esc(k) + '</span>' + esc(v) + '</span>'
                   : '<span class="np">' + esc(k) + '</span>');
    });
    if (!parts.length) return '';
    return '<p class="md-note">' + parts.join('<span class="np k">·</span>') + '</p>';
  }

  function renderMarkdown(src) {
    var split = splitExplMeta(src);
    var s = split.body;
    var blocks = [];
    s = s.replace(/```[\w-]*\n([\s\S]*?)```/g, function (m, code) {
      blocks.push('<pre><code>' + esc(code.replace(/\n$/, '')) + '</code></pre>');
      return '\u0000' + (blocks.length - 1) + '\u0000';
    });
    s = esc(s);
    var lines = s.split('\n');
    var html = '', para = [], i = 0;
    var noteObj = null;

    function flushPara() {
      if (!para.length) return;
      html += '<p>' + para.join('<br>') + '</p>';
      para = [];
    }
    function parseRow(r) {
      return r.trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); });
    }

    while (i < lines.length) {
      var line = lines[i];
      var ph = line.match(/^\u0000(\d+)\u0000$/);
      if (ph) { flushPara(); html += blocks[+ph[1]]; i++; continue; }
      var h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        flushPara();
        var lvl = h[1].length, txt = h[2];
        /* 一级标题与页面头部（编号/科目/年级/知识点）完全重复，页面已承载，这里不再渲染 */
        if (lvl > 1) {
          html += '<h' + lvl + ' class="md-h">' + txt + '</h' + lvl + '>';
        }
        i++; continue;
      }
      if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) { flushPara(); html += '<hr>'; i++; continue; }
      if (/^\s*>\s?/.test(line)) {
        flushPara();
        var quote = [];
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) { quote.push(lines[i].replace(/^\s*>\s?/, '')); i++; }
        html += '<blockquote>' + quote.join('<br>') + '</blockquote>';
        continue;
      }
      if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
        flushPara();
        var heads = parseRow(lines[i]);
        i += 2;
        var rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(parseRow(lines[i])); i++; }
        html += '<table><thead><tr>' + heads.map(function (c) { return '<th>' + c + '</th>'; }).join('') +
          '</tr></thead><tbody>' +
          rows.map(function (r) {
            return '<tr>' + r.map(function (c) { return '<td>' + c + '</td>'; }).join('') + '</tr>';
          }).join('') +
          '</tbody></table>';
        continue;
      }
      var noteM = line.match(/^\*\*元信息\*\*\s*[：:]\s*(.+)$/);
      if (noteM) { flushPara(); noteObj = normalizeNote(noteM[1]); i++; continue; }
      var ulm = line.match(/^\s*[-*+]\s+(.*)$/);
      var olm = line.match(/^\s*\d+[.、]\s*(.*)$/);
      if (ulm || olm) {
        flushPara();
        var ordered = !!olm;
        var tag = ordered ? 'ol' : 'ul';
        var items = [];
        while (i < lines.length) {
          var m2 = lines[i].match(ordered ? /^\s*\d+[.、]\s*(.*)$/ : /^\s*[-*+]\s+(.*)$/);
          if (!m2) break;
          items.push(m2[1]);
          i++;
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*+]|\d+[.、])\s/.test(lines[i])) {
            items[items.length - 1] += '<br>' + lines[i].trim();
            i++;
          }
        }
        html += '<' + tag + '>' + items.map(function (t) { return '<li>' + t + '</li>'; }).join('') + '</' + tag + '>';
        continue;
      }
      var em = null;
      for (var e = 0; e < EMOJI_HEADS.length; e++) {
        if (line.trim().indexOf(EMOJI_HEADS[e]) === 0 && line.trim().length <= 34) { em = line.trim(); break; }
      }
      if (em) { flushPara(); html += '<p class="md-h">' + em + '</p>'; i++; continue; }
      if (line.trim() === '') { flushPara(); i++; continue; }
      para.push(inlineMD(line.trim()));
      i++;
    }
    flushPara();

    /* 题名中的学科代码换成中文 */
    html = html.replace(/(<h1[^>]*>)([\s\S]*?)(<\/h1>)/, function (m, a, b, c) {
      return a + b.replace(/\b(math|physics|chemistry|biology|english|chinese)\b/g, function (x) { return subjCN(x); }) + c;
    });

    if (!noteObj) {
      var meta = split.meta;
      if (meta.version || meta.generated_at || meta.model || meta.ocr_verified) {
        noteObj = {};
        if (meta.version) noteObj['版本'] = meta.version;
        if (meta.generated_at) noteObj['生成于'] = fmtDT(meta.generated_at);
        if (meta.model) noteObj['模型'] = meta.model;
        if (meta.ocr_verified === '1') noteObj['转录已校验'] = '';
      }
    }
    /* md 自带「元信息」行时，把注释头里的 provenance（生成时间/模型）补进去 */
    if (noteObj) {
      var cm = split.meta;
      if (cm.generated_at && noteObj['生成于'] === undefined) noteObj['生成于'] = fmtDT(cm.generated_at);
      if (cm.model && noteObj['模型'] === undefined) noteObj['模型'] = cm.model;
      if (cm.ocr_verified === '1' && noteObj['转录已校验'] === undefined) noteObj['转录已校验'] = '';
    }
    var note = noteHtml(noteObj, split.meta);
    if (note) html += note;
    return html;
  }

  /* ------------------------------------------------ 数据加载 */

  function fetchData() {
    return fetch(DATA_URL, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }
  function fetchExpl(qid, version) {
    var key = qid + '|' + version;
    if (state.explCache[key] !== undefined) return Promise.resolve(state.explCache[key]);
    var entry = null;
    (state.data.explanations || []).forEach(function (x) {
      if (x.id === qid && x.version === version) entry = x;
    });
    if (!entry) return Promise.resolve(null);
    return fetch('data/' + entry.file, { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (txt) { state.explCache[key] = txt; return txt; });
  }

  function buildIndex() {
    state.qIndex = {};
    (state.data.questions || []).forEach(function (q) { state.qIndex[q.id] = q; });
  }
  function qById(id) { return state.qIndex[id] || null; }

  /* ------------------------------------------------ 派生统计（v1.5.0 近况/成长共用）
     契约 v1.3：月度序列、知识覆盖、科目分布、做错时段、里程碑全部由前端从既有字段现算
     （questions[].created_at / do_time / knowledge_points、explanations[].generated_at、
     crop_sessions[].date）；只有 error_type、stats.review_backlog、stats.crop_figures
     三个新字段来自同步脚本，缺失时对应区块整体不渲染（不摆 0、不摆空框）。
     mastery / resolved / review_count 不参与任何视图渲染。 */

  var CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二'];

  /* 口语计数：月数用「两」，里程碑印文与时刻用「二/十/二十」 */
  function cnCount(n) { return n === 2 ? '两' : (n > 0 && n < 10 ? CN_NUM[n] : String(n)); }
  function cnNum(n) {
    if (n < 10) return CN_NUM[n];
    if (n === 10) return '十';
    if (n < 20) return '十' + CN_NUM[n - 10];
    var r = n % 10;
    return CN_NUM[Math.floor(n / 10)] + '十' + (r ? CN_NUM[r] : '');
  }

  function dayOf(s) {
    var m = String(s || '').match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : null;
  }
  function monthOf(s) {
    var m = String(s || '').match(/^(\d{4}-\d{2})/);
    return m ? m[1] : null;
  }
  function hourOf(s) {
    var m = String(s || '').match(/[T ](\d{2}):(\d{2})/);
    return m ? parseInt(m[1], 10) : null;
  }
  function dayDiff(a, b) {  /* b - a，整天；本地日期运算，避开时区位移 */
    var pa = a.split('-'), pb = b.split('-');
    return Math.round((new Date(+pb[0], +pb[1] - 1, +pb[2]) - new Date(+pa[0], +pa[1] - 1, +pa[2])) / 86400000);
  }
  function sortedQuestions() {
    return (state.data.questions || []).slice().sort(function (a, b) {
      return String(a.created_at || '').localeCompare(String(b.created_at || ''));
    });
  }

  /* 本周 = 以最近一条入库日期为锚点的最近 7 个自然日（含锚点日）；
     上周 = 再往前 7 天。锚点取数据里的最新入库日，不用浏览器当天，
     这样旧数据（还没同步）也有一句真话可说。 */
  function weekIntake() {
    var days = {};
    (state.data.questions || []).forEach(function (q) {
      var d = dayOf(q.created_at);
      if (d) days[d] = (days[d] || 0) + 1;
    });
    var keys = Object.keys(days).sort();
    if (!keys.length) return null;
    var anchor = keys[keys.length - 1], cur = 0, prev = 0;
    keys.forEach(function (d) {
      var off = dayDiff(anchor, d);
      if (off >= -6) cur += days[d];
      else if (off >= -13) prev += days[d];
    });
    return { cur: cur, prev: prev, anchor: anchor };
  }

  function periodWord(h) {
    if (h < 6) return '凌晨';
    if (h < 12) return '上午';
    if (h < 14) return '中午';
    if (h < 18) return '下午';
    return '晚上';
  }
  /* 做错时段：do_time 小时分布的 3 小时连续滑动窗取最高一段（不跨零点绕回） */
  function eveningStats() {
    var hours = [], i;
    for (i = 0; i < 24; i++) hours.push(0);
    var withTime = 0;
    (state.data.questions || []).forEach(function (q) {
      var h = hourOf(q.do_time);
      if (h === null || h < 0 || h > 23) return;
      withTime++;
      hours[h]++;
    });
    if (!withTime) return null;
    var bestFrom = 0, bestN = -1;
    for (i = 0; i <= 21; i++) {
      var n = hours[i] + hours[i + 1] + hours[i + 2];
      if (n > bestN) { bestN = n; bestFrom = i; }
    }
    return { withTime: withTime, evening: bestN, fromHour: bestFrom, toHour: bestFrom + 3 };
  }
  /* 口语时刻按十二时辰说法（20:00 → 八点、23:00 → 十一点、0:00 → 十二点），
     与等宽刻度「20:00 到 23:00」同指一段，只是说法不同。 */
  function cnHour12(h) { var v = ((h % 12) + 12) % 12; return v === 0 ? '十二' : CN_NUM[v]; }
  function spokenRange(fromHour, toHour) {
    return periodWord(fromHour) + cnHour12(fromHour) + '点到' +
      (toHour >= 24 ? '零点' : cnHour12(toHour) + '点');
  }

  /* 最硬骨头：原始知识点标签计数最高的一条（口径 = questions[].knowledge_points） */
  function topKnowledge() {
    var c = kpCounts(), best = null;
    Object.keys(c).forEach(function (k) {
      if (!best || c[k] > c[best] || (c[k] === c[best] && k.localeCompare(best, 'zh') < 0)) best = k;
    });
    return best ? { name: best, n: c[best] } : null;
  }

  function explainedCount() {
    return (state.data.questions || []).filter(function (q) { return q.has_explanation; }).length;
  }

  /* 「这几个月」的口径：从第一道错题到数据更新日经历的月数（设计稿「三个月」同口径），
     与柱图里的月份格数（入过库的日历月数）不是一回事，页面两处各说各的。 */
  function spanMonths() {
    var qs = sortedQuestions();
    if (!qs.length) return 0;
    var first = dayOf(qs[0].created_at);
    var last = dayOf(state.data.generated_at) || dayOf(qs[qs.length - 1].created_at);
    if (!first || !last) return 0;
    return Math.max(1, Math.round(dayDiff(first, last) / 30));
  }

  /* 里程碑：按入库顺序数到第 50/100/150… 道盖一枚朱印（error_book_indexed 口径） */
  function cnMilestone(n) {
    var h = Math.floor(n / 100), r = n % 100, s = '';
    if (h) s += (h > 1 ? CN_NUM[h] : '') + '百';
    if (r === 50) s += '五十';
    return s;
  }
  function milestoneInfo() {
    var qs = sortedQuestions(), total = qs.length, step = 50;
    var done = Math.floor(total / step) * step;
    var info = { total: total, done: done, next: done + step, remaining: done + step - total };
    if (done) {
      info.doneDate = qs[done - 1].created_at;
      info.seal = cnMilestone(done);
      if (done - step >= step) {
        info.prev = done - step;
        info.prevDate = qs[info.prev - 1].created_at;
      }
    }
    return info;
  }

  /* 月度序列：入库/讲解/切题按 created_at | generated_at | date 归月；
     新增知识点按原始标签的 first-seen 月计。只收有入库的月份（柱图横轴就是入库），
     讲解或切题单独发生在无入库月份时不入列。 */
  function monthlySeries() {
    var byMonth = {};
    function slot(m) { return byMonth[m] || (byMonth[m] = { m: m, intake: 0, expl: 0, crops: 0, newTags: 0 }); }
    (state.data.questions || []).forEach(function (q) {
      var m = monthOf(q.created_at);
      if (m) slot(m).intake++;
    });
    (state.data.explanations || []).forEach(function (e) {
      var m = monthOf(e.generated_at);
      if (m) slot(m).expl++;
    });
    (state.data.crop_sessions || []).forEach(function (s) {
      var m = monthOf(s.date);
      if (m) slot(m).crops += (s.problems || []).length;
    });
    var firstSeen = {};
    sortedQuestions().forEach(function (q) {
      var m = monthOf(q.created_at);
      if (!m) return;
      (q.knowledge_points || []).forEach(function (k) {
        if (!k || firstSeen[k]) return;
        firstSeen[k] = m;
        slot(m).newTags++;
      });
    });
    var cum = 0;
    return Object.keys(byMonth).filter(function (m) { return byMonth[m].intake > 0; }).sort().map(function (m) {
      var row = byMonth[m];
      cum += row.newTags;
      row.cum = cum;
      return row;
    });
  }

  function subjectCounts() {
    var c = {};
    (state.data.questions || []).forEach(function (q) { if (q.subject) c[q.subject] = (c[q.subject] || 0) + 1; });
    return Object.keys(c).map(function (s) {
      return { key: s, name: subjCN(s), seal: subjSeal(s), n: c[s] };
    }).sort(function (a, b) { return b.n - a.n || a.name.localeCompare(b.name, 'zh'); });
  }

  /* 错题归因（契约 v1.3 questions[].error_type）：自由文本，已知取值映射到档案用语，
     未知取值原样显示；一题都没打标签时返回 null，整个区块不渲染。 */
  var ERROR_TYPE_NAMES = {
    concept: '概念没吃透', '概念': '概念没吃透', '概念不清': '概念没吃透', '概念没吃透': '概念没吃透',
    method: '方法不会', '方法': '方法不会', '方法不会': '方法不会',
    calculation: '计算失误', '计算': '计算失误', '计算失误': '计算失误',
    misreading: '审题粗心', careless: '审题粗心', '审题': '审题粗心', '审题粗心': '审题粗心', '粗心': '审题粗心'
  };
  function errorTypeCounts() {
    var c = {}, order = [];
    (state.data.questions || []).forEach(function (q) {
      var v = q.error_type;
      if (v === undefined || v === null) return;
      var key = String(v).trim();
      if (!key) return;
      if (!c[key]) { c[key] = 0; order.push(key); }
      c[key]++;
    });
    if (!order.length) return null;
    var total = order.reduce(function (n, k) { return n + c[k]; }, 0);
    return {
      total: total,
      rows: order.map(function (k) {
        var name = ERROR_TYPE_NAMES[k] || k;
        return { raw: k, name: name, concept: name === '概念没吃透', n: c[k] };
      }).sort(function (a, b) { return b.n - a.n || a.raw.localeCompare(b.raw, 'zh'); })
    };
  }

  /* 复习到期账（契约 v1.3 stats.review_backlog）：同步脚本可能给标量（题数）或对象
     （含快照日与当天到期数），两种形态都消费；字段缺席返回 null，相关数字整体不显示。 */
  function reviewBacklog() {
    var rb = state.data.stats && state.data.stats.review_backlog;
    if (rb === undefined || rb === null) return null;
    if (typeof rb === 'object') {
      if (typeof rb.overdue !== 'number' || !isFinite(rb.overdue)) return null;
      return {
        overdue: rb.overdue,
        dueToday: typeof rb.due_today === 'number' && isFinite(rb.due_today) ? rb.due_today : null,
        snapshot: rb.snapshot_date || rb.snapshot || null
      };
    }
    if (typeof rb === 'number' && isFinite(rb)) return { overdue: rb, dueToday: null, snapshot: null };
    return null;
  }
  /* 切图总张数（契约 v1.3 stats.crop_figures，按张计）：只在场时披露，并说明与按月
     登记行（按会话内题数计）的口径差异。 */
  function cropFigures() {
    var v = state.data.stats && state.data.stats.crop_figures;
    return (typeof v === 'number' && isFinite(v)) ? v : null;
  }

  /* 月份注记：只写这个月最值得记的一句真话（首道 / 讲解最集中 / 收得最厚 / 切题） */
  function monthNote(m, maxExpl, peakIntake) {
    if (m.first) return '第一道错题收进档案，是 ' + fmtDateCN(m.firstDay) + '。';
    if (maxExpl > 0 && m.expl === maxExpl) return m.expl + ' 篇讲解在这个月写完。';
    if (peakIntake > 0 && m.intake === peakIntake) return '这个月收得最厚：' + m.intake + ' 道。';
    if (m.crops) return '从作业照片里切进 ' + m.crops + ' 道题。';
    return '';
  }

  /* ------------------------------------------------ 路由 */

  function parseHash() {
    var raw = location.hash.replace(/^#/, '') || '/';
    var qi = raw.indexOf('?');
    var path = qi >= 0 ? raw.slice(0, qi) : raw;
    var query = {};
    if (qi >= 0) {
      raw.slice(qi + 1).split('&').forEach(function (kv) {
        if (!kv) return;
        var i = kv.indexOf('=');
        var k = decodeURIComponent(i >= 0 ? kv.slice(0, i) : kv);
        var v = decodeURIComponent(i >= 0 ? kv.slice(i + 1) : '');
        if (v !== '') query[k] = v;
      });
    }
    return { path: path, parts: path.split('/').filter(Boolean), query: query };
  }

  function teachHref(extra) {
    var f = state.filters;
    var q = {};
    if (f.subject !== 'all') q.subject = f.subject;
    if (f.expl !== 'all') q.expl = f.expl;
    var kps = Object.keys(f.kps).filter(function (k) { return f.kps[k]; });
    if (kps.length) q.kp = kps.join(',');
    if (f.kw.trim()) q.kw = f.kw.trim();
    if (f.sort !== 'new') q.sort = f.sort;
    Object.keys(extra || {}).forEach(function (k) {
      var v = extra[k];
      if (v === null || v === undefined || v === '') delete q[k]; else q[k] = v;
    });
    var qs = Object.keys(q).map(function (k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(q[k]);
    }).join('&');
    return '#/teach' + (qs ? '?' + qs : '');
  }

  function syncFiltersFromRoute() {
    var q = state.route.query;
    var f = state.filters;
    f.subject = q.subject || 'all';
    f.expl = q.expl || 'all';
    f.kps = {};
    if (q.kp) q.kp.split(',').forEach(function (k) { if (k) f.kps[k] = true; });
    f.kw = q.kw || '';
    f.sort = q.sort === 'old' ? 'old' : 'new';
  }

  function setRoute(hash) {
    history.replaceState(null, '', hash);
    render();
  }

  /* ------------------------------------------------ 视图调度 */

  function render() {
    var route = parseHash();
    state.route = route;
    syncFiltersFromRoute();
    renderTabs(route);
    if (window.__closeLightbox) window.__closeLightbox();
    if (window.__closeSheet) window.__closeSheet(true);
    if (!state.data) { $app.innerHTML = '<div class="boot">正在读取档案…</div>'; return; }
    window.scrollTo(0, 0);
    var v = route.parts[0];
    var html = '';
    if (v === undefined) html = viewHome();
    else if (v === 'growth') html = viewGrowth();
    else if (v === 'teach') html = route.parts[1] === 'q' ? viewQuestion(parseInt(route.parts[2], 10)) : viewTeach();
    else if (v === 'crop') {
      if (route.parts[1] === 's') {
        html = route.parts[3] ? viewProblem(route.parts[2], parseInt(route.parts[3], 10))
                              : viewSession(decodeURIComponent(route.parts[2]));
      } else html = viewCrop();
    } else if (v === 'accum') {
      html = route.parts[1] === 'b'
        ? viewAccumBook(route.parts[2] ? decodeURIComponent(route.parts[2]) : '')
        : viewAccum();
    } else if (v === 'kp') {
      html = route.parts[1] === 'c'
        ? viewKpConcept(route.parts[2] ? decodeURIComponent(route.parts[2]) : '')
        : viewKp();
    } else html = viewHome();

    $app.innerHTML = html;
    var main = $app.firstElementChild;
    if (main) main.classList.add('route-in');
    wireView(v, route);
    if (state.booted) { try { $app.focus({ preventScroll: true }); } catch (e) {} }
  }

  function renderTabs(route) {
    var active = route.parts[0] || 'home';
    $tabs.innerHTML = MODULES.filter(function (m) { return m.enabled; }).map(function (m) {
      var cur = m.id === active ? ' aria-current="page"' : '';
      /* 窄屏（<560px）只显示短标签，宽屏显示全标签；两个 span 都在 DOM 里，由 CSS 切换 */
      return '<a href="#' + m.path + '"' + cur + '>' +
        '<span class="lb-short">' + esc(m.short || m.label) + '</span>' +
        '<span class="lb-full">' + esc(m.label) + '</span></a>';
    }).join('');
  }

  /* ------------------------------------------------ 首页 · 学习近况（v1.5.0 重构） */

  function recentExplanations(n) {
    var list = (state.data.explanations || []).slice();
    list.sort(function (a, b) { return String(b.generated_at || '').localeCompare(String(a.generated_at || '')); });
    var out = [], seen = {};
    for (var i = 0; i < list.length && out.length < n; i++) {
      var e = list[i];
      if (seen[e.id]) continue;
      seen[e.id] = true;
      var q = qById(e.id);
      if (q) out.push({ q: q, e: e });
    }
    return out;
  }

  function recentSessions(n) {
    return sortedSessions().slice(0, n);
  }

  function viewHome() {
    var d = state.data;
    var qs = d.questions || [];
    var html = dataNotices();

    if (!qs.length) {
      html += '<p class="empty">档案里还没有错题。等手机端同步一次就有数据了。</p>';
      var rs0 = recentSessions(3);
      if (rs0.length) html += secHead('最近切题', '#/crop') + rs0.map(sessionRow).join('');
      return html;
    }

    var total = qs.length;
    var explained = explainedCount();
    var noExpl = total - explained;
    var wk = weekIntake() || { cur: 0, prev: 0, anchor: null };
    var ev = eveningStats();
    var top = topKnowledge();
    var grade = qs[0].grade || '';
    var explLink = teachHref({ expl: 'no', subject: null, kp: null, kw: null, sort: null });

    /* 开篇三句：本周节奏 / 做错时段 / 最硬骨头与讲解覆盖。文案结构照设计稿，
       每个数字都由上面的派生函数现算，不写死。 */
    var lead = '<section class="home-lead"><h1 class="home-tag">' +
      (wk.cur > 0 ? '这一周，错题本又厚了 ' + num(wk.cur) + ' 道。'
                 : '这一周，错题本没有添新题。') + '</h1>';
    var note1 = wk.prev === wk.cur ? '和上周一样稳。'
      : (wk.prev === 0 ? '上周一道新题也没有，这周开始了。'
      : (wk.cur > wk.prev ? '比上周多 ' + num(wk.cur - wk.prev) + ' 道。'
                          : '比上周少 ' + num(wk.prev - wk.cur) + ' 道。'));
    if (ev) {
      note1 += (grade || '孩子') + '的节奏看起来是这样：' + spokenRange(ev.fromHour, ev.toHour) +
        '是错题高产时段——记下做题时间的 ' + num(ev.withTime) + ' 道题里，' + num(ev.evening) +
        ' 道发生在 ' + pad2(ev.fromHour) + ':00 到 ' + pad2(ev.toHour) + ':00。';
    }
    lead += '<p class="home-note">' + note1 + '</p>';

    var note2 = '';
    /* 最硬骨头：至少两条错题绕着同一个标签转，才够格叫「最硬的一根骨头」 */
    if (top && top.n >= 2) {
      note2 += '眼下最硬的一根骨头是<span class="quiet">「' + esc(top.name) + '」</span>：' +
        num(top.n) + ' 道错题都绕着它转。';
    }
    note2 += num(total) + ' 道错题里，' + num(explained) + ' 道已经讲明白了；' +
      (noExpl > 0 ? '<a href="' + explLink + '">还有 ' + noExpl + ' 道等着讲</a>。'
                  : '每一道都有讲解了。');
    lead += '<p class="home-note">' + note2 + '</p></section>';
    html += lead;

    /* 里程碑带：已达成印 + 下一枚进度 + 讲解覆盖发丝 gauge（真比例） */
    var ms = milestoneInfo();
    var pct = total ? (explained / total * 100) : 0;
    var band = '<section class="milestone">';
    if (ms.done) {
      band += '<div class="milestone-seal' + (ms.seal.length > 1 ? ' wide' : '') +
        '" aria-hidden="true">' + esc(ms.seal) + '</div>';
    }
    band += '<div class="milestone-main">';
    if (ms.done) {
      band += '<p class="milestone-t">第 ' + num(ms.done) + ' 道错题，' + esc(fmtDay(ms.doneDate)) + ' 收进档案。</p>' +
        '<p class="milestone-sub">' +
        (ms.prev ? '第 ' + ms.prev + ' 道是 ' + esc(fmtDay(ms.prevDate)) + '。' : '') +
        '下一枚印在第 ' + ms.next + ' 道——还差 ' + num(ms.remaining) + ' 道。</p>';
    } else {
      band += '<p class="milestone-t">已经收进 ' + num(total) + ' 道，第一枚印盖在第 ' + ms.next + ' 道。</p>' +
        '<p class="milestone-sub">还差 ' + num(ms.remaining) + ' 道。</p>';
    }
    band += '<div class="gauge-row">' +
      '<span class="gauge-label">讲解覆盖 ' + num(explained + ' / ' + total) + '</span>' +
      '<span class="gauge"><i style="width:' + pct.toFixed(1) + '%"></i></span>' +
      '<span class="gauge-label">' +
      (noExpl > 0 ? '<a href="' + explLink + '">还差 ' + noExpl + ' 道</a>' : '都讲完了') +
      '</span></div></div></section>';
    html += band;

    /* 最近讲解 / 最近切题退居辅助位（沿用档案行组件与缩略图） */
    var rec = recentExplanations(3);
    if (rec.length) {
      html += secHead('最近讲解', '#/teach');
      html += '<div class="rows">' + rec.map(function (r) {
        return questionRow(r.q, { summary: r.e && r.e.summary ? r.e.summary : '', thumb: true });
      }).join('') + '</div>';
    }
    var rs = recentSessions(2);
    if (rs.length) {
      html += secHead('最近切题', '#/crop');
      html += rs.map(sessionRow).join('');
    }

    var months = spanMonths();
    if (months) {
      html += '<p class="crosslink">这' + cnCount(months) + '个月是怎么长过来的？' +
        '<a href="#/growth">看看成长记录</a>。</p>';
    }
    return html;
  }

  /* ------------------------------------------------ 成长（v1.5.0 新增视图） */

  function viewGrowth() {
    var d = state.data;
    var rows = monthlySeries();
    var html = dataNotices();
    if (!rows.length) {
      return html + '<p class="empty">档案里还没有错题。等手机端同步一次就有数据了。</p>';
    }

    var total = (d.questions || []).length;
    var explained = explainedCount();
    var qs = sortedQuestions();
    var firstDay = dayOf(qs[0].created_at);
    var genDay = dayOf(d.generated_at) || dayOf(qs[qs.length - 1].created_at);
    var days = dayDiff(firstDay, genDay);
    var maxIntake = Math.max.apply(null, rows.map(function (m) { return m.intake; }));
    var maxExpl = Math.max.apply(null, rows.map(function (m) { return m.expl; }));
    var peak = rows.reduce(function (a, b) { return b.intake > a.intake ? b : a; }, rows[0]);
    var nowMonth = rows[rows.length - 1].m;
    var top = topKnowledge();
    var figs = cropFigures();
    var cols = 'repeat(' + rows.length + ',minmax(0,1fr))';

    rows[0].first = true;
    rows[0].firstDay = firstDay;

    html += '<section class="growth-lead"><h1 class="home-tag">' +
      cnCount(spanMonths()) + '个月，' + num(total) + ' 道错题。</h1>' +
      '<p class="home-note">从 ' + fmtDateCN(firstDay) + ' 第一道错题收进档案算起' +
      (days >= 1 ? '，' + num(days) + ' 天' : '') +
      '。这一页每一条数，都能在档案里找到出处。</p></section>';

    /* 学习活动：唯一图形是真比例柱图（柱高 ∝ 当月入库数，当前月朱红） */
    html += secHead('学习活动', '');
    html += '<div class="chart" style="grid-template-columns:' + cols + '" role="img" aria-label="月度入库错题数：' +
      rows.map(function (m) { return parseInt(m.m.slice(5), 10) + '月' + m.intake + '道'; }).join('，') + '">' +
      rows.map(function (m) {
        var h = m.intake === 0 ? 0 : Math.max(3, Math.round(m.intake / maxIntake * 100));
        return '<span class="col' + (m.m === nowMonth ? ' now' : '') + '">' +
          '<span class="val">' + m.intake + '</span>' +
          '<span class="track"><span class="bar" style="height:' + h + '%"></span></span></span>';
      }).join('') + '</div>' +
      '<div class="chart-x" style="grid-template-columns:' + cols + '">' +
      rows.map(function (m) {
        return '<span class="' + (m.m === nowMonth ? 'now' : '') + '">' +
          m.m.slice(5) + (rows.length <= 6 ? ' 月' : '') + '</span>';
      }).join('') + '</div>' +
      '<p class="chart-cap">柱高就是当月收进的错题数。' +
      (peak.intake > 0 ? parseInt(peak.m.slice(5), 10) + ' 月最厚，收了 ' + peak.intake + ' 道。' : '') +
      (figs !== null ? '切图一共 ' + figs + ' 张（按月登记行里的切题按会话内题数计，两种口径不混用）。' : '') +
      '</p>';

    /* 月度登记行：收错题 / 切题 / 讲解 / 新增知识点（原始标签口径） */
    html += rows.map(function (m) {
      var parts = ['收错题 ' + m.intake];
      if (figs !== null && m.crops) parts.push('切题 ' + m.crops + ' 题');
      if (m.expl) parts.push('讲解 ' + m.expl + ' 篇');
      if (m.newTags) parts.push('新增知识点 ' + m.newTags);
      var note = monthNote(m, maxExpl, peak.intake);
      return '<div class="mrow">' +
        '<div class="mrow-h"><span class="m">' + m.m.slice(5) + ' 月</span>' +
        '<span class="n">' + parts.join(' · ') + '</span></div>' +
        (note ? '<p class="mrow-note">' + esc(note) + '</p>' : '') +
        '</div>';
    }).join('');

    /* 知识覆盖增长（登记表：月 / 新增 / 累计） */
    html += secHead('知识覆盖', '');
    html += '<div class="reg">' + rows.map(function (m) {
      return '<div class="reg-row two">' +
        '<span class="t">' + m.m.slice(5) + ' 月</span>' +
        '<span class="n">+' + m.newTags + ' <small>累计 ' + m.cum + '</small></span>' +
        '</div>';
    }).join('') + '</div>' +
      '<p class="reg-note">错题自带的知识点标签，' + cnCount(spanMonths()) + '个月从 ' + num(rows[0].cum) +
      ' 个长到 ' + num(rows[rows.length - 1].cum) +
      ' 个。标签是原始记录；整理成受控概念后，是知识点页那份清单。</p>';

    /* 科目与错题结构（科目分布 + error_type 分布 + 一句据实生成的解读） */
    html += secHead('科目与错题结构', '');
    html += '<div class="reg">' + subjectCounts().map(function (s) {
      var pct = total ? (s.n / total * 100) : 0;
      return '<div class="reg-row">' +
        '<span class="seal-mark' + sealCls(s.key) + '" aria-hidden="true">' + esc(s.seal) + '</span>' +
        '<span class="t">' + esc(s.name) + '</span>' +
        '<span class="n">' + s.n + ' <small>' + pct.toFixed(1) + '%</small></span>' +
        '<span class="reg-bar"><i style="width:' + pct.toFixed(1) + '%"></i></span>' +
        '</div>';
    }).join('') + '</div>';

    var ets = errorTypeCounts();
    if (ets) {
      html += '<div class="reg reg-gap">' + ets.rows.map(function (e) {
        var pct = ets.total ? (e.n / ets.total * 100) : 0;
        return '<div class="reg-row two">' +
          '<span class="t">' + esc(e.name) + '</span>' +
          '<span class="n">' + e.n + ' <small>' + pct.toFixed(1) + '%</small></span>' +
          '<span class="reg-bar"><i style="width:' + pct.toFixed(1) + '%"></i></span>' +
          '</div>';
      }).join('') + '</div>';
      var topEt = ets.rows[0];
      var note = ets.total < total
        ? '错题归因覆盖 ' + ets.total + ' / ' + total + ' 道，比例按打了归因标签的题算。'
        : '';
      if (topEt.concept && topEt.n / ets.total > 0.5) {
        note += '一半以上的错题错在<b>概念</b>——所以每篇讲解都从概念讲起，而不是先讲步骤。';
      } else {
        note += '错得最多的是<b>「' + esc(topEt.name) + '」</b>（' + topEt.n + ' 道，' +
          (topEt.n / ets.total * 100).toFixed(1) + '%）——下一份讲解可以从这里补起。';
      }
      html += '<p class="reg-note">' + note + '</p>';
    }

    /* 学习阶梯：当前级按数据诚实评定，上两级只写路径，不摆假进度 */
    var rb = reviewBacklog();
    /* 定级依据（写进代码，便于核对）：
       L1「认真订正」= 有入库且有讲解（explained > 0）；
       L2「让复习转起来」= stats.review_backlog.overdue > 0 且到期未复习占到总数一半以上
         ——到期占比高说明复习还没转起来，卡在第二级入口；
       review_backlog 缺席时无法诚实评定，任何一级都不标「你在这儿」；
       L3/L4 只有路径文字，无百分比、无勾选、无灰禁用。 */
    var l2now = !!rb && rb.overdue > 0 && total > 0 && rb.overdue >= total / 2;
    var l2text;
    if (!rb) l2text = '到期未复习的题数，要等手机侧同步后才看得到。';
    else if (rb.overdue <= 0) l2text = num(total) + ' 道错题里，到期未复习的已经清空。';
    else {
      l2text = num(total) + ' 道错题里，' + num(rb.overdue) + ' 道的复习已经到期' +
        (rb.snapshot ? '（' + esc(fmtDay(rb.snapshot)) + ' 快照）' : '') + '。';
    }
    html += secHead('学习阶梯', '');
    html += '<div class="ladder">' +
      '<div class="lstep' + (explained > 0 ? ' done' : '') + '">' +
        '<span class="lmark" aria-hidden="true"></span>' +
        '<div class="lbody"><p class="lname">认真订正</p>' +
        '<p class="lev">收进 ' + num(total) + ' 道，讲透 ' + num(explained) + ' 篇。错题不再沉在拍照里。</p>' +
        '</div></div>' +
      '<div class="lstep' + (l2now ? ' now' : '') + '">' +
        '<span class="lmark" aria-hidden="true"></span>' +
        '<div class="lbody"><p class="lname">让复习转起来' +
        (l2now ? '<span class="lhere">你在这儿</span>' : '') + '</p>' +
        '<p class="lev">' + l2text + '</p></div></div>' +
      '<div class="lstep">' +
        '<span class="lmark" aria-hidden="true"></span>' +
        '<div class="lbody"><p class="lname">举一反三</p>' +
        '<p class="lev ahead">' + (top && top.n >= 2
          ? '「' + esc(top.name) + '」收了 ' + num(top.n) + ' 道——同一条路还在摔跤。跨过它，就到这一级。'
          : '把错得最多的那一类反复拾起来，跨过它，就到这一级。') + '</p></div></div>' +
      '<div class="lstep">' +
        '<span class="lmark" aria-hidden="true"></span>' +
        '<div class="lbody"><p class="lname">自主总结</p>' +
        '<p class="lev ahead">自己把一章的错题整理成册，讲给别人听。</p></div></div>' +
      '</div>';

    /* 下一件事：从最近讲过的题起步，挂去讲解查阅 */
    var recN = recentExplanations(3).length;
    html += '<section class="nextstep">' +
      '<p class="nextstep-t">下一件事：让复习转起来。</p>' +
      '<p class="nextstep-p">' +
      (rb && rb.overdue > 0
        ? '截至 ' + (rb.snapshot ? esc(fmtDay(rb.snapshot)) : '最近一次同步') + '：' + num(rb.overdue) +
          ' 道复习到期未看' + (rb.dueToday ? '，当天又有 ' + num(rb.dueToday) + ' 道到期' : '') + '。'
        : '') +
      '不用一次看完——' + (recN ? '明天从最近讲过的 ' + num(recN) + ' 道开始' : '从手头最近的一道开始') +
      '，看完在档案里记一笔。</p>' +
      '<a class="nextstep-a" href="#/teach">去讲解查阅挑题</a>' +
      '</section>';
    return html;
  }

  function secHead(label, moreHref) {
    /* moreHref 为空（成长页各区没有「全部」可去）时整条链接不渲染，不摆空链接 */
    return '<h2 class="sec-h"><span>' + esc(label) + '</span>' +
      (moreHref ? '<a class="sec-more" href="' + moreHref + '">全部</a>' : '') +
      '</h2>';
  }

  function sampleBanner() {
    if (!state.data.sample) return '';
    return '<p class="hint">⚠️ 当前是开发用的合成样例数据，不是真实学习记录。手机端首次同步后会自动替换。</p>';
  }

  function dataNotices() {
    var html = sampleBanner();
    if (state.contractMismatch) {
      html += '<p class="hint">⚠️ 数据契约版本不匹配（页面期望 ' + CONTRACT_COMPAT_VERSIONS.join(' / ') +
        '，数据为 ' + esc(String(state.data.contract_version)) + '），显示可能异常。</p>';
    }
    return html;
  }

  /* ------------------------------------------------ 讲解查阅 · 列表 */

  function filteredQuestions() {
    var f = state.filters;
    var arr = (state.data.questions || []).slice();
    if (f.subject !== 'all') arr = arr.filter(function (q) { return q.subject === f.subject; });
    if (f.expl === 'yes') arr = arr.filter(function (q) { return q.has_explanation; });
    if (f.expl === 'no') arr = arr.filter(function (q) { return !q.has_explanation; });
    var kps = Object.keys(f.kps).filter(function (k) { return f.kps[k]; });
    if (kps.length) {
      arr = arr.filter(function (q) {
        return (q.knowledge_points || []).some(function (k) { return kps.indexOf(k) >= 0; });
      });
    }
    var kw = f.kw.trim().toLowerCase();
    if (kw) {
      arr = arr.filter(function (q) {
        var hay = [q.question, q.student_answer, q.correct_answer, (q.knowledge_points || []).join(' ')]
          .join(' ').toLowerCase();
        return hay.indexOf(kw) >= 0;
      });
    }
    arr.sort(function (a, b) {
      var r = String(a.created_at || '').localeCompare(String(b.created_at || ''));
      return f.sort === 'old' ? r : -r;
    });
    return arr;
  }

  /* opts.thumb：讲解列表传 true，行有 q.thumb 时左侧上缩略图；opts.summary：首页传讲解摘要，
     有则代替题干截断显示（契约 v1.1，字段缺席一律回退现有形态）。 */
  function questionRow(q, opts) {
    opts = opts || {};
    var kps = q.knowledge_points || [];
    var kpText = kps.length ? kps.slice(0, 3).join(' · ') + (kps.length > 3 ? ' · +' + (kps.length - 3) : '') : '';
    var vers = q.explanation_versions || [];
    var st = vers.length ? vers.join(' ') : '未讲';
    var meta = [];
    if (kpText) meta.push(kpText);
    meta.push(fmtDay(q.do_time || q.created_at));
    var thumb = opts.thumb && q.thumb
      ? '<img class="row-thumb" src="data/' + esc(q.thumb) + '" alt="题 #' + q.id + '" loading="lazy" decoding="async">'
      : '';
    var text = opts.summary ? clampText(opts.summary, 120) : clampText(q.question, 120);
    return '<a class="row' + (thumb ? ' has-thumb' : '') + '" href="#/teach/q/' + q.id + '">' +
      thumb +
      '<span class="seal-mark' + sealCls(q.subject) + '">' + esc(subjSeal(q.subject)) + '</span>' +
      '<span class="row-main">' +
      '<span class="row-q">' + esc(text) + '</span>' +
      '<span class="row-meta">' + esc(meta.join(' · ')) + '</span>' +
      '</span>' +
      '<span class="row-idx">#' + q.id +
      '<span class="st' + (vers.length ? '' : ' no') + '">' + esc(st) + '</span></span>' +
      '</a>';
  }

  function viewTeach() {
    var qs = state.data.questions || [];
    var subjCount = {};
    qs.forEach(function (q) { subjCount[q.subject] = (subjCount[q.subject] || 0) + 1; });
    var f = state.filters;

    var subjSeg = '<button class="seg-btn" type="button" data-f="subject" data-v="all"' +
      (f.subject === 'all' ? ' aria-pressed="true"' : '') + '>全部<span class="n">' + qs.length + '</span></button>';
    Object.keys(subjCount).sort(function (a, b) {
      return (SUBJECT_CN[a] || a).localeCompare(SUBJECT_CN[b] || b, 'zh');
    }).forEach(function (s) {
      subjSeg += '<button class="seg-btn" type="button" data-f="subject" data-v="' + esc(s) + '"' +
        (f.subject === s ? ' aria-pressed="true"' : '') + '>' + esc(subjCN(s)) + '<span class="n">' + subjCount[s] + '</span></button>';
    });

    var hasN = qs.filter(function (q) { return q.has_explanation; }).length;
    var explSeg =
      '<button class="seg-btn" type="button" data-f="expl" data-v="all"' + (f.expl === 'all' ? ' aria-pressed="true"' : '') + '>全部</button>' +
      '<button class="seg-btn" type="button" data-f="expl" data-v="yes"' + (f.expl === 'yes' ? ' aria-pressed="true"' : '') + '>有讲解<span class="n">' + hasN + '</span></button>' +
      '<button class="seg-btn" type="button" data-f="expl" data-v="no"' + (f.expl === 'no' ? ' aria-pressed="true"' : '') + '>无讲解<span class="n">' + (qs.length - hasN) + '</span></button>';

    var selKps = Object.keys(f.kps).filter(function (k) { return f.kps[k]; });
    var kpSummary = selKps.length
      ? '<p class="kp-summary">已按 <b>' + selKps.map(esc).join('</b>、<b>') + '</b> 过滤' +
        '<button class="kp-clear" type="button" id="kp-clear">清空</button></p>'
      : '';

    var html = dataNotices() +
      '<div class="toolbar">' +
      '<div class="search-wrap"><input class="search" id="kw-input" type="search" enterkeyhint="search" ' +
      'placeholder="搜题干、答案或知识点" aria-label="搜索题目" value="' + esc(f.kw) + '">' +
      '<button class="search-clear" type="button" id="kw-clear" aria-label="清空搜索"' +
      (f.kw ? '' : ' hidden') + '>清空</button></div>' +
      '<div class="frow"><div class="frow-label">科目</div><div class="seg" role="group" aria-label="按科目筛选">' + subjSeg + '</div></div>' +
      '<div class="frow"><div class="frow-label">讲解</div><div class="seg" role="group" aria-label="按有无讲解筛选">' + explSeg + '</div></div>' +
      '<div class="frow"><div class="frow-head"><div class="frow-label">知识点</div>' +
      '<button class="kp-open" type="button" id="kp-open"' + (selKps.length ? ' aria-pressed="true"' : '') + '>选择知识点' +
      (selKps.length ? ' · 已选 <span class="n">' + selKps.length + '</span>' : '') + '</button></div>' + kpSummary + '</div>' +
      '</div>';

    var list = filteredQuestions();
    html += '<p class="result-line"><b>' + list.length + '</b> 道题' +
      '<button class="kp-clear" type="button" id="sort-toggle" style="margin-left:12px">' +
      (f.sort === 'new' ? '最新录入优先 ↓' : '最早录入优先 ↑') + '</button></p>';

    html += list.length
      ? '<div class="rows">' + list.map(function (q) { return questionRow(q, { thumb: true }); }).join('') + '</div>'
      : '<div class="empty">没有符合条件的题目<br><button class="kp-clear" type="button" id="reset-all" style="margin-top:10px">清空全部筛选</button></div>';
    return html;
  }

  function wireTeach() {
    var $kw = document.getElementById('kw-input');
    var $clear = document.getElementById('kw-clear');
    var t;
    function paintClear() { $clear.hidden = !$kw.value; }
    $clear.addEventListener('click', function () {
      $kw.value = '';
      state.filters.kw = '';
      paintClear();
      setRoute(teachHref());
      $kw.focus();
    });
    $kw.addEventListener('input', function () {
      paintClear();
      clearTimeout(t);
      var v = $kw.value;
      t = setTimeout(function () { state.filters.kw = v; setRoute(teachHref()); }, 220);
    });
    $app.querySelectorAll('.seg-btn[data-f]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-f'), v = btn.getAttribute('data-v');
        if (f === 'subject') state.filters.subject = (state.filters.subject === v ? 'all' : v);
        else if (f === 'expl') state.filters.expl = (state.filters.expl === v ? 'all' : v);
        setRoute(teachHref());
      });
    });
    var $kpOpen = document.getElementById('kp-open');
    if ($kpOpen) $kpOpen.addEventListener('click', function () { openKpSheet(); });
    var $kpClear = document.getElementById('kp-clear');
    if ($kpClear) $kpClear.addEventListener('click', function () { state.filters.kps = {}; setRoute(teachHref()); });
    var $sort = document.getElementById('sort-toggle');
    if ($sort) $sort.addEventListener('click', function () {
      state.filters.sort = state.filters.sort === 'new' ? 'old' : 'new';
      setRoute(teachHref());
    });
    var $reset = document.getElementById('reset-all');
    if ($reset) $reset.addEventListener('click', function () {
      state.filters = { subject: 'all', expl: 'all', kps: {}, kw: '', sort: 'new' };
      setRoute(teachHref());
    });
  }

  /* ------------------------------------------------ 知识点面板 */

  var sheetState = { open: false, lastFocus: null };

  function kpCounts() {
    var c = {};
    (state.data.questions || []).forEach(function (q) {
      (q.knowledge_points || []).forEach(function (k) { c[k] = (c[k] || 0) + 1; });
    });
    return c;
  }

  function openKpSheet() {
    if (sheetState.open) return;
    sheetState.open = true;
    sheetState.lastFocus = document.activeElement;

    var counts = kpCounts();
    var all = Object.keys(counts).sort(function (a, b) {
      return counts[b] - counts[a] || a.localeCompare(b, 'zh');
    });

    var scrim = document.getElementById('scrim');
    scrim.hidden = false;
    var sheet = document.createElement('div');
    sheet.className = 'sheet';
    sheet.id = 'kp-sheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    sheet.setAttribute('aria-label', '选择知识点');
    sheet.innerHTML =
      '<div class="sheet-hd"><h2>选择知识点</h2>' +
      '<button class="sheet-x" type="button" id="sheet-x">完成</button></div>' +
      '<div class="sheet-body">' +
      '<div class="search-wrap" style="margin-bottom:10px"><input class="search" id="kp-search" type="search" ' +
      'placeholder="搜索知识点" value="' + esc(state.kpSearch) + '"></div>' +
      '<div id="kp-list"></div>' +
      '</div>' +
      '<div class="sheet-ft">' +
      '<button class="btn" type="button" id="kp-clear-all">清空选择</button>' +
      '<button class="btn btn-primary" type="button" id="kp-done">看结果</button>' +
      '</div>';
    document.body.appendChild(sheet);

    function paintList() {
      var s = state.kpSearch.trim().toLowerCase();
      var shown = all.filter(function (k) { return !s || k.toLowerCase().indexOf(s) >= 0; });
      var $list = document.getElementById('kp-list');
      if (!shown.length) { $list.innerHTML = '<p class="empty" style="padding:24px 0">没有匹配的知识点</p>'; return; }
      $list.innerHTML = shown.map(function (k) {
        var on = state.filters.kps[k] ? 'true' : 'false';
        return '<button class="kp-item" type="button" data-kp="' + esc(k) + '" aria-pressed="' + on + '">' +
          '<span class="box">✓</span><span class="txt">' + esc(k) + '</span>' +
          '<span class="cnt">' + counts[k] + '</span></button>';
      }).join('');
      $list.querySelectorAll('.kp-item').forEach(function (b) {
        b.addEventListener('click', function () {
          var k = b.getAttribute('data-kp');
          state.filters.kps[k] = !state.filters.kps[k];
          b.setAttribute('aria-pressed', state.filters.kps[k] ? 'true' : 'false');
        });
      });
    }
    paintList();

    var $search = document.getElementById('kp-search');
    $search.addEventListener('input', function () {
      state.kpSearch = $search.value;
      paintList();
      $search.focus();
    });    document.getElementById('kp-clear-all').addEventListener('click', function () {
      state.filters.kps = {};
      paintList();
    });
    function done() { closeSheet(); setRoute(teachHref()); }
    document.getElementById('kp-done').addEventListener('click', done);
    document.getElementById('sheet-x').addEventListener('click', done);
    scrim.addEventListener('click', closeSheet);

    $search.focus();

    window.__closeSheet = function (silent) {
      if (!sheetState.open) return;
      sheetState.open = false;
      var sh = document.getElementById('kp-sheet');
      if (sh) sh.remove();
      scrim.hidden = true;
      scrim.removeEventListener('click', closeSheet);
      window.__closeSheet = null;
      if (!silent && sheetState.lastFocus && sheetState.lastFocus.focus) sheetState.lastFocus.focus();
    };
    document.addEventListener('keydown', sheetKey);
  }
  function closeSheet() { if (window.__closeSheet) window.__closeSheet(); }
  function sheetKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); closeSheet(); }
  }

  /* ------------------------------------------------ 讲解查阅 · 详情 */

  function viewQuestion(id) {
    var q = qById(id);
    if (!q) {
      return '<div class="backbar"><a class="backlink" href="#/teach">← 返回题目列表</a></div>' +
        '<div class="err"><b>找不到这道题</b>错题本里没有编号 #' + esc(id) + ' 的题目，可能已被删除。</div>';
    }
    var kps = q.knowledge_points || [];
    var headBits = ['#' + q.id, subjCN(q.subject)];
    if (q.grade) headBits.push(q.grade);
    var html = dataNotices() +
      '<div class="backbar"><a class="backlink" href="#/teach">← 返回题目列表</a></div>' +
      '<div class="detail-head">' +
      '<span class="seal-mark' + sealCls(q.subject) + '">' + esc(subjSeal(q.subject)) + '</span>' +
      '<span class="detail-id">' + esc(headBits.join(' · ')) + '</span>' +
      '<span class="detail-date">' + esc(fmtDay(q.do_time || q.created_at)) + '</span>' +
      '</div>';

    html += q.image
      ? '<figure class="figure"><img id="q-img" src="data/' + esc(q.image) + '" alt="第 ' + q.id + ' 题题图" decoding="async">' +
        '<figcaption class="cap">点按可看大图</figcaption></figure>'
      : '<div class="img-missing">这道题没有归档题图</div>';

    html += '<section class="block"><h2 class="block-h">题目</h2>' +
      '<p class="reading">' + esc(q.question || '（没有 OCR 文本）') + '</p>';
    if (q.student_answer || q.correct_answer) {
      html += '<div class="ans">';
      if (q.student_answer) html += '<div class="ans-row"><span class="k">我的答案</span><span class="v mine">' + esc(q.student_answer) + '</span></div>';
      if (q.correct_answer) html += '<div class="ans-row ans-right"><span class="k">正确答案</span><span class="v right">' + esc(q.correct_answer) + '</span></div>';
      html += '</div>';
    }
    html += '</section>';

    html += '<section class="block"><h2 class="block-h">知识点</h2>';
    html += kps.length
      ? '<p class="kp-line">' + kps.map(function (k) {
          return '<a href="' + teachHref({ kp: k, subject: null, expl: null, kw: null, sort: null }) + '">' + esc(k) + '</a>';
        }).join('<span class="dot">·</span>') + '</p>'
      : '<p class="kp-line" style="color:var(--ink-2)">这道题还没有打知识点标签</p>';
    html += '</section>';

    html += '<section class="block"><h2 class="block-h">讲解记录</h2><div id="expl-body"></div></section>';

    var meta = [];
    if (q.review_count) meta.push('复习 ' + q.review_count + ' 次');
    if (q.ocr_verified) meta.push('OCR 已校验');
    if (q.crop_session) meta.push('<a href="#/crop/s/' + encodeURIComponent(q.crop_session) + '">出自切题</a>');
    if (meta.length) html += '<p class="hint">' + meta.join(' · ') + '</p>';
    return html;
  }

  function renderExplCard(q) {
    var vers = q.explanation_versions || [];
    var $body = document.getElementById('expl-body');
    if (!vers.length) {
      $body.innerHTML = '<p class="hint">这道题还没有讲解记录。让机器人讲一次，这里就会出现。</p>';
      return;
    }
    var cur = state.explSel[q.id] && vers.indexOf(state.explSel[q.id]) >= 0
      ? state.explSel[q.id] : vers[vers.length - 1];
    state.explSel[q.id] = cur;

    $body.innerHTML = '<div class="vers" role="tablist" aria-label="讲解版本">' +
      vers.map(function (v) {
        return '<button type="button" role="tab" data-v="' + esc(v) + '"' +
          (v === cur ? ' aria-selected="true"' : ' aria-selected="false"') + '>' + esc(v) +
          (v === 'v2' ? '<span class="tag">重讲</span>' : '') + '</button>';
      }).join('') + '</div><div id="expl-md" role="tabpanel"><div class="boot" style="padding:28px 0">正在读取讲解…</div></div>';

    $body.querySelectorAll('.vers button').forEach(function (b) {
      b.addEventListener('click', function () { loadVersion(b.getAttribute('data-v')); });
    });
    loadVersion(cur);

    function loadVersion(v) {
      state.explSel[q.id] = v;
      $body.querySelectorAll('.vers button').forEach(function (b) {
        b.setAttribute('aria-selected', b.getAttribute('data-v') === v ? 'true' : 'false');
      });
      var $md = document.getElementById('expl-md');
      $md.innerHTML = '<div class="boot" style="padding:28px 0">正在读取讲解…</div>';
      fetchExpl(q.id, v).then(function (txt) {
        $md.innerHTML = txt
          ? '<div class="md">' + renderMarkdown(txt) + '</div>'
          : '<div class="hint">讲解文件缺失：data/explanations/' + q.id + '-' + esc(v) + '.md</div>';
      });
    }
  }

  /* ------------------------------------------------ 切题库 */

  function sortedSessions() {
    return (state.data.crop_sessions || []).slice().sort(function (a, b) {
      return String(b.date).localeCompare(String(a.date)) || String(b.session).localeCompare(String(a.session));
    });
  }

  function sessionRow(s) {
    var probs = s.problems || [];
    var thumbs = probs.slice(0, 3).map(function (p) {
      return '<img src="data/' + esc(p.file) + '" alt="' + esc(p.qnum || ('第 ' + p.index + ' 题')) + '" loading="lazy" decoding="async">';
    }).join('');
    return '<a class="sess" href="#/crop/s/' + encodeURIComponent(s.session) + '">' +
      '<span class="sess-thumbs">' + thumbs + '</span>' +
      '<span class="sess-meta">' +
      '<span class="sess-t">' + esc(fmtTimeCN(s.photo_time || s.date)) + '</span>' +
      '<span class="sess-s"><span class="cnt">' + probs.length + '</span> 题</span>' +
      '</span></a>';
  }

  function viewCrop() {
    var sessions = sortedSessions();
    if (!sessions.length) {
      return dataNotices() + '<p class="empty">还没有切题记录。发一张作业照片，机器人切好题后这里就会出现。</p>';
    }
    var byDate = {};
    sessions.forEach(function (s) { (byDate[s.date] = byDate[s.date] || []).push(s); });
    var html = dataNotices();
    Object.keys(byDate).sort().reverse().forEach(function (d) {
      var total = byDate[d].reduce(function (n, s) { return n + (s.problems || []).length; }, 0);
      html += '<div class="date-h"><span class="d">' + esc(fmtDateCN(d)) + '</span>' +
        '<span class="n">' + byDate[d].length + ' 次 · ' + total + ' 题</span></div>';
      html += byDate[d].map(sessionRow).join('');
    });
    return html;
  }

  function findSession(name) {
    var found = null;
    (state.data.crop_sessions || []).forEach(function (x) { if (x.session === name) found = x; });
    return found;
  }

  function viewSession(name) {
    var s = findSession(name);
    if (!s) {
      return '<div class="backbar"><a class="backlink" href="#/crop">← 返回切题库</a></div>' +
        '<div class="err"><b>找不到这次切题</b>会话 ' + esc(name) + ' 不在当前数据里。</div>';
    }
    var probs = s.problems || [];
    var cells = probs.map(function (p) {
      var label = p.qnum || ('第 ' + p.index + ' 题');
      var eb = '';
      if (p.error_book_id != null) {
        eb = '<a class="cc-eb" href="#/teach/q/' + p.error_book_id + '">错题 #' + p.error_book_id + '</a>';
      } else if ('error_book_id' in p) {
        eb = '<span class="cc-eb none">未收录</span>';
      }
      return '<button type="button" class="crop-cell" data-idx="' + p.index + '">' +
        '<img src="data/' + esc(p.file) + '" alt="' + esc(label) + '" loading="lazy" decoding="async">' +
        '<span class="cc-meta"><span class="cc-q">' + esc(label) + '</span>' + eb + '</span></button>';
    }).join('');

    return dataNotices() +
      '<div class="backbar"><a class="backlink" href="#/crop">← 返回日期列表</a></div>' +
      '<div class="detail-head">' +
      '<span class="seal-mark">切</span>' +
      '<span class="detail-id">' + esc(fmtDateCN(s.date)) + ' ' + esc(fmtTimeCN(s.photo_time || s.date)) + '</span>' +
      '<span class="detail-date">' + probs.length + ' 题</span></div>' +
      '<div class="crop-grid">' + cells + '</div>' +
      '<p class="hint">标了错题本的题目可以直接点进去；没标的只拍了照。</p>';
  }

  function wireSession(sessName) {
    $app.querySelectorAll('.crop-cell').forEach(function (cell) {
      cell.addEventListener('click', function () {
        location.hash = '#/crop/s/' + encodeURIComponent(sessName) + '/' + cell.getAttribute('data-idx');
      });
    });
  }

  /* ------------------------------------------------ 切题库 · 单题大图 */

  function viewProblem(sessName, idx) {
    var s = findSession(sessName);
    var p = null;
    if (s) (s.problems || []).forEach(function (x) { if (x.index === idx) p = x; });
    if (!p) {
      return '<div class="backbar"><a class="backlink" href="#/crop/s/' + encodeURIComponent(sessName) + '">← 返回会话网格</a></div>' +
        '<div class="err"><b>找不到这道切题</b>这次会话里没有序号 ' + esc(idx) + ' 的题目。</div>';
    }
    var probs = s.problems || [];
    var pos = probs.indexOf(p);
    var prev = pos > 0 ? probs[pos - 1] : null;
    var next = pos < probs.length - 1 ? probs[pos + 1] : null;
    var q = p.error_book_id != null ? qById(p.error_book_id) : null;
    var label = p.qnum || ('第 ' + p.index + ' 题');

    var html = '<div class="backbar"><a class="backlink" href="#/crop/s/' + encodeURIComponent(sessName) + '">← 返回会话网格</a></div>';

    if (p.error_book_id != null) {
      html += '<p class="hint">已入错题本 · <a href="#/teach/q/' + p.error_book_id + '">#' + p.error_book_id +
        (q ? ' ' + esc(subjCN(q.subject)) : '') + '</a>' + (q ? (q.has_explanation ? ' · 有讲解' : ' · 还没讲解') : '') + '</p>';
    } else if ('error_book_id' in p) {
      html += '<p class="hint">这道题只拍了照，还没有收进错题本。</p>';
    }

    /* 附图组合排版：仅当 figure_attached 为真且 figure_files 非空时渲染；
       无附图题的 HTML 与此分支完全无关（回归硬约束：逐字节不变）。
       附图文件与 problems[].file 同目录（crops.json 产物口径）。 */
    var figFiles = (p.figure_attached && Array.isArray(p.figure_files)) ? p.figure_files : [];
    var figHtml = '';
    if (figFiles.length) {
      var slash = p.file.lastIndexOf('/');
      var figDir = slash >= 0 ? p.file.slice(0, slash + 1) : '';
      figHtml = '<div class="prob-figs"><p class="prob-figs-h">附图</p><div class="prob-figs-row">' +
        figFiles.map(function (f, i) {
          return '<figure class="prob-fig"><img src="data/' + esc(figDir + f) + '" alt="附图 ' + (i + 1) +
            '" decoding="async"><figcaption>附图 ' + (i + 1) + '</figcaption></figure>';
        }).join('') + '</div></div>';
    }

    html += '<figure class="prob-figure"><img id="prob-img" src="data/' + esc(p.file) + '" alt="' + esc(label) + '" decoding="async"></figure>' +
      figHtml +
      '<div class="pnav">' +
      (prev ? '<a class="btn" href="#/crop/s/' + encodeURIComponent(sessName) + '/' + prev.index + '">← 上一题</a>'
            : '<span class="btn" aria-disabled="true">← 上一题</span>') +
      '<span class="pos">' + (pos + 1) + ' / ' + probs.length + '</span>' +
      (next ? '<a class="btn" href="#/crop/s/' + encodeURIComponent(sessName) + '/' + next.index + '">下一题 →</a>'
            : '<span class="btn" aria-disabled="true">下一题 →</span>') +
      '</div>' +
      '<p class="hint">' + esc(fmtDateTimeCN(s.photo_time || s.date)) +
      (p.text_preview ? ' · 图中文字：' + esc(p.text_preview) : '') + '</p>';
    return html;
  }

  /* ------------------------------------------------ 积累册 */

  function accumBooks() {
    return state.data.accum_books || [];
  }
  function findBook(name) {
    var found = null;
    accumBooks().forEach(function (b) { if (b.name === name) found = b; });
    return found;
  }
  function bookHref(b) { return '#/accum/b/' + encodeURIComponent(b.name); }

  function viewAccum() {
    var books = accumBooks();
    if (!books.length) {
      return dataNotices() +
        '<p class="empty">还没有积累册。手机端整理好一本后，这里会按册排出来。</p>';
    }
    var html = dataNotices() +
      '<p class="accum-lead">手机侧整理的积累册，按册翻看；点开读正文，PDF 原件可另存。</p>' +
      '<div class="arows">' + books.map(function (b, i) {
        var kps = b.knowledge_points || [];
        var kpText = kps.length
          ? kps.slice(0, 4).join(' · ') + (kps.length > 4 ? ' · +' + (kps.length - 4) : '')
          : '';
        var cnt = (b.problem_count == null || b.problem_count === '') ? '' : b.problem_count;
        return '<a class="arow" href="' + bookHref(b) + '">' +
          '<span class="arow-idx">' + pad2(i + 1) + '</span>' +
          '<span class="arow-main">' +
          '<span class="arow-t">' + esc(b.name) + '</span>' +
          '<span class="arow-meta">' + esc(kpText) + '</span>' +
          '</span>' +
          '<span class="arow-n">' + (cnt === '' ? '' : cnt + ' 题') + '</span>' +
          '</a>';
      }).join('') + '</div>';
    return html;
  }

  function viewAccumBook(name) {
    var b = findBook(name);
    if (!b) {
      return '<div class="backbar"><a class="backlink" href="#/accum">← 返回积累册</a></div>' +
        '<div class="err"><b>找不到这本积累册</b>档案里没有名为「' + esc(name) + '」的册子，可能已重新整理。</div>';
    }
    var kps = b.knowledge_points || [];
    var cnt = (b.problem_count == null || b.problem_count === '') ? '' : b.problem_count;
    var note = '<span class="np"><span class="k">题</span>' +
      (cnt === '' ? '未记' : cnt) + '</span>' +
      '<span class="np"><span class="k">知识点</span>' + (kps.length ? kps.length : '未标') + ' 个</span>';
    if (kps.length) {
      note += '<span class="np kpd">' + esc(kps.join(' · ')) + '</span>';
    }
    note += '<a class="book-pdf" href="data/' + esc(b.pdf) + '" target="_blank" rel="noopener">PDF 原件 ↗</a>';
    return dataNotices() +
      '<div class="backbar"><a class="backlink" href="#/accum">← 返回积累册</a></div>' +
      '<header class="book-head"><h1 class="book-title">' + esc(b.name) + '</h1>' +
      '<p class="book-note">' + note + '</p></header>' +
      '<iframe class="book-frame" id="book-frame" src="data/' + esc(b.html) + '" ' +
      'title="' + esc(b.name) + '" sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe>' +
      '<p class="hint">正文是手机侧生成的原册页面，这里原样嵌入、不套站点样式。</p>';
  }

  function wireAccumBook() {
    var $f = document.getElementById('book-frame');
    if (!$f) return;
    $f.addEventListener('load', function () {
      try {
        var doc = $f.contentDocument;
        if (doc && doc.documentElement) {
          $f.style.height = Math.max(doc.documentElement.scrollHeight, 320) + 'px';
        }
      } catch (e) {}
    });
  }

  /* ------------------------------------------------ 知识点 · 受控概念（契约 v1.2 kp_concepts） */

  function kpVocab() { return state.data.kp_concepts || null; }

  /* 题目数由 questions[].kp_concepts 客户端统计；字段缺席的题不参与计数 */
  function kpConceptCounts() {
    var c = {};
    (state.data.questions || []).forEach(function (q) {
      (q.kp_concepts || []).forEach(function (k) { c[k] = (c[k] || 0) + 1; });
    });
    return c;
  }

  var KP_SUBJECT_ORDER = ['math', 'physics', 'chemistry'];

  function viewKp() {
    var vocab = kpVocab();
    if (!vocab || !vocab.length) {
      return dataNotices() +
        '<p class="empty">数据还没有受控概念归档。手机端按新契约同步一次后，这里会按科目列出受控概念。</p>';
    }
    var counts = kpConceptCounts();
    var bySubj = {};
    vocab.forEach(function (c) {
      var s = c.subject || 'other';
      (bySubj[s] = bySubj[s] || []).push(c.name);
    });
    var subjects = KP_SUBJECT_ORDER.filter(function (s) { return bySubj[s]; }).concat(
      Object.keys(bySubj).filter(function (s) { return KP_SUBJECT_ORDER.indexOf(s) < 0; }).sort()
    );
    var listedTotal = 0;
    subjects.forEach(function (s) {
      bySubj[s].forEach(function (n) { if (counts[n] > 0) listedTotal++; });
    });
    var html = dataNotices() +
      '<p class="kp-lead">受控词表 <b>' + vocab.length + '</b> 个概念，其中 <b>' + listedTotal +
      '</b> 个已有题目归档。</p>';
    if (!listedTotal) {
      html += '<p class="empty">受控概念都还没有题目归档。手机端同步归一后，这里会列出有题的概念。</p>';
      return html;
    }
    subjects.forEach(function (s) {
      var names = bySubj[s].filter(function (n) { return counts[n] > 0; });
      if (!names.length) return;
      names.sort(function (a, b) { return counts[b] - counts[a] || a.localeCompare(b, 'zh'); });
      html += '<div class="date-h"><span class="d">' + esc(subjCN(s)) + '</span>' +
        '<span class="n">' + names.length + ' 个</span></div>';
      html += '<div class="krows">' + names.map(function (n) {
        return '<a class="krow" href="#/kp/c/' + encodeURIComponent(n) + '">' +
          '<span class="krow-t">' + esc(n) + '</span>' +
          '<span class="krow-n">' + counts[n] + ' 题</span></a>';
      }).join('') + '</div>';
    });
    return html;
  }

  function viewKpConcept(name) {
    var back = '<div class="backbar"><a class="backlink" href="#/kp">← 返回知识点</a></div>';
    var entry = null;
    (kpVocab() || []).forEach(function (c) { if (c.name === name) entry = c; });
    if (!entry) {
      return back + '<div class="err"><b>找不到这个受控概念</b>词表里没有名为「' + esc(name) +
        '」的概念，可能已归并或改名。</div>';
    }
    var qs = (state.data.questions || []).filter(function (q) {
      return (q.kp_concepts || []).indexOf(name) >= 0;
    });
    if (!qs.length) {
      return back + '<div class="err"><b>这个概念还没有题目归档</b>「' + esc(name) +
        '」在受控词表里，但还没有题目归到它下面。</div>';
    }
    qs.sort(function (a, b) { return String(b.created_at || '').localeCompare(String(a.created_at || '')); });
    var note = '<span class="np"><span class="k">科目</span>' + esc(subjCN(entry.subject)) + '</span>' +
      '<span class="np"><span class="k">题</span>' + qs.length + '</span>';
    return dataNotices() + back +
      '<header class="book-head"><h1 class="book-title">' + esc(name) + '</h1>' +
      '<p class="book-note">' + note + '</p></header>' +
      '<div class="rows">' + qs.map(function (q) { return questionRow(q, { thumb: true }); }).join('') + '</div>';
  }

  /* ------------------------------------------------ 图片兜底 & 灯箱 */

  function wireImgFallback(img) {
    img.addEventListener('error', function () {
      var box = document.createElement('div');
      box.className = 'img-missing';
      box.textContent = '图片缺失：' + (img.getAttribute('src') || '');
      img.replaceWith(box);
    });
  }

  /* 列表缩略图加载失败时直接摘掉，行回退纯文字形态（不出破图、不出占位框） */
  function dropBrokenThumbs() {
    $app.querySelectorAll('.row-thumb').forEach(function (img) {
      function drop() { img.remove(); }
      if (img.complete && img.naturalWidth === 0) drop();
      else img.addEventListener('error', drop);
    });
  }

  /* 切题库附图过滤：最小边 < FIG_MIN_SIDE 的（手写误报档）加载后摘除、不展示；
     全部摘除时附图区整体消失，不留空头。加载失败走既有 wireImgFallback 降位框。 */
  function wireProbFigures() {
    var $sec = $app.querySelector('.prob-figs');
    if (!$sec) return;
    $sec.querySelectorAll('.prob-fig img').forEach(function (img) {
      function tooSmall() {
        var w = img.naturalWidth, h = img.naturalHeight;
        return w > 0 && h > 0 && Math.min(w, h) < FIG_MIN_SIDE;
      }
      function drop() {
        var fig = img.closest('.prob-fig');
        if (fig) fig.remove();
        if (!$sec.querySelector('.prob-fig')) $sec.remove();
      }
      if (img.complete) { if (tooSmall()) drop(); }
      else img.addEventListener('load', function () { if (tooSmall()) drop(); });
    });
  }

  function wireLightbox() {
    var $lb = document.getElementById('lightbox');
    var $img = document.getElementById('lightbox-img');
    var $close = document.getElementById('lb-close');
    var $zoom = document.getElementById('lb-zoom');
    var lastFocus = null;

    function open(src, alt) {
      lastFocus = document.activeElement;
      $img.src = src;
      $img.alt = alt || '大图';
      $lb.hidden = false;
      $lb.classList.remove('zoom');
      $zoom.textContent = '按原图大小看';
      $close.focus();
    }
    function close() {
      if ($lb.hidden) return;
      $lb.hidden = true;
      $lb.classList.remove('zoom');
      $img.src = '';
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    function toggleZoom() {
      var z = $lb.classList.toggle('zoom');
      $zoom.textContent = z ? '适应屏幕' : '按原图大小看';
    }
    window.__closeLightbox = close;
    $close.addEventListener('click', close);
    $zoom.addEventListener('click', toggleZoom);
    $lb.addEventListener('click', function (e) { if (e.target === $lb) close(); });
    document.addEventListener('keydown', function (e) {
      if ($lb.hidden) return;
      if (e.key === 'Escape') { e.preventDefault(); close(); }
    });
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (t.tagName === 'IMG' && (t.id === 'q-img' || t.id === 'prob-img' || !!t.closest('.prob-figure') || !!t.closest('.prob-fig'))) {
        open(t.src, t.alt);
      }
    });
  }

  /* ------------------------------------------------ 主题 */

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }
  function paintThemeBtn() {
    var dark = currentTheme() === 'dark';
    $themeLabel.textContent = dark ? '日间' : '夜间';
    $themeBtn.setAttribute('aria-pressed', dark ? 'true' : 'false');
    $themeBtn.setAttribute('aria-label', dark ? '切换到日间模式' : '切换到夜间模式');
  }
  function wireTheme() {
    paintThemeBtn();
    $themeBtn.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('xueji-theme', next); } catch (e) {}
      paintThemeBtn();
    });
  }

  /* ------------------------------------------------ 视图装配 */

  function wireView(kind, route) {
    if (kind === 'teach' && route.parts[1] === 'q') {
      var q = qById(parseInt(route.parts[2], 10));
      $app.querySelectorAll('img').forEach(wireImgFallback);
      if (q) renderExplCard(q);
    } else if (kind === 'teach') {
      wireTeach();
      dropBrokenThumbs();
    } else if (kind === 'crop' && route.parts[1] === 's' && route.parts[3]) {
      $app.querySelectorAll('img').forEach(wireImgFallback);
      wireProbFigures();
    } else if (kind === 'crop' && route.parts[1] === 's') {
      wireSession(decodeURIComponent(route.parts[2]));
      $app.querySelectorAll('img').forEach(wireImgFallback);
    } else if (kind === 'accum' && route.parts[1] === 'b') {
      wireAccumBook();
    } else if (kind === 'kp' && route.parts[1] === 'c') {
      dropBrokenThumbs();
    } else if (kind === undefined || kind === 'growth') {
      /* 近况/成长：档案行缩略图坏了就退回纯文字行，会话缩略图走缺图兜底 */
      dropBrokenThumbs();
      $app.querySelectorAll('.sess-thumbs img').forEach(wireImgFallback);
    } else {
      $app.querySelectorAll('img').forEach(wireImgFallback);
    }
  }

  /* ------------------------------------------------ 页脚 & 启动 */

  function renderFooter() {
    var d = state.data;
    if (!d) return;
    var cv = d.contract_version;
    $footMeta.textContent = '数据更新于 ' + fmtDateTimeCN(d.generated_at) +
      ' · 契约 ' + (cv === undefined || cv === null || cv === '' ? 'v1' : String(cv)) +
      ' · 手机端每 10 分钟同步' + (d.sample ? ' · 样例数据' : '');
  }

  function init() {
    wireLightbox();
    wireTheme();
    window.addEventListener('hashchange', render);
    fetchData()
      .then(function (d) {
        state.data = d;
        var cv = d.contract_version;
        state.contractMismatch = (cv !== undefined && cv !== null && cv !== '' && CONTRACT_COMPAT_VERSIONS.indexOf(String(cv)) < 0);
        buildIndex();
        renderFooter();
        render();
        state.booted = true;
      })
      .catch(function (err) {
        $app.innerHTML = '<div class="err"><b>数据读取失败</b>' + esc(err.message || String(err)) +
          '<ol><li>确认 data/index.json 已经由同步脚本推到站点上；</li>' +
          '<li>确认浏览器已经通过站点认证；</li>' +
          '<li>网络恢复后刷新重试。</li></ol></div>';
      });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
