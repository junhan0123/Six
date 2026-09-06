/**
 * work_filters.js — Task Query Layer (PHASE 128.2)
 * 
 * 职责：统一的任务过滤逻辑，支持多种视图模式
 * 原则：纯函数，不修改原始数据，基于 localStorage
 */

// ============================================================
// localStorage 键
// ============================================================
const STORAGE_KEYS = {
  WATCHED: 'xiao6.watched_tasks',
  RECENT_OPEN: 'xiao6.recent_open',
  RECENT_DONE: 'xiao6.recent_done',
  RECENT_FAILED: 'xiao6.recent_failed'
};

// ============================================================
// 关注功能
// ============================================================

/**
 * 获取关注的任务 ID 列表
 */
function getWatchedTasks() {
  try {
    const data = localStorage.getItem(STORAGE_KEYS.WATCHED);
    return data ? JSON.parse(data) : [];
  } catch (e) {
    return [];
  }
}

/**
 * 切换任务关注状态
 * @param {string} taskId - 任务 ID
 * @returns {boolean} 是否已关注
 */
function toggleWatchTask(taskId) {
  const watched = getWatchedTasks();
  const index = watched.indexOf(taskId);

  if (index >= 0) {
    watched.splice(index, 1);
    saveWatchedTasks(watched); // 修复：保存取消关注
    return false;
  } else {
    watched.push(taskId);
    saveWatchedTasks(watched);
    return true;
  }
}

/**
 * 保存关注列表
 */
function saveWatchedTasks(watched) {
  try {
    localStorage.setItem(STORAGE_KEYS.WATCHED, JSON.stringify(watched));
  } catch (e) {
    console.warn('保存关注列表失败:', e);
  }
}

/**
 * 检查任务是否被关注
 */
function isTaskWatched(taskId) {
  return getWatchedTasks().includes(taskId);
}

// ============================================================
// 最近工作记录
// ============================================================

/**
 * 记录最近打开的任务
 */
function recordOpenTask(taskId, timestamp) {
  const recent = getRecentWork(STORAGE_KEYS.RECENT_OPEN);
  const now = timestamp || Date.now();
  
  // 移除旧的记录
  const filtered = recent.filter(item => item.id !== taskId);
  
  // 添加新的记录
  filtered.unshift({ id: taskId, time: now });
  
  // 只保留最近 10 条
  saveRecentWork(STORAGE_KEYS.RECENT_OPEN, filtered.slice(0, 10));
}

/**
 * 记录完成的任务
 */
function recordDoneTask(taskId, timestamp) {
  const recent = getRecentWork(STORAGE_KEYS.RECENT_DONE);
  const now = timestamp || Date.now();
  
  const filtered = recent.filter(item => item.id !== taskId);
  filtered.unshift({ id: taskId, time: now });
  
  saveRecentWork(STORAGE_KEYS.RECENT_DONE, filtered.slice(0, 10));
}

/**
 * 记录失败的任务
 */
function recordFailedTask(taskId, timestamp) {
  const recent = getRecentWork(STORAGE_KEYS.RECENT_FAILED);
  const now = timestamp || Date.now();
  
  const filtered = recent.filter(item => item.id !== taskId);
  filtered.unshift({ id: taskId, time: now });
  
  saveRecentWork(STORAGE_KEYS.RECENT_FAILED, filtered.slice(0, 10));
}

/**
 * 获取最近工作记录
 */
function getRecentWork(key) {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : [];
  } catch (e) {
    return [];
  }
}

/**
 * 保存最近工作记录
 */
function saveRecentWork(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.warn('保存最近工作记录失败:', e);
  }
}

/**
 * 格式化时间
 */
function formatRelativeTime(timestamp) {
  if (!timestamp) return '';

  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;

  return new Date(timestamp).toLocaleDateString('zh-CN');
}

// ============================================================
// 最近工作查询
// ============================================================

/**
 * 获取最近工作列表（合并三个维度）
 * @param {Array} tasks - 任务数组
 * @param {number} limit - 返回数量限制
 * @returns {Array} 去重后的任务数组
 */
function getRecentTasks(tasks, limit = 20) {
  if (!Array.isArray(tasks)) return [];

  const allRecent = [
    ...getRecentWork(STORAGE_KEYS.RECENT_OPEN),
    ...getRecentWork(STORAGE_KEYS.RECENT_DONE),
    ...getRecentWork(STORAGE_KEYS.RECENT_FAILED)
  ];

  // 去重，保留最新的记录
  const seen = new Set();
  const unique = allRecent.filter(item => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });

  // 获取任务详情
  return unique.slice(0, limit).map(item => {
    const task = tasks.find(t => String(t.id) === String(item.id));
    return task ? { ...task, lastOpened: item.time } : null;
  }).filter(Boolean);
}

/**
 * 检查任务是否在最近打开列表中
 * @param {string} taskId - 任务ID
 * @returns {boolean}
 */
function isTaskRecentlyOpened(taskId) {
  const recent = getRecentWork(STORAGE_KEYS.RECENT_OPEN);
  return recent.some(item => String(item.id) === String(taskId));
}

// ============================================================
// 统一过滤层
// ============================================================

/**
 * 任务过滤器
 * @param {Array} tasks - 任务数组
 * @param {Object} options - 过滤选项
 * @param {string} options.mode - 过滤模式: 'all', 'run', 'done', 'failed', 'watched', 'recent_open', 'recent_done', 'recent_failed'
 * @returns {Array} 过滤后的任务数组
 */
function filterTasks(tasks, options = {}) {
  if (!Array.isArray(tasks)) return [];
  
  const { mode = 'all' } = options;
  
  // 基础状态过滤
  const baseFilter = {
    all: () => true,
    run: (t) => ['open', 'running', 'in_progress', 'active', 'pending'].some(s => 
      String(t.status || '').toLowerCase().includes(s)
    ),
    done: (t) => ['done', 'completed', 'finished', 'success'].some(s => 
      String(t.status || '').toLowerCase().includes(s)
    ),
    failed: (t) => ['failed', 'error', 'failure'].some(s => 
      String(t.status || '').toLowerCase().includes(s)
    )
  };
  
  let result = tasks.filter(baseFilter[mode] || baseFilter.all);
  
  // 关注过滤
  if (mode === 'watched') {
    const watched = getWatchedTasks();
    result = result.filter(t => watched.includes(t.id));
  }
  
  // 最近工作视图（从历史记录中查找任务）
  if (mode === 'recent_open' || mode === 'recent_done' || mode === 'recent_failed') {
    const key = mode === 'recent_open' ? STORAGE_KEYS.RECENT_OPEN :
                mode === 'recent_done' ? STORAGE_KEYS.RECENT_DONE :
                STORAGE_KEYS.RECENT_FAILED;
    
    const recentIds = getRecentWork(key).map(item => item.id);
    result = tasks.filter(t => recentIds.includes(t.id));
  }
  
  return result;
}

// ============================================================
// 导出
// ============================================================
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    STORAGE_KEYS,
    getWatchedTasks,
    toggleWatchTask,
    isTaskWatched,
    recordOpenTask,
    recordDoneTask,
    recordFailedTask,
    getRecentWork,
    formatRelativeTime,
    filterTasks,
    getRecentTasks,
    isTaskRecentlyOpened
  };
} else {
  window.WorkFilters = {
    STORAGE_KEYS,
    getWatchedTasks,
    toggleWatchTask,
    isTaskWatched,
    recordOpenTask,
    recordDoneTask,
    recordFailedTask,
    getRecentWork,
    formatRelativeTime,
    filterTasks,
    getRecentTasks,
    isTaskRecentlyOpened
  };
}
