/**
 * work_health.js — Task Health Layer (PHASE 128.2)
 * 
 * 职责：纯前端任务健康度计算与风险提示
 * 原则：只读已有字段，不猜测状态，不修改 S.tasks
 * 
 * 数据来源：
 *   - status: 任务状态字符串
 *   - updated_at / updated: 最后更新时间
 *   - current_step / total_steps: 步骤进度
 *   - history: 执行历史（可选）
 */

// ============================================================
// 健康度状态常量
// ============================================================
const HEALTH = {
  GOOD: 'GOOD',
  WARNING: 'WARNING',
  STALE: 'STALE',
  FAILED: 'FAILED'
};

// 运行时状态集合（与 wxRUNNING 保持一致）
const RUNNING_STATUS = ['open', 'running', 'in_progress', 'active', 'pending'];
const DONE_STATUS = ['done', 'completed', 'finished', 'success'];
const FAILED_STATUS = ['failed', 'error', 'failure'];

// ============================================================
// 核心函数
// ============================================================

/**
 * 计算任务健康度
 * @param {Object} task - 任务对象
 * @returns {{ status: string, reason: string }}
 */
function calculateHealth(task) {
  if (!task || !task.id) {
    return { status: HEALTH.GOOD, reason: '' };
  }

  const status = String(task.status || '').toLowerCase();
  const updated = task.updated || task.updated_at;
  
  // 已失败任务直接标记
  if (FAILED_STATUS.some(s => status.includes(s))) {
    return { status: HEALTH.FAILED, reason: '任务失败需要处理' };
  }

  // 已完成任务
  if (DONE_STATUS.some(s => status.includes(s))) {
    return { status: HEALTH.GOOD, reason: '任务正常完成' };
  }

  // 运行中任务：检查是否停滞
  if (RUNNING_STATUS.some(s => status.includes(s))) {
    // 如果有更新时间，检查是否长时间无更新
    if (updated) {
      const hoursSinceUpdate = hoursSince(updated);
      
      // 检查是否有步骤进度
      const currentStep = task.current_step || 0;
      const totalSteps = task.total_steps || 0;
      const hasProgress = totalSteps > 0 && currentStep > 0;
      
      if (hoursSinceUpdate >= 72 && !hasProgress) {
        return { 
          status: HEALTH.STALE, 
          reason: `任务超过72小时没有进度更新` 
        };
      }
      
      if (hoursSinceUpdate >= 24 && !hasProgress) {
        return { 
          status: HEALTH.WARNING, 
          reason: `任务24小时无进度更新` 
        };
      }
    }

    // 正常运行
    return { status: HEALTH.GOOD, reason: '任务正在正常推进' };
  }

  // 等待执行的任务
  return { status: HEALTH.GOOD, reason: '任务等待执行' };
}

/**
 * 获取时间戳距现在的小时数
 * @param {string|number} timestamp - ISO 时间字符串或时间戳
 * @returns {number} 小时数
 */
function hoursSince(timestamp) {
  if (!timestamp) return 0;
  
  let date;
  if (typeof timestamp === 'string') {
    date = new Date(timestamp);
  } else if (typeof timestamp === 'number') {
    date = new Date(timestamp * 1000); // 假设是秒级时间戳
  }
  
  if (isNaN(date.getTime())) return 0;
  
  const now = new Date();
  const diffMs = now - date;
  return Math.floor(diffMs / (1000 * 60 * 60));
}

/**
 * 生成健康度 HTML 标签
 * @param {Object} task - 任务对象
 * @returns {string} HTML 字符串
 */
function healthBadge(task) {
  const { status, reason } = calculateHealth(task);
  
  const icons = {
    [HEALTH.GOOD]: '✓',
    [HEALTH.WARNING]: '⚠',
    [HEALTH.STALE]: '⏸',
    [HEALTH.FAILED]: '✗'
  };
  
  const classes = {
    [HEALTH.GOOD]: 'health-good',
    [HEALTH.WARNING]: 'health-warning',
    [HEALTH.STALE]: 'health-stale',
    [HEALTH.FAILED]: 'health-failed'
  };
  
  return `<span class="health-badge ${classes[status]}" title="${esc(reason)}">${icons[status]}</span>`;
}

// 简易转义函数（如果全局未定义）
function esc(str) {
  if (typeof str !== 'string') str = String(str || '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ============================================================
// 导出（兼容模块系统和全局变量）
// ============================================================
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { HEALTH, calculateHealth, hoursSince, healthBadge };
} else {
  window.WorkHealth = { HEALTH, calculateHealth, hoursSince, healthBadge };
}
