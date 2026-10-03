// ============ STATE MANAGEMENT ============
const state = {
  currentUser: null,
  activeAdminFilter: 'ALL',
  activeAnalystFilter: 'ALL',
  adminTab: 'logs',
  adminPage: 1,
  analystPage: 1,
  adminTotalPages: 10,
  analystTotalPages: 10
};
let refreshInterval = null;

// ============ INITIALIZATION ============
function init() {
  const savedUser = localStorage.getItem('secureAuthUser');
  if (savedUser) {
    try {
      state.currentUser = JSON.parse(savedUser);
      routeDashboard(state.currentUser);
    } catch (e) {
      localStorage.removeItem('secureAuthUser');
    }
  }
}

function quickFill(username, password) {
  document.getElementById('username').value = username;
  document.getElementById('password').value = password;
}

// ============ LOGIN HANDLER ============
async function handleLogin(e) {
  e.preventDefault();
  
  const student_id = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const btn = document.getElementById('loginBtn');
  const btnText = document.getElementById('loginBtnText');
  const spinner = document.getElementById('loginSpinner');
  
  btn.disabled = true;
  btnText.textContent = '인증 진행 중 (Verifying)...';
  spinner.classList.remove('hidden');
  
  try {
    const response = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: student_id, password: password })
    });

    const result = await response.json();

    if (response.ok && result.status === "SUCCESS") {
      state.currentUser = result.user || { student_id: student_id, role: 'Student', full_name: student_id };
      localStorage.setItem('secureAuthUser', JSON.stringify(state.currentUser));
      
      showToast('success', '성공!', result.message);
      routeDashboard(state.currentUser);
    } else if (response.status === 403 && result.status === "ACCOUNT_SUSPENDED") {
      showToast('warn', '계정 정지 / 비활성화 (SUSPENDED)', result.message || '이메일 2FA 인증으로 비밀번호를 변경하고 계정을 복구하세요.');
      if (result.can_2fa_recover) {
        open2FAModal(result.student_id || student_id, result.email || '');
      } else {
        showBlockedPage(result.message);
      }
    } else if (response.status === 429 || result.status === "MALICIOUS_ATTACK_BLOCKED") {
      showToast('error', '접근 차단 (BLOCKED)!', result.message || '보안 시스템에 의해 차단되었습니다.');
      showBlockedPage(result.message);
    } else {
      const form = document.getElementById('loginForm');
      form.classList.add('shake');
      setTimeout(() => form.classList.remove('shake'), 600);
      showToast('error', '로그인 실패', result.message || '인증 정보가 일치하지 않습니다.');
    }
  } catch (error) {
    console.error('서버 연결 오류:', error);
    showToast('error', '연결 오류', '서버에 연결할 수 없습니다.');
  } finally {
    btn.disabled = false;
    btnText.textContent = '로그인 (Login)';
    spinner.classList.add('hidden');
  }
}

// ============ ROUTING BASED ON USER ROLE ============
function routeDashboard(user) {
  document.getElementById('loginPage').classList.add('hidden');
  document.getElementById('blockedPage').classList.add('hidden');
  document.getElementById('userDashboardPage').classList.add('hidden');
  document.getElementById('analystDashboardPage').classList.add('hidden');
  document.getElementById('adminDashboardPage').classList.add('hidden');
  
  if (refreshInterval) clearInterval(refreshInterval);

  if (user.role === 'Admin') {
    document.getElementById('adminDashboardPage').classList.remove('hidden');
    loadAdminDashboard(user);
    refreshInterval = setInterval(() => {
      if (state.adminTab === 'logs') {
        loadAdminStats();
        loadAdminLogs();
      }
    }, 5000);
  } else if (user.role === 'Analyst') {
    document.getElementById('analystDashboardPage').classList.remove('hidden');
    loadAnalystDashboard(user);
    refreshInterval = setInterval(() => {
      loadAnalystAnalytics();
      loadAnalystLogs();
    }, 5000);
  } else {
    document.getElementById('userDashboardPage').classList.remove('hidden');
    loadUserDashboard(user);
    refreshInterval = setInterval(() => {
      loadUserLogs();
    }, 5000);
  }
}

// ============ USER DASHBOARD ============
async function loadUserDashboard(user) {
  document.getElementById('uFullName').textContent = user.full_name || user.student_id;
  document.getElementById('uWelcomeName').textContent = user.full_name || user.student_id;
  document.getElementById('uStudentId').textContent = user.student_id;
  document.getElementById('uEmail').textContent = user.email || 'N/A';
  document.getElementById('uRoleBadge').textContent = user.role || 'Student';
  document.getElementById('uAccountStatus').textContent = user.status || 'ACTIVE';

  await loadUserLogs();
}

async function loadUserLogs() {
  const container = document.getElementById('userLogsTable');
  if (!state.currentUser) return;
  
  try {
    const res = await fetch(`/api/user/logs?student_id=${encodeURIComponent(state.currentUser.student_id)}`);
    const data = await res.json();
    
    if (data.status === "SUCCESS" && data.logs.length > 0) {
      container.innerHTML = data.logs.map(log => {
        const timeStr = new Date(log.timestamp).toLocaleString('ko-KR');
        const statusBadge = log.status === 'SUCCESS' 
          ? '<span class="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-xs">SUCCESS</span>'
          : log.status === 'BLOCKED'
          ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-bold">BLOCKED</span>'
          : '<span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs">FAILED</span>';
          
        return `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="py-3 px-4 mono text-xs text-slate-400">${timeStr}</td>
            <td class="py-3 px-4 mono text-xs text-slate-300">${log.ip_address}</td>
            <td class="py-3 px-4">${statusBadge}</td>
            <td class="py-3 px-4 text-xs text-slate-400 truncate max-w-[200px]">${log.user_agent}</td>
          </tr>
        `;
      }).join('');
    } else {
      container.innerHTML = '<tr><td colspan="4" class="text-center py-6 text-slate-500">등록된 로그인 이력이 없습니다.</td></tr>';
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="4" class="text-center py-6 text-red-400">로그를 불러오는 중 오류가 발생했습니다.</td></tr>';
  }
}

// ============ SECURITY ANALYST DASHBOARD ============
async function loadAnalystDashboard(user) {
  document.getElementById('anFullName').textContent = user.full_name || user.student_id;
  document.getElementById('anStudentId').textContent = user.student_id;
  document.getElementById('anRoleBadge').textContent = user.role || 'ANALYST';

  await loadAnalystAnalytics();
  await loadAnalystLogs();
}

async function loadAnalystAnalytics() {
  try {
    const res = await fetch('/api/analyst/analytics');
    const data = await res.json();
    
    if (data.status === "SUCCESS") {
      const counts = data.attack_counts;
      document.getElementById('anCountIpRotation').textContent = counts.ip_rotation || 0;
      document.getElementById('anCountPasswordSpraying').textContent = counts.password_spraying || 0;
      document.getElementById('anCountBruteForce').textContent = counts.brute_force || 0;
      document.getElementById('anCountBotTraffic').textContent = counts.bot_traffic || 0;

      // Render Top Threat Targets
      const targetsList = document.getElementById('anTopTargetsList');
      if (data.top_target_users && data.top_target_users.length > 0) {
        targetsList.innerHTML = data.top_target_users.map(t => `
          <div class="flex items-center justify-between bg-slate-900/80 px-3 py-2 rounded-lg border border-purple-500/20">
            <span class="mono text-xs text-purple-300 font-semibold">${t.student_id}</span>
            <span class="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs">${t.count}회 시도</span>
          </div>
        `).join('');
      } else {
        targetsList.innerHTML = '<p class="text-xs text-slate-500 text-center py-2">최근 공격을 받은 계정이 없습니다.</p>';
      }

      // Render Top Threat IPs
      const ipsList = document.getElementById('anTopIpsList');
      if (data.top_threat_ips && data.top_threat_ips.length > 0) {
        ipsList.innerHTML = data.top_threat_ips.map(ip => `
          <div class="flex items-center justify-between bg-slate-900/80 px-3 py-2 rounded-lg border border-red-500/20">
            <span class="mono text-xs text-red-300 font-semibold">${ip.ip}</span>
            <span class="px-2 py-0.5 bg-red-500/20 text-red-300 rounded text-xs font-bold">${ip.count}회 요청</span>
          </div>
        `).join('');
      } else {
        ipsList.innerHTML = '<p class="text-xs text-slate-500 text-center py-2">고위험 IP가 탐지되지 않았습니다.</p>';
      }
    }
  } catch (err) {
    console.error('Analyst analytics loading error:', err);
  }
}

async function filterAnalystLogs(filterType) {
  state.activeAnalystFilter = filterType;
  state.analystPage = 1;
  
  const buttons = [
    { id: 'anFilterALL', val: 'ALL' },
    { id: 'anFilterBLOCKED', val: 'BLOCKED' },
    { id: 'anFilterIpRot', val: 'IP Rotation Spraying' },
    { id: 'anFilterPassSpray', val: 'Password Spraying' },
    { id: 'anFilterBrute', val: 'Brute Force / DoS' }
  ];
  
  buttons.forEach(b => {
    const el = document.getElementById(b.id);
    if (el) {
      if (b.val === filterType) {
        el.className = 'px-2.5 py-1 font-semibold rounded bg-purple-600 text-white';
      } else {
        el.className = 'px-2.5 py-1 font-semibold rounded text-slate-400 hover:text-white';
      }
    }
  });

  await loadAnalystLogs();
}

async function loadAnalystLogs() {
  const container = document.getElementById('analystLogsTable');
  
  try {
    const res = await fetch(`/api/admin/logs?status=${encodeURIComponent(state.activeAnalystFilter)}&page=${state.analystPage}&per_page=100`);
    const data = await res.json();
    
    if (data.status === "SUCCESS" && data.logs.length > 0) {
      state.analystTotalPages = data.total_pages || 1;
      renderPagination('an', state.analystPage, state.analystTotalPages, data.total_records, setAnalystPage);

      container.innerHTML = data.logs.map(log => {
        const timeStr = new Date(log.timestamp).toLocaleString('ko-KR');
        const statusBadge = log.status === 'SUCCESS' 
          ? '<span class="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-xs">SUCCESS</span>'
          : log.status === 'BLOCKED'
          ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-bold">BLOCKED</span>'
          : '<span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs">FAILED</span>';

        const attType = log.attack_type || "LEGITIMATE";
        const attBadge = attType === 'IP Rotation Spraying'
          ? '<span class="px-2 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded text-xs font-bold">🌐 IP Rotation</span>'
          : attType === 'Password Spraying'
          ? '<span class="px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded text-xs font-bold">🔑 Pass Spraying</span>'
          : attType === 'Brute Force / DoS'
          ? '<span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs font-bold">⚡ Brute Force</span>'
          : attType === 'Automated Bot Traffic'
          ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-bold">🤖 Bot Script</span>'
          : '<span class="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-xs">Legitimate</span>';

        return `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="py-3 px-3 mono text-xs text-slate-400">${timeStr}</td>
            <td class="py-3 px-3 mono text-xs font-semibold text-slate-200">${log.student_id}</td>
            <td class="py-3 px-3 mono text-xs text-slate-300">${log.ip_address}</td>
            <td class="py-3 px-3">${statusBadge}</td>
            <td class="py-3 px-3">${attBadge}</td>
            <td class="py-3 px-3 mono text-xs ${log.risk_score >= 50 ? 'text-red-400 font-bold' : 'text-emerald-400'}">${log.risk_score}%</td>
          </tr>
        `;
      }).join('');
    } else {
      container.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-500">로그 데이터가 없습니다.</td></tr>`;
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-red-400">분석 로그를 불러오는 중 오류가 발생했습니다.</td></tr>';
  }
}

function setAnalystPage(p) {
  if (p < 1 || p > state.analystTotalPages) return;
  state.analystPage = p;
  loadAnalystLogs();
}

function searchAnalystLogs() {
  const query = document.getElementById('anSearchInput').value.toLowerCase();
  const rows = document.querySelectorAll('#analystLogsTable tr');
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

// ============ ADMIN DASHBOARD ============
async function loadAdminDashboard(user) {
  document.getElementById('aFullName').textContent = user.full_name || user.student_id;
  document.getElementById('aStudentId').textContent = user.student_id;
  document.getElementById('aRoleBadge').textContent = user.role || 'ADMIN';

  if (state.adminTab === 'logs') {
    await loadAdminStats();
    await loadAdminLogs();
  } else {
    await loadAdminUsers();
  }
}

function switchAdminTab(tab) {
  state.adminTab = tab;
  const logsTab = document.getElementById('adminTabLogs');
  const usersTab = document.getElementById('adminTabUsers');
  const btnLogs = document.getElementById('tabBtnLogs');
  const btnUsers = document.getElementById('tabBtnUsers');

  if (tab === 'logs') {
    logsTab.classList.remove('hidden');
    usersTab.classList.add('hidden');
    btnLogs.className = 'px-4 py-2 font-bold text-sm text-emerald-400 border-b-2 border-emerald-500 flex items-center gap-2';
    btnUsers.className = 'px-4 py-2 font-bold text-sm text-slate-400 hover:text-slate-200 flex items-center gap-2';
    loadAdminStats();
    loadAdminLogs();
  } else {
    logsTab.classList.add('hidden');
    usersTab.classList.remove('hidden');
    btnUsers.className = 'px-4 py-2 font-bold text-sm text-emerald-400 border-b-2 border-emerald-500 flex items-center gap-2';
    btnLogs.className = 'px-4 py-2 font-bold text-sm text-slate-400 hover:text-slate-200 flex items-center gap-2';
    loadAdminUsers();
  }
}

async function loadAdminStats() {
  try {
    const res = await fetch('/api/admin/stats');
    const stats = await res.json();
    
    if (stats.status === "SUCCESS") {
      document.getElementById('admTotalTraffic').textContent = stats.total_traffic;
      document.getElementById('admTotalSuccess').textContent = stats.total_success;
      document.getElementById('admTotalFailed').textContent = stats.total_failed;
      document.getElementById('admTotalBlocked').textContent = stats.total_blocked;
      
      const blockedList = document.getElementById('blockedIpsList');
      if (stats.blocked_ips && stats.blocked_ips.length > 0) {
        blockedList.innerHTML = stats.blocked_ips.map(ip => `
          <div class="flex items-center justify-between bg-slate-900/90 px-3 py-2 rounded-lg border border-red-500/30">
            <span class="mono text-xs text-red-300">${ip}</span>
            <button onclick="unblockTarget('${ip}')" class="px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-300 border border-emerald-500/40 rounded text-[11px] font-medium transition">
              차단 해제 (Unblock)
            </button>
          </div>
        `).join('');
      } else {
        blockedList.innerHTML = '<p class="text-xs text-slate-500 text-center py-2">현재 차단된 IP가 없습니다.</p>';
      }
    }
  } catch (err) {
    console.error('Admin stats loading error:', err);
  }
}

async function filterAdminLogs(filterType) {
  state.activeAdminFilter = filterType;
  state.adminPage = 1;
  ['ALL', 'SUCCESS', 'FAILED', 'BLOCKED'].forEach(f => {
    const btn = document.getElementById('btnFilter' + f);
    if (btn) {
      if (f === filterType) {
        btn.className = 'px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-500 text-white';
      } else {
        btn.className = 'px-2.5 py-1 text-xs font-semibold rounded-md text-slate-400 hover:text-white';
      }
    }
  });
  
  await loadAdminLogs();
}

async function loadAdminLogs() {
  const container = document.getElementById('adminLogsTable');
  
  try {
    const res = await fetch(`/api/admin/logs?status=${encodeURIComponent(state.activeAdminFilter)}&page=${state.adminPage}&per_page=100`);
    const data = await res.json();
    
    if (data.status === "SUCCESS" && data.logs.length > 0) {
      state.adminTotalPages = data.total_pages || 1;
      renderPagination('adm', state.adminPage, state.adminTotalPages, data.total_records, setAdminPage);

      container.innerHTML = data.logs.map(log => {
        const timeStr = new Date(log.timestamp).toLocaleString('ko-KR');
        const statusBadge = log.status === 'SUCCESS' 
          ? '<span class="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-xs">SUCCESS</span>'
          : log.status === 'BLOCKED'
          ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-bold">BLOCKED</span>'
          : log.status === 'UNBLOCKED_BY_ADMIN'
          ? '<span class="px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded text-xs font-bold">UNBLOCKED</span>'
          : '<span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs">FAILED</span>';
          
        return `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="py-3 px-3 mono text-xs text-slate-400">${timeStr}</td>
            <td class="py-3 px-3 mono text-xs font-semibold text-slate-200">${log.student_id}</td>
            <td class="py-3 px-3 mono text-xs text-slate-300">${log.ip_address}</td>
            <td class="py-3 px-3">${statusBadge}</td>
            <td class="py-3 px-3 mono text-xs ${log.risk_score >= 50 ? 'text-red-400 font-bold' : 'text-emerald-400'}">${log.risk_score}%</td>
          </tr>
        `;
      }).join('');
    } else {
      container.innerHTML = `<tr><td colspan="5" class="text-center py-6 text-slate-500">'${state.activeAdminFilter}' 상태의 로그가 없습니다.</td></tr>`;
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="5" class="text-center py-6 text-red-400">시스템 로그를 불러오는 중 오류가 발생했습니다.</td></tr>';
  }
}

function setAdminPage(p) {
  if (p < 1 || p > state.adminTotalPages) return;
  state.adminPage = p;
  loadAdminLogs();
}

function renderPagination(prefix, currentPage, totalPages, totalRecords, callback) {
  const infoEl = document.getElementById(prefix + 'PaginationInfo');
  const controlsEl = document.getElementById(prefix + 'PaginationControls');
  
  if (infoEl) {
    infoEl.textContent = `페이지 ${currentPage} / ${totalPages} (총 ${totalRecords.toLocaleString()}건 Log)`;
  }
  
  if (!controlsEl) return;
  
  let html = '';
  html += `<button onclick="${callback.name}(${currentPage - 1})" ${currentPage === 1 ? 'disabled class="px-2 py-1 bg-slate-900 text-slate-600 rounded text-xs cursor-not-allowed"' : 'class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium"'}>&laquo; 이전</button>`;
  
  for (let i = 1; i <= Math.min(10, totalPages); i++) {
    if (i === currentPage) {
      html += `<button class="px-2.5 py-1 bg-emerald-500 text-white font-bold rounded text-xs">${i}</button>`;
    } else {
      html += `<button onclick="${callback.name}(${i})" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs">${i}</button>`;
    }
  }
  
  html += `<button onclick="${callback.name}(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled class="px-2 py-1 bg-slate-900 text-slate-600 rounded text-xs cursor-not-allowed"' : 'class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium"'}>다음 &raquo;</button>`;
  
  controlsEl.innerHTML = html;
}

// ============ ADMIN UNBLOCK ACTION ============
async function submitAdminUnblock() {
  const target = document.getElementById('unblockInput').value.trim();
  if (!target) {
    showToast('warn', '알림', '해제할 IP 주소를 입력하세요.');
    return;
  }
  await unblockTarget(target);
  document.getElementById('unblockInput').value = '';
}

async function unblockTarget(target) {
  try {
    const res = await fetch('/api/admin/unblock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        target: target,
        requester_role: state.currentUser ? state.currentUser.role : 'Student'
      })
    });
    
    const data = await res.json();
    if (res.ok && data.status === "SUCCESS") {
      showToast('success', '차단 해제 성공!', data.message);
      await loadAdminDashboard(state.currentUser);
    } else {
      showToast('error', '권한 제한', data.error || '차단을 해제할 수 없습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', 'IP 차단 해제 요청 실패');
  }
}

// ============ ADMIN USER MANAGEMENT ============
async function loadAdminUsers() {
  const container = document.getElementById('usersTableBody');
  const search = document.getElementById('userSearchInput').value.trim();
  const role = document.getElementById('userRoleFilter').value;
  const status = document.getElementById('userStatusFilter').value;
  
  try {
    const res = await fetch(`/api/admin/users?search=${encodeURIComponent(search)}&role=${encodeURIComponent(role)}&status=${encodeURIComponent(status)}`);
    const data = await res.json();
    
    if (data.status === "SUCCESS" && data.users.length > 0) {
      container.innerHTML = data.users.map(u => {
        const isPrimaryAdmin = u.student_id === 'admin';

        const roleBadge = u.role === 'Admin'
          ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-bold">Admin</span>'
          : u.role === 'Analyst'
          ? '<span class="px-2 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded text-xs font-bold">Analyst</span>'
          : u.role === 'Instructor'
          ? '<span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs">Instructor</span>'
          : '<span class="px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded text-xs">Student</span>';

        const statusBadge = u.status === 'ACTIVE'
          ? '<span class="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-xs font-semibold">ACTIVE</span>'
          : '<span class="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-semibold">SUSPENDED</span>';

        const nextStatus = u.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
        const statusBtnText = u.status === 'ACTIVE' ? '🚫 정지 (Suspend)' : '✅ 해제 (Activate)';
        const statusBtnClass = u.status === 'ACTIVE'
          ? 'px-2 py-1 bg-amber-500/20 hover:bg-amber-500/40 text-amber-300 border border-amber-500/40 rounded text-[11px]'
          : 'px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-300 border border-emerald-500/40 rounded text-[11px]';

        return `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="py-3 px-3 mono text-xs font-bold text-slate-100">${u.student_id}</td>
            <td class="py-3 px-3 text-xs text-slate-200 font-medium">${u.full_name || '—'}</td>
            <td class="py-3 px-3 text-xs text-slate-400 truncate max-w-[150px]">${u.email || '—'}</td>
            <td class="py-3 px-3">
              ${isPrimaryAdmin ? `
                <span class="px-2.5 py-1 bg-red-500/20 text-red-300 border border-red-500/30 rounded text-xs font-bold opacity-80 cursor-not-allowed" title="최고 관리자 계정 보호">🔑 Admin (Protected)</span>
              ` : `
                <select onchange="updateUserRole('${u.student_id}', this.value)" class="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500">
                  <option value="Student" ${u.role === 'Student' ? 'selected' : ''}>Student</option>
                  <option value="Analyst" ${u.role === 'Analyst' ? 'selected' : ''}>Analyst</option>
                  <option value="Instructor" ${u.role === 'Instructor' ? 'selected' : ''}>Instructor</option>
                  <option value="Admin" ${u.role === 'Admin' ? 'selected' : ''}>Admin</option>
                </select>
              `}
            </td>
            <td class="py-3 px-3">${statusBadge}</td>
            <td class="py-3 px-3 text-right flex items-center justify-end gap-2">
              ${isPrimaryAdmin ? `
                <span class="px-2 py-1 bg-slate-800 text-slate-500 rounded text-[11px] font-medium cursor-not-allowed">🔒 Protected Mode</span>
              ` : `
                <button onclick="toggleUserStatus('${u.student_id}', '${nextStatus}')" class="${statusBtnClass}">${statusBtnText}</button>
                <button onclick="deleteUserAccount('${u.student_id}')" class="px-2 py-1 bg-red-500/20 hover:bg-red-500/40 text-red-300 border border-red-500/40 rounded text-[11px]">🗑️ 삭제</button>
              `}
            </td>
          </tr>
        `;
      }).join('');
    } else {
      container.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-500">검색 조건에 일치하는 사용자가 없습니다.</td></tr>`;
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-red-400">사용자 목록을 불러올 수 없습니다.</td></tr>';
  }
}

function openAddUserModal() {
  document.getElementById('addUserModal').classList.remove('hidden');
}

function closeAddUserModal() {
  document.getElementById('addUserModal').classList.add('hidden');
}

async function submitAddUser(e) {
  e.preventDefault();
  
  const student_id = document.getElementById('newStudentId').value.trim();
  const password = document.getElementById('newPassword').value.trim();
  const full_name = document.getElementById('newFullName').value.trim();
  const email = document.getElementById('newEmail').value.trim();
  const role = document.getElementById('newRole').value;
  const status = document.getElementById('newStatus').value;
  
  try {
    const res = await fetch('/api/admin/users/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: student_id,
        password: password,
        full_name: full_name,
        email: email,
        role: role,
        status: status
      })
    });
    
    const data = await res.json();
    if (res.ok && data.status === "SUCCESS") {
      showToast('success', '사용자 추가 완료!', data.message);
      closeAddUserModal();
      document.getElementById('newStudentId').value = '';
      document.getElementById('newPassword').value = '';
      document.getElementById('newFullName').value = '';
      document.getElementById('newEmail').value = '';
      await loadAdminUsers();
    } else {
      showToast('error', '오류', data.error || '사용자를 추가할 수 없습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', '사용자 추가 요청 실패');
  }
}

async function updateUserRole(studentId, newRole) {
  try {
    const res = await fetch('/api/admin/users/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, role: newRole })
    });
    const data = await res.json();
    if (res.ok && data.status === "SUCCESS") {
      showToast('success', '권한 변경 완료', `'${studentId}' 계정의 권한이 ${newRole}로 변경되었습니다.`);
      await loadAdminUsers();
    } else {
      showToast('error', '보호된 계정', data.error || '권한을 변경할 수 없습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', '권한 변경 요청 실패');
  }
}

async function toggleUserStatus(studentId, newStatus) {
  try {
    const res = await fetch('/api/admin/users/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, status: newStatus })
    });
    const data = await res.json();
    if (res.ok && data.status === "SUCCESS") {
      showToast('info', '상태 변경 완료', `'${studentId}' 계정 상태: ${newStatus}`);
      await loadAdminUsers();
    } else {
      showToast('error', '오류', data.error || '상태를 변경할 수 없습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', '상태 변경 요청 실패');
  }
}

async function deleteUserAccount(studentId) {
  if (!confirm(`'${studentId}' 계정을 시스템에서 영구히 삭제하시겠습니까?`)) return;
  
  try {
    const res = await fetch('/api/admin/users/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId })
    });
    const data = await res.json();
    if (res.ok && data.status === "SUCCESS") {
      showToast('success', '삭제 완료', data.message);
      await loadAdminUsers();
    } else {
      showToast('error', '오류', data.error || '삭제할 수 없습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', '삭제 요청 실패');
  }
}

// ============ LOGOUT & UTILS ============
function logout() {
  state.currentUser = null;
  localStorage.removeItem('secureAuthUser');
  if (refreshInterval) clearInterval(refreshInterval);
  
  document.getElementById('userDashboardPage').classList.add('hidden');
  document.getElementById('analystDashboardPage').classList.add('hidden');
  document.getElementById('adminDashboardPage').classList.add('hidden');
  document.getElementById('blockedPage').classList.add('hidden');
  document.getElementById('loginPage').classList.remove('hidden');
  
  document.getElementById('username').value = '';
  document.getElementById('password').value = '';
  
  showToast('info', '로그아웃 완료', '안전하게 로그아웃되었습니다.');
}

function showBlockedPage(message) {
  document.getElementById('loginPage').classList.add('hidden');
  document.getElementById('userDashboardPage').classList.add('hidden');
  document.getElementById('analystDashboardPage').classList.add('hidden');
  document.getElementById('adminDashboardPage').classList.add('hidden');
  document.getElementById('blockedPage').classList.remove('hidden');
  
  document.getElementById('blockReason').textContent = message || 'ML 이상 탐지 엔진(ML Detection Engine)에 의해 차단되었습니다.';
}

function togglePassword() {
  const input = document.getElementById('password');
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}

function showToast(type, title, message) {
  const toast = document.getElementById('toast');
  const content = document.getElementById('toastContent');
  const icon = document.getElementById('toastIcon');
  
  const configs = {
    success: { border: 'border-emerald-500', iconBg: 'bg-emerald-500/20', iconColor: 'text-emerald-400', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>' },
    error: { border: 'border-red-500', iconBg: 'bg-red-500/20', iconColor: 'text-red-400', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>' },
    warn: { border: 'border-amber-500', iconBg: 'bg-amber-500/20', iconColor: 'text-amber-400', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>' },
    info: { border: 'border-blue-500', iconBg: 'bg-blue-500/20', iconColor: 'text-blue-400', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>' }
  };
  
  const cfg = configs[type] || configs.info;
  content.className = `glass rounded-xl p-4 shadow-2xl border-l-4 max-w-sm ${cfg.border}`;
  icon.className = `w-8 h-8 rounded-lg ${cfg.iconBg} flex items-center justify-center flex-shrink-0`;
  icon.innerHTML = `<svg class="w-5 h-5 ${cfg.iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">${cfg.svg}</svg>`;
  
  document.getElementById('toastTitle').textContent = title;
  document.getElementById('toastMessage').textContent = message;
  
  toast.classList.remove('hidden');
  setTimeout(() => { toast.classList.add('hidden'); }, 4000);
}

window.addEventListener('DOMContentLoaded', init);

// ============ 2FA PASSWORD RESET & RECOVERY MODAL HANDLERS ============
function validatePasswordStrength(password) {
  if (!password || password.length < 8) {
    return { valid: false, message: '비밀번호는 최소 8자 이상이어야 합니다.' };
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, message: '비밀번호에 최소 1개 이상의 대문자(A-Z)가 포함되어야 합니다.' };
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, message: '비밀번호에 최소 1개 이상의 소문자(a-z)가 포함되어야 합니다.' };
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, message: '비밀번호에 최소 1개 이상의 숫자(0-9)가 포함되어야 합니다.' };
  }
  if (!/[^a-zA-Z0-9]/.test(password)) {
    return { valid: false, message: '비밀번호에 최소 1개 이상의 특수문자(!@#$%^&*)가 포함되어야 합니다.' };
  }
  return { valid: true, message: '' };
}

function checkRealtimePasswordStrength() {
  const pwd = document.getElementById('twoFaNewPassword') ? document.getElementById('twoFaNewPassword').value : '';
  
  const hasLen = pwd.length >= 8;
  const hasUpper = /[A-Z]/.test(pwd);
  const hasLower = /[a-z]/.test(pwd);
  const hasNum = /[0-9]/.test(pwd);
  const hasSpec = /[^a-zA-Z0-9]/.test(pwd);

  updateRuleUI('ruleLen', hasLen, '최소 8자 이상');
  updateRuleUI('ruleUpper', hasUpper, '대문자 (A-Z)');
  updateRuleUI('ruleLower', hasLower, '소문자 (a-z)');
  updateRuleUI('ruleNum', hasNum, '숫자 (0-9)');
  updateRuleUI('ruleSpec', hasSpec, '특수문자 (!@#$%^&*)');
}

function updateRuleUI(elemId, isValid, labelText) {
  const elem = document.getElementById(elemId);
  if (!elem) return;
  if (isValid) {
    elem.className = 'text-emerald-400 font-semibold flex items-center gap-1';
    elem.innerText = '✓ ' + labelText;
  } else {
    elem.className = 'text-slate-500 flex items-center gap-1';
    elem.innerText = '✕ ' + labelText;
  }
}

function open2FAModal(emailOrId = '') {
  const modal = document.getElementById('twoFactorModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  document.getElementById('2faStep1').classList.remove('hidden');
  document.getElementById('2faStep2').classList.add('hidden');
  
  const mainUsername = document.getElementById('username') ? document.getElementById('username').value.trim() : '';
  
  if (emailOrId) {
    if (emailOrId.includes('@')) {
      document.getElementById('twoFaEmail').value = emailOrId;
      if (mainUsername) document.getElementById('twoFaStudentId').value = mainUsername;
    } else {
      document.getElementById('twoFaStudentId').value = emailOrId;
    }
  } else if (mainUsername) {
    document.getElementById('twoFaStudentId').value = mainUsername;
  }
}

function close2FAModal() {
  const modal = document.getElementById('twoFactorModal');
  if (modal) modal.classList.add('hidden');
}

async function request2FaOtp() {
  const student_id = document.getElementById('twoFaStudentId').value.trim();
  const email = document.getElementById('twoFaEmail').value.trim();

  if (!student_id) {
    showToast('warn', '입력 오류', '사용자 아이디 / 학번을 입력해 주세요.');
    return;
  }
  if (!email) {
    showToast('warn', '입력 오류', '등록된 이메일 주소를 입력해 주세요.');
    return;
  }

  const btn = document.getElementById('btnRequestOtp');
  btn.disabled = true;
  btn.innerText = '검증 및 전송 중...';

  try {
    const res = await fetch('/api/user/2fa/request-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: student_id, email: email })
    });
    const data = await res.json();
    if (res.ok && data.status === 'SUCCESS') {
      showToast('info', 'OTP 코드 발송 완료!', data.message);
      document.getElementById('2faStep1').classList.add('hidden');
      document.getElementById('2faStep2').classList.remove('hidden');
      if (data.mock_otp) {
        document.getElementById('mockOtpBox').classList.remove('hidden');
        document.getElementById('mockOtpVal').innerText = data.mock_otp;
        document.getElementById('twoFaOtpCode').value = data.mock_otp;
      }
    } else {
      showToast('error', '인증 정보 불일치', data.message || '학번과 이메일 정보가 일치하지 않습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '📧 6자리 OTP 인증 코드 이메일로 받기';
  }
}

async function verify2FaAndResetPassword() {
  const student_id = document.getElementById('twoFaStudentId').value.trim();
  const email = document.getElementById('twoFaEmail').value.trim();
  const otp_code = document.getElementById('twoFaOtpCode').value.trim();
  const new_password = document.getElementById('twoFaNewPassword').value.trim();

  if (!otp_code || otp_code.length !== 6) {
    showToast('warn', '입력 오류', '6자리 OTP 코드를 입력해 주세요.');
    return;
  }
  
  const pwdCheck = validatePasswordStrength(new_password);
  if (!pwdCheck.valid) {
    showToast('warn', '비밀번호 규칙 오류', pwdCheck.message);
    return;
  }

  const btn = document.getElementById('btnVerifyReset');
  btn.disabled = true;
  btn.innerText = '변경 및 검증 중...';

  try {
    const res = await fetch('/api/user/2fa/verify-unsuspend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: student_id,
        email: email,
        otp_code: otp_code,
        new_password: new_password
      })
    });
    const data = await res.json();
    if (res.ok && data.status === 'SUCCESS') {
      showToast('success', '인증 및 비밀번호 변경 완료!', data.message);
      close2FAModal();
      // Auto-fill login form with new credentials and trigger login!
      if (data.student_id) {
        document.getElementById('username').value = data.student_id;
      }
      document.getElementById('password').value = new_password;
      
      // Submit login form automatically
      setTimeout(() => {
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
          loginForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
      }, 500);
    } else {
      showToast('error', '인증 실패', data.message || '잘못된 코드이거나 비밀번호 규칙을 충족하지 않습니다.');
    }
  } catch (err) {
    showToast('error', '연결 오류', err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '✅ 인증 완료, 비밀번호 변경 및 로그인';
  }
}