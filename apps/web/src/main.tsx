import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

type Locale = 'zh-CN' | 'en-US'
type Page = 'codexSessions' | 'conversations' | 'infra' | 'secrets'

type User = { id: string; username: string; display_name: string; role: string; locale: Locale }
type InfraCheck = { id: string; label: string; status: 'pass' | 'warn' | 'fail'; summary: string; detail: string }
type RunEvent = { id: string; at: string; level: 'info' | 'warn' | 'error' | 'pass'; message: string }
type AuditEvent = { id: string; at: string; actor_name: string; event_code: string; resource: string }
type WorkflowStep = { id: string; label: string; status: 'complete' | 'active' | 'pending' | 'failed'; at?: string }
type CodexRun = {
  id: string
  repo: string
  branch: string
  sandbox_id: string
  template: string
  owner_name: string
  status: string
  elapsed_seconds: number
  step: string
  progress: number
  resources: Record<string, number>
  workflow: WorkflowStep[]
  diff_summary: {
    file: string
    added: number
    removed: number
    files_changed: number
    hunks: Array<{ line: number; kind: 'add' | 'remove'; text: string }>
  }
}
type CodexAuthStatus = {
  mode: 'chatgpt' | 'api_key' | 'none'
  state: 'authenticated' | 'pending' | 'missing' | 'failed'
  fallback_api_key: boolean
  login_url?: string
  user_code?: string
  token_fingerprint?: string
}
type DashboardSnapshot = {
  user: User
  preflight: { checked_at: string; overall_status: 'pass' | 'warn' | 'fail'; overall_score: number; checks: InfraCheck[] }
  runs: CodexRun[]
  selected_run: CodexRun
  events: RunEvent[]
  audit: AuditEvent[]
  codex_auth: CodexAuthStatus
  quota: Record<string, number>
}

const dict: Record<Locale, Record<string, string>> = {
  'zh-CN': {
    app: 'Sandbox Control',
    overview: '总览',
    sandboxes: 'Sandboxes',
    codexSessions: 'Codex 会话',
    conversations: '对话',
    templates: '模板',
    repos: '代码仓库',
    secrets: '密钥',
    infra: '基础设施',
    audit: '审计',
    settings: '设置',
    loginTitle: '登录 Sandbox Control',
    username: '用户名',
    password: '密码',
    login: '登录',
    defaultHint: '开发默认账号：admin / sandbox-control-admin',
    search: '搜索 sandbox、会话、repo、模板',
    createSandbox: '创建 Sandbox',
    createRun: '创建 Codex Run',
    infraPreflight: 'INFRA PREFLIGHT（单机实验）',
    overallHealth: '整体健康',
    preflightTitle: '为什么 KVM / Firecracker 会限制单机部署？',
    preflightText:
      'KVM 是 Linux 内核的硬件虚拟化接口，Firecracker 是基于 KVM 启动 microVM 的轻量运行时。E2B 沙箱依赖 VM 级隔离；如果服务器没有 VT-x/AMD-V、/dev/kvm、TUN/TAP 或合适的内核权限，只安装 Docker 也无法运行 Firecracker 沙箱。',
    runQueue: '运行队列',
    liveLog: '实时日志',
    diffSummary: 'Diff 摘要',
    workflow: '工作流时间线',
    auditTrail: '审计轨迹',
    activeSandbox: '活动 Sandbox',
    codexAccount: 'Codex 账号',
    startChatGptLogin: '启动 ChatGPT 登录',
    saveApiKey: '保存 API Key 备用',
    logoutCodex: '退出 Codex',
    approve: '批准',
    requestChanges: '要求修改',
    reject: '拒绝',
    pause: '暂停',
    resume: '恢复',
    kill: '终止',
    openIde: '打开 IDE',
    openSandbox: '打开 Sandbox',
    quota: '配额',
    costEstimate: '成本估算',
    localUsers: '本地用户',
    patVault: 'PAT Vault',
    composerPlaceholder: '告诉 Codex 要做什么，或粘贴 issue / 错误日志',
    send: '发送',
    chatTitle: 'Codex 对话页',
    toolApprovals: '工具调用与审批',
    terminal: '终端',
    files: '文件 / Diff',
  },
  'en-US': {
    app: 'Sandbox Control',
    overview: 'Overview',
    sandboxes: 'Sandboxes',
    codexSessions: 'Codex Sessions',
    conversations: 'Conversations',
    templates: 'Templates',
    repos: 'Repos',
    secrets: 'Secrets',
    infra: 'Infra',
    audit: 'Audit',
    settings: 'Settings',
    loginTitle: 'Sign in to Sandbox Control',
    username: 'Username',
    password: 'Password',
    login: 'Sign in',
    defaultHint: 'Development default: admin / sandbox-control-admin',
    search: 'Search sandboxes, sessions, repos, templates',
    createSandbox: 'Create Sandbox',
    createRun: 'Create Codex Run',
    infraPreflight: 'INFRA PREFLIGHT (single-node experimental)',
    overallHealth: 'Overall Health',
    preflightTitle: 'Why can KVM / Firecracker block single-node deployments?',
    preflightText:
      'KVM is the Linux kernel hardware virtualization interface. Firecracker is a lightweight runtime that starts KVM-backed microVMs. E2B isolation depends on VM-level boundaries; without VT-x/AMD-V, /dev/kvm, TUN/TAP, or kernel permissions, Docker alone cannot run Firecracker sandboxes.',
    runQueue: 'Run Queue',
    liveLog: 'Live Log Stream',
    diffSummary: 'Diff Summary',
    workflow: 'Workflow Timeline',
    auditTrail: 'Audit Trail',
    activeSandbox: 'Active Sandbox',
    codexAccount: 'Codex Account',
    startChatGptLogin: 'Start ChatGPT Login',
    saveApiKey: 'Save API Key Fallback',
    logoutCodex: 'Log out Codex',
    approve: 'Approve',
    requestChanges: 'Request Changes',
    reject: 'Reject',
    pause: 'Pause',
    resume: 'Resume',
    kill: 'Kill',
    openIde: 'Open in IDE',
    openSandbox: 'Open Sandbox',
    quota: 'Quota',
    costEstimate: 'Cost Estimate',
    localUsers: 'Local Users',
    patVault: 'PAT Vault',
    composerPlaceholder: 'Tell Codex what to do, or paste an issue / error log',
    send: 'Send',
    chatTitle: 'Codex Conversation Page',
    toolApprovals: 'Tool Calls & Approvals',
    terminal: 'Terminal',
    files: 'Files / Diff',
  },
}

const glyph: Record<string, string> = {
  overview: '⌘',
  sandboxes: '▣',
  codexSessions: '◉',
  conversations: '☷',
  templates: '▤',
  repos: '⌁',
  secrets: '◇',
  infra: '⌬',
  audit: '≣',
  settings: '⚙',
}

function tr(locale: Locale, key: string) {
  return dict[locale][key] ?? key
}

async function api<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}

function App() {
  const [locale, setLocale] = useState<Locale>((localStorage.getItem('sandbox-control-locale') as Locale) || 'zh-CN')
  const [token, setToken] = useState(localStorage.getItem('sandbox-control-token'))
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null)
  const [page, setPage] = useState<Page>('codexSessions')
  const [error, setError] = useState('')
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('sandbox-control-admin')

  useEffect(() => localStorage.setItem('sandbox-control-locale', locale), [locale])
  useEffect(() => {
    if (!token) return
    api<DashboardSnapshot>('/api/dashboard', token)
      .then(setSnapshot)
      .catch((err) => {
        setError(err.message)
        setToken(null)
        localStorage.removeItem('sandbox-control-token')
      })
  }, [token])

  async function login(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    const response = await api<{ token: string }>('/api/auth/login', undefined, {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    localStorage.setItem('sandbox-control-token', response.token)
    setToken(response.token)
  }

  if (!token) {
    return (
      <main className="login-shell">
        <form className="login-panel" onSubmit={login}>
          <Brand />
          <h1>{tr(locale, 'loginTitle')}</h1>
          <label>{tr(locale, 'username')}<input value={username} onChange={(event) => setUsername(event.target.value)} /></label>
          <label>{tr(locale, 'password')}<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button className="primary-action" type="submit">{tr(locale, 'login')}</button>
          <p className="muted">{tr(locale, 'defaultHint')}</p>
          {error ? <p className="error-text">{error}</p> : null}
          <LocaleSwitch locale={locale} setLocale={setLocale} />
        </form>
      </main>
    )
  }
  if (!snapshot) return <div className="boot">Sandbox Control</div>

  return (
    <div className="app-frame">
      <Sidebar locale={locale} snapshot={snapshot} page={page} setPage={setPage} />
      <main className="workspace">
        <CommandBar locale={locale} setLocale={setLocale} logout={() => {
          setToken(null)
          localStorage.removeItem('sandbox-control-token')
        }} />
        {page === 'conversations' ? (
          <ConversationPage locale={locale} snapshot={snapshot} />
        ) : (
          <ControlPage locale={locale} token={token} snapshot={snapshot} setSnapshot={setSnapshot} />
        )}
      </main>
    </div>
  )
}

function ControlPage({ locale, token, snapshot, setSnapshot }: { locale: Locale; token: string; snapshot: DashboardSnapshot; setSnapshot: (next: DashboardSnapshot) => void }) {
  const [selectedRun, setSelectedRun] = useState(snapshot.selected_run)
  async function refresh() {
    setSnapshot(await api<DashboardSnapshot>('/api/dashboard', token))
  }
  async function action(actionName: string) {
    const response = await api<{ run: CodexRun }>(`/api/codex-runs/${selectedRun.id}/${actionName}`, token, { method: 'POST' })
    setSelectedRun(response.run)
    await refresh()
  }
  async function startCodexLogin() {
    await api('/api/codex-auth/login/start', token, { method: 'POST' })
    await refresh()
  }
  return (
    <>
      <InfraPreflight locale={locale} snapshot={snapshot} />
      <section className="content-grid">
        <RunQueue locale={locale} runs={snapshot.runs} selectedRun={selectedRun} setSelectedRun={setSelectedRun} />
        <RunDetail locale={locale} run={selectedRun} onAction={action} />
        <LogAndDiff locale={locale} run={selectedRun} events={snapshot.events} />
        <AuditTrail locale={locale} audit={snapshot.audit} />
        <CodexAccountPanel locale={locale} status={snapshot.codex_auth} onStartLogin={startCodexLogin} />
        <ResourcePanel locale={locale} run={selectedRun} />
      </section>
    </>
  )
}

function ConversationPage({ locale, snapshot }: { locale: Locale; snapshot: DashboardSnapshot }) {
  const run = snapshot.selected_run
  const [draft, setDraft] = useState('')
  const messages = [
    { role: 'user', body: '修复 runner 超时重试，保持接口兼容。' },
    { role: 'agent', body: '我会先检查 src/services/ai/runner.py，再生成最小补丁并运行 pytest -k runner。' },
    { role: 'tool', body: 'apply_patch requested: src/services/ai/runner.py (+24 -8)' },
    { role: 'agent', body: '测试已通过，等待你批准继续提交变更。' },
  ]
  return (
    <section className="chat-layout">
      <aside className="panel chat-sessions">
        <div className="panel-title"><h2>{tr(locale, 'chatTitle')}</h2><span>{snapshot.runs.length}</span></div>
        {snapshot.runs.map((item) => (
          <button key={item.id} className={item.id === run.id ? 'chat-item selected' : 'chat-item'}>
            <strong>{item.repo}</strong>
            <span>{item.id} · {item.status}</span>
          </button>
        ))}
      </aside>
      <section className="panel chat-thread">
        <div className="thread-header">
          <div>
            <h1>{run.repo}</h1>
            <span>{run.branch} / {run.sandbox_id}</span>
          </div>
          <button className="primary-action">{tr(locale, 'approve')}</button>
        </div>
        <div className="messages">
          {messages.map((message, index) => (
            <article key={`${message.role}-${index}`} className={`message ${message.role}`}>
              <span>{message.role}</span>
              <p>{message.body}</p>
            </article>
          ))}
          <article className="tool-card">
            <div className="panel-title"><h2>{tr(locale, 'toolApprovals')}</h2><span>apply_patch</span></div>
            <p>src/services/ai/runner.py · +24 -8 · pytest passed</p>
            <div className="actions"><button className="approve">{tr(locale, 'approve')}</button><button className="reject">{tr(locale, 'reject')}</button></div>
          </article>
        </div>
        <form className="composer" onSubmit={(event) => event.preventDefault()}>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={tr(locale, 'composerPlaceholder')} />
          <button className="primary-action">{tr(locale, 'send')}</button>
        </form>
      </section>
      <aside className="chat-side">
        <div className="panel"><div className="panel-title"><h2>{tr(locale, 'terminal')}</h2><span>Tailing</span></div><pre>{snapshot.events.map((event) => `${event.at} ${event.message}`).join('\n')}</pre></div>
        <div className="panel"><div className="panel-title"><h2>{tr(locale, 'files')}</h2><span>+{run.diff_summary.added} -{run.diff_summary.removed}</span></div><DiffLines run={run} /></div>
      </aside>
    </section>
  )
}

function Brand() {
  return <div className="brand"><div className="brand-mark">⬡</div><div><strong>SANDBOX</strong><span>CONTROL</span></div></div>
}

function LocaleSwitch({ locale, setLocale }: { locale: Locale; setLocale: (locale: Locale) => void }) {
  return <div className="locale-switch"><button className={locale === 'zh-CN' ? 'active' : ''} onClick={() => setLocale('zh-CN')}>中文</button><button className={locale === 'en-US' ? 'active' : ''} onClick={() => setLocale('en-US')}>EN</button></div>
}

function Sidebar({ locale, snapshot, page, setPage }: { locale: Locale; snapshot: DashboardSnapshot; page: Page; setPage: (page: Page) => void }) {
  const items = ['overview', 'sandboxes', 'codexSessions', 'conversations', 'templates', 'repos', 'secrets', 'infra', 'audit', 'settings']
  return (
    <aside className="sidebar">
      <Brand />
      <nav>{items.map((item) => <button key={item} className={page === item ? 'selected' : ''} onClick={() => ['codexSessions', 'conversations', 'infra', 'secrets'].includes(item) && setPage(item as Page)}><span>{glyph[item]}</span>{tr(locale, item)}</button>)}</nav>
      <div className="side-stack">
        <SideStat title={tr(locale, 'localUsers')} value="32" detail="+27" />
        <SideStat title={tr(locale, 'patVault')} value="23" detail="18 / 3 / 2" />
        <div className="side-card"><div className="side-title">{tr(locale, 'quota')}</div><Meter label="Sandboxes" value={snapshot.quota.sandboxes} max={snapshot.quota.sandbox_limit} /><Meter label="vCPU" value={snapshot.quota.cpu} max={snapshot.quota.cpu_limit} /><Meter label="RAM" value={snapshot.quota.ram} max={snapshot.quota.ram_limit} /><div className="cost"><span>{tr(locale, 'costEstimate')}</span><strong>${snapshot.quota.cost}</strong></div></div>
      </div>
    </aside>
  )
}

function CommandBar({ locale, setLocale, logout }: { locale: Locale; setLocale: (locale: Locale) => void; logout: () => void }) {
  return <header className="command-bar"><div className="selector">Acme Corp</div><div className="selector">Platform</div><div className="env-pill">single-node</div><div className="search">⌕ {tr(locale, 'search')} <kbd>⌘K</kbd></div><button className="ghost-action">＋ {tr(locale, 'createSandbox')}</button><button className="primary-action">＋ {tr(locale, 'createRun')}</button><LocaleSwitch locale={locale} setLocale={setLocale} /><button className="avatar" onClick={logout}>SK</button></header>
}

function InfraPreflight({ locale, snapshot }: { locale: Locale; snapshot: DashboardSnapshot }) {
  return (
    <section className="preflight">
      <div className="section-heading"><h2>{tr(locale, 'infraPreflight')}</h2><div className={`health ${snapshot.preflight.overall_status}`}>{snapshot.preflight.overall_score}%</div></div>
      <div className="preflight-grid">{snapshot.preflight.checks.slice(0, 9).map((check) => <div key={check.id} className={`check ${check.status}`}><div><strong>{check.label}</strong><span>{check.status.toUpperCase()}</span></div><p>{check.summary}</p></div>)}</div>
      <div className="explainer"><strong>{tr(locale, 'preflightTitle')}</strong><p>{tr(locale, 'preflightText')}</p></div>
    </section>
  )
}

function RunQueue({ locale, runs, selectedRun, setSelectedRun }: { locale: Locale; runs: CodexRun[]; selectedRun: CodexRun; setSelectedRun: (run: CodexRun) => void }) {
  return <section className="panel run-queue"><div className="panel-title"><h2>{tr(locale, 'runQueue')}</h2><span>{runs.length}</span></div><div className="filter">⌕ Filter runs</div><div className="run-list">{runs.map((run) => <button key={run.id} className={`run-row ${selectedRun.id === run.id ? 'selected' : ''}`} onClick={() => setSelectedRun(run)}><span className={`status-dot ${run.status}`} /><span><strong>{run.id}</strong><small>{run.repo}<br />{run.branch}</small></span><em>{run.step}</em></button>)}</div></section>
}

function RunDetail({ locale, run, onAction }: { locale: Locale; run: CodexRun; onAction: (action: string) => void }) {
  return (
    <section className="panel run-detail">
      <div className="run-header"><div><h1>{run.id}</h1><span className={`state ${run.status}`}>{run.status}</span></div><div className="actions"><button className="approve" onClick={() => onAction('approve')}>{tr(locale, 'approve')}</button><button className="warn">{tr(locale, 'requestChanges')}</button><button className="reject" onClick={() => onAction('reject')}>{tr(locale, 'reject')}</button></div></div>
      <div className="meta-grid"><Meta label="Repo" value={run.repo} /><Meta label="Branch" value={run.branch} /><Meta label="Sandbox" value={run.sandbox_id} /><Meta label="Template" value={run.template} /><Meta label="Owner" value={run.owner_name} /><Meta label="Runtime" value={formatElapsed(run.elapsed_seconds)} /></div>
      <div className="safety-row"><Safety label="Network Policy" value="default-deny-egress" /><Safety label="Token Scope" value="repo:read, issues:write" /><Safety label="Egress Limit" value="500 Mbps" /><Safety label="Approval Required" value="On Success" /></div>
      <div className="run-controls"><button onClick={() => onAction('pause')}>Ⅱ {tr(locale, 'pause')}</button><button>▶ {tr(locale, 'resume')}</button><button className="kill" onClick={() => onAction('kill')}>■ {tr(locale, 'kill')}</button><button className="right">↗ {tr(locale, 'openIde')}</button><button>⬡ {tr(locale, 'openSandbox')}</button></div>
      <Workflow locale={locale} run={run} />
    </section>
  )
}

function Workflow({ locale, run }: { locale: Locale; run: CodexRun }) {
  return <div className="workflow"><h2>{tr(locale, 'workflow')}</h2><div className="step-track">{run.workflow.map((step) => <div key={step.id} className={`step ${step.status}`}><span /><strong>{step.label}</strong><small>{step.at ?? '--'}</small></div>)}</div><div className="step-cards">{['Read file', 'Generate patch', 'Apply patch', 'Run tests', 'Commit changes'].map((label, index) => <div key={label} className={index === 2 ? 'active' : ''}><strong>{index < 3 ? '✓' : '⟳'} {label}</strong><small>{index === 2 ? '1.5s' : index < 2 ? 'OK' : '--'}</small></div>)}</div></div>
}

function LogAndDiff({ locale, run, events }: { locale: Locale; run: CodexRun; events: RunEvent[] }) {
  return <section className="right-stack"><div className="panel log-panel"><div className="panel-title"><h2>{tr(locale, 'liveLog')}</h2><span>Tailing</span></div><pre>{events.map((event) => `${event.at} [${event.level.toUpperCase()}] ${event.message}`).join('\n')}</pre></div><div className="panel diff-panel"><div className="panel-title"><h2>{tr(locale, 'diffSummary')} <small>{run.diff_summary.file}</small></h2><span>+{run.diff_summary.added} -{run.diff_summary.removed}</span></div><DiffLines run={run} /></div></section>
}

function DiffLines({ run }: { run: CodexRun }) {
  return <div className="diff-lines">{run.diff_summary.hunks.map((hunk) => <div key={`${hunk.line}-${hunk.text}`} className={hunk.kind}><span>{hunk.line}</span><code>{hunk.text}</code></div>)}</div>
}

function AuditTrail({ locale, audit }: { locale: Locale; audit: AuditEvent[] }) {
  return <section className="panel audit-panel"><div className="panel-title"><h2>{tr(locale, 'auditTrail')}</h2><span>All Events</span></div><div className="audit-table">{audit.slice(0, 6).map((event) => <div key={event.id}><span>{event.at}</span><strong>{event.actor_name}</strong><em>{event.event_code}</em><code>{event.resource}</code></div>)}</div></section>
}

function CodexAccountPanel({ locale, status, onStartLogin }: { locale: Locale; status: CodexAuthStatus; onStartLogin: () => void }) {
  return <section className="panel codex-panel"><div className="panel-title"><h2>{tr(locale, 'codexAccount')}</h2><span>{status.mode}</span></div><div className={`account-state ${status.state}`}>{status.state}</div>{status.login_url ? <code className="login-url">{status.login_url}</code> : null}{status.user_code ? <div className="user-code">{status.user_code}</div> : null}<button className="primary-action" onClick={onStartLogin}>{tr(locale, 'startChatGptLogin')}</button><button className="ghost-action">{tr(locale, 'saveApiKey')}</button><button className="danger-link">{tr(locale, 'logoutCodex')}</button></section>
}

function ResourcePanel({ locale, run }: { locale: Locale; run: CodexRun }) {
  return <section className="panel resource-panel"><div className="panel-title"><h2>{tr(locale, 'activeSandbox')}: {run.sandbox_id}</h2><span>{run.status}</span></div><div className="radial" style={{ '--value': `${run.resources.cpu}%` } as React.CSSProperties}><strong>{run.resources.cpu}%</strong><span>vCPU</span></div><Meter label="Memory" value={run.resources.memory} max={100} /><Meter label="Disk" value={run.resources.disk} max={100} /><Meter label="Network" value={run.resources.network} max={100} /></section>
}

function SideStat({ title, value, detail }: { title: string; value: string; detail: string }) {
  return <div className="side-card"><div className="side-title">{title}</div><div className="side-value"><strong>{value}</strong><span>{detail}</span></div><div className="mini-bar"><span style={{ width: '68%' }} /></div></div>
}

function Meter({ label, value, max }: { label: string; value: number; max: number }) {
  return <div className="meter"><div><span>{label}</span><em>{value} / {max}</em></div><div className="meter-track"><span style={{ width: `${Math.min(100, Math.round((value / max) * 100))}%` }} /></div></div>
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>
}

function Safety({ label, value }: { label: string; value: string }) {
  return <div><span>◈</span><small>{label}</small><strong>{value}</strong></div>
}

function formatElapsed(seconds: number) {
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

createRoot(document.getElementById('app')!).render(<App />)
