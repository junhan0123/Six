/* ============================================================================
 * capability-exposure.js — 小6 AI OS Experience Sprint v1.0 · Sprint 3
 * 能力暴露统一真相（Frontend infra，非业务；引用 product-constitution/05）
 * 职责：
 *   - 以产品宪法 05_CAPABILITY_EXPOSURE_RULES §2/§3 的 T0–T4 五档 + 成熟度
 *     （prod/beta/exp/hidden/dead/missing）为唯一分级来源；
 *   - 供 指令中心 / 能力清单视图 / 设置面板 三处统一读取，消除三处重复声明；
 *   - 落地诚实标注：missing/dead 不暴露、exp 标“实验”、beta 标“Beta”。
 * 纪律：零业务逻辑；不新增能力、不改动后端/EventBus/权限。仅做“怎么露”的映射。
 *       经典脚本，暴露 window.CapabilityExposure。
 * ========================================================================== */
(function (global) {
  'use strict';

  // —— 五档暴露级别（单一来源，对齐 05 §2）——
  var TIERS = {
    T0: { key: 'T0', name: '默认展示', desc: '高频低风险核心能力，首屏/常驻可见' },
    T1: { key: 'T1', name: '按需',     desc: '有用但非高频，用户召唤才出现（指令中心/面板按钮）' },
    T2: { key: 'T2', name: '自动',     desc: '后台运行、无需用户操作即生效' },
    T3: { key: 'T3', name: '后台',     desc: '系统/开发者/监控类，普通用户无感' },
    T4: { key: 'T4', name: '专家模式', desc: '高风险/开发者/高级调试，默认隐藏' }
  };

  // —— 成熟度（对齐能力真相 maturity + 05 §4 诚实标注）——
  var MATURITY = {
    prod:    { key: 'prod',    label: '正式',   badge: 'prod',    honest: '' },
    beta:    { key: 'beta',    label: 'Beta',   badge: 'beta',    honest: 'beta' },
    exp:     { key: 'exp',     label: '实验',   badge: 'exp',     honest: 'exp' },
    hidden:  { key: 'hidden',  label: '隐藏',   badge: 'hidden',  honest: 'hidden' },
    dead:    { key: 'dead',    label: '已废弃', badge: 'dead',    honest: 'dead' },
    missing: { key: 'missing', label: '规划中', badge: 'missing', honest: 'missing' }
  };

  // —— 19 分类默认档位（对齐 05 §3 分级映射表；可被单能力覆盖）——
  var CATEGORY_DEFAULTS = {
    Conversation:    { tier: 'T0', maturity: 'prod' },
    Knowledge:       { tier: 'T0', maturity: 'prod' },
    Memory:          { tier: 'T0', maturity: 'prod' },
    Context:         { tier: 'T3', maturity: 'hidden' },
    Execution:       { tier: 'T1', maturity: 'prod' },
    Tools:           { tier: 'T1', maturity: 'prod' },
    Goals:           { tier: 'T0', maturity: 'prod' },
    Computer:        { tier: 'T1', maturity: 'prod' },
    Permission:      { tier: 'T4', maturity: 'prod' },
    Proactive:       { tier: 'T2', maturity: 'prod' },
    Social:          { tier: 'T1', maturity: 'beta' },
    Perception:      { tier: 'T3', maturity: 'exp' },
    External:        { tier: 'T1', maturity: 'prod' },
    CrossDevice:     { tier: 'T4', maturity: 'exp' },
    Personalization: { tier: 'T1', maturity: 'dead' },
    Settings:        { tier: 'T1', maturity: 'prod' },
    System:          { tier: 'T3', maturity: 'prod' },
    UI:              { tier: 'T1', maturity: 'prod' },
    Developer:       { tier: 'T4', maturity: 'prod' }
  };

  // 不暴露的成熟度集合（05 §4：missing/dead 严禁作为可用能力暴露）
  var HIDDEN_MATURITY = { missing: true, dead: true };

  function defaultsFor(category) {
    return CATEGORY_DEFAULTS[category] || { tier: 'T1', maturity: 'prod' };
  }

  /* classify(spec): 计算单能力的暴露描述
   * spec: { category, maturity?, implemented?, tier? }
   * 返回: { tier, maturity, exposed, badge, honest, note } */
  function classify(spec) {
    spec = spec || {};
    var def = defaultsFor(spec.category);
    var maturity = spec.maturity || def.maturity;
    var exposed = !HIDDEN_MATURITY[maturity];
    var tier = exposed ? (spec.tier || def.tier) : 'T4';
    var m = MATURITY[maturity] || MATURITY.prod;
    var note = '';
    if (maturity === 'missing') note = '蓝图能力，仅“规划中”说明，不可作为可用能力暴露';
    else if (maturity === 'dead') note = '已废弃，完全不暴露、不引用';
    else if (maturity === 'exp') note = '实验能力，须注明“实验/模拟数据”';
    else if (maturity === 'beta') note = 'Beta 能力，标注“Beta”，不承诺稳定';
    else if (maturity === 'hidden') note = '隐藏能力，仅专家/开发者模式可见';
    return {
      tier: tier,
      maturity: maturity,
      exposed: exposed,
      badge: m.badge,
      honest: m.honest,
      note: note
    };
  }

  /* tag(item): 给一个 UI 能力项（命令/开关/清单项）附加暴露元数据，便于统一渲染标签
   * item: { category, maturity?, implemented?, label } → 返回带 tier/maturity/exposed 的新对象 */
  function tag(item) {
    var spec = {
      category: item.category,
      maturity: item.maturity,
      implemented: item.implemented,
      tier: item.tier
    };
    var c = classify(spec);
    var out = {};
    for (var k in item) { if (Object.prototype.hasOwnProperty.call(item, k)) out[k] = item[k]; }
    out.tier = c.tier;
    out.maturity = c.maturity;
    out.exposed = c.exposed;
    out.badge = c.badge;
    return out;
  }

  /* computerMap(): 由能力注册表（capability-registry.js）派生电脑能力的暴露描述
   * 不存在时回退内联快照，保证本模块不依赖加载顺序。 */
  function computerMap() {
    var reg = global.ZZCapabilities;
    var map = {};
    if (reg && typeof reg.allCapabilities === 'function') {
      reg.allCapabilities().forEach(function (cap) {
        var maturity = cap.implemented === false ? 'missing' : 'prod';
        map[cap.id] = tag({ category: 'Computer', maturity: maturity, label: cap.label, id: cap.id, risk: cap.risk });
      });
      return map;
    }
    // 回退快照（与 capability-registry.js 对齐）
    [
      { id: 'read_file', label: '读取文件', risk: 'LOW', implemented: true },
      { id: 'capture_screen', label: '截取屏幕', risk: 'LOW', implemented: true },
      { id: 'get_window_info', label: '获取窗口信息', risk: 'LOW', implemented: true },
      { id: 'list_process', label: '列举进程', risk: 'LOW', implemented: true },
      { id: 'open_application', label: '打开应用', risk: 'MEDIUM', implemented: true },
      { id: 'focus_window', label: '聚焦窗口', risk: 'MEDIUM', implemented: true },
      { id: 'browser_navigate', label: '浏览器导航', risk: 'MEDIUM', implemented: true },
      { id: 'modify_file', label: '修改文件', risk: 'HIGH', implemented: false },
      { id: 'execute_command', label: '执行命令', risk: 'HIGH', implemented: false },
      { id: 'kill_process', label: '结束进程', risk: 'HIGH', implemented: false },
      { id: 'delete', label: '删除', risk: 'CRITICAL', implemented: false },
      { id: 'system', label: '系统操作', risk: 'CRITICAL', implemented: false },
      { id: 'network', label: '网络操作', risk: 'CRITICAL', implemented: false }
    ].forEach(function (cap) {
      var maturity = cap.implemented ? 'prod' : 'missing';
      map[cap.id] = tag({ category: 'Computer', maturity: maturity, label: cap.label, id: cap.id, risk: cap.risk });
    });
    return map;
  }

  global.CapabilityExposure = {
    TIERS: TIERS,
    MATURITY: MATURITY,
    CATEGORY_DEFAULTS: CATEGORY_DEFAULTS,
    classify: classify,
    tag: tag,
    computerMap: computerMap,
    tierLabel: function (t) { return TIERS[t] ? TIERS[t].name : t; },
    maturityLabel: function (m) { return MATURITY[m] ? MATURITY[m].label : m; },
    isExposed: function (m) { return !HIDDEN_MATURITY[m]; }
  };
})(window);
