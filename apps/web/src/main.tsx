import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

type Locale = 'zh-CN' | 'en-US'
type Page = 'codexSessions' | 'conversations' | 'infra' | 'secrets'
type User = { id: string; username: string; display_name: string; role: string; locale: Locale }
type InfraCheck = { id: string; label: string; status: 'pass' | 'warn' | 'fail'; summary: string; detail: string }
type RunEvent = { id: string; at: string; level: 'info' | 'warn' | 'error' | 'pass'; event_type: string; message: string }
type AuditEvent = { id: string; at: string; actor_name: string; event_code: string; resource: string }
type WorkflowStep = { id: string; label: string; status: 'complete' | 'active' | 'pending' | 'failed'; at?: string }
type CodexRun = {
  id: string
  repo: string
  branch: string
  prompt: string
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
  selected_run: CodexRun | null
  events: RunEvent[]
  audit: AuditEvent[]
  codex_auth: CodexAuthStatus
  quota: Record<string, number>
}

const dict: Record<Locale, Record<string, string>> = {
  'zh-CN': {
    app: 'Sandbox Control',
    codexSessions: 'Codex 运行',
    conversations: '对话',
    infra: '基础设施',
    secrets: '密钥',
    loginTitle: '登录 Sandbox Control',
    username: '用户名',
    password: '密码',
    login: '登录',
    defaultHint: '默认开发账号：admin / sandbox-control-admin',
    createRun: '创建真实 Codex Run',
    repo: '仓库',
    branch: '分支',
    prompt: '任务',
    promptPlaceholder: '告诉 Codex 要真实执行什么，例如：检查 README 并提出改动',
    startRun: '启动',
    emptyRuns: '还没有真实 Codex run。创建后这里会显示真实 clone、codex exec、退出码和 diff。',
    infraPreflight: 'INFRA PREFLIGHT（真实主机检测）',
    runQueue: '运行队列',
    liveLog: '真实事件流',
    diffSummary: '真实 Diff',
    workflow: '工作流',
    auditTrail: '审计',
    codexAccount: 'Codex 账号',
    startChatGptLogin: '启动 ChatGPT 登录',
    saveApiKey: '保存 API Key 备用',
    logout: '退出',
    approve: '批准',
    reject: '拒绝',
    pause: '暂停',
    kill: '终止',
    chatTitle: 'Codex 对话页',
    noConversation: '没有真实会话。先创建一个 Codex run。',
    composerPlaceholder: '后续会接入持续对话；当前只展示真实 run 事件。',
    send: '发送',
  },
  'en-US': {
    app: 'Sandbox Control',
    codexSessions: 'Codex Runs',
    conversations: 'Conversation',
    infra: 'Infra',
    secrets: 'Secrets',
    loginTitle: 'Sign in to Sandbox Control',
    username: 'Username',
    password: 'Password',
    login: 'Sign in',
    defaultHint: 'Development default: admin / sandbox-control-admin',
    createRun: 'Create Real Codex Run',
    repo: 'Repository',
    branch: 'Branch',
    prompt: 'Prompt',
    promptPlaceholder: 'Tell Codex what to actually execute, e.g. inspect README and propose edits',
    startRun: 'Start',
    emptyRuns: 'No real Codex runs yet. After creation this shows real clone, codex exec, exit code, and diff.',
    infraPreflight: 'INFRA PREFLIGHT (real host checks)',
    runQueue: 'Run Queue',
    liveLog: 'Real Event Stream',
    diffSummary: 'Real Diff',
    workflow: 'Workflow',
    auditTrail: 'Audit',
    codexAccount: 'Codex Account',
    startChatGptLogin: 'Start ChatGPT Login',
    saveApiKey: 'Save API Key Fallback',
    logout: 'Log out',
    approve: 'Approve',
    reject: 'Reject',
    pause: 'Pause',
    kill: 'Kill',
    chatTitle: 'Codex Conversation Page',
    noConversation: 'No real conversation yet. Create a Codex run first.',
    composerPlaceholder: 'Continuous chat will be wired next; currently this shows real run events.',
    send: 'Send',
  },
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
    refresh(token).catch((err) => {
      setError(err.message)
      setToken(null)
      localStorage.removeItem('sandbox-control-token')
    })
  }, [token])

  async function refresh(authToken = token) {
    if (!authToken) return
    setSnapshot(await api<DashboardSnapshot>('/api/dashboard', authToken))
  }

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
          setSnapshot(null)
          localStorage.removeItem('sandbox-control-token')
        }} />
        {page === 'conversations' ? (
          <ConversationPage locale={locale} snapshot={snapshot} />
        ) : (
          <ControlPage locale={locale} token={token} snapshot={snapshot} refresh={() => refresh()} />
        )}
      </main>
    </div>
  )
}

function ControlPage({ locale, token, snapshot, refresh }: { locale: Locale; token: string; snapshot: DashboardSnapshot; refresh: () => Promise<void> }) {
  const [selectedId, setSelectedId] = useState(snapshot.selected_run?.id ?? '')
  const selectedRun = useMemo(
    () => snapshot.runs.find((run) => run.id === selectedId) ?? snapshot.selected_run ?? snapshot.runs[0] ?? null,
    [snapshot, selectedId],
  )

  async function action(actionName: string) {
    if (!selectedRun) return
    await api(`/api/codex-runs/${selectedRun.id}/${actionName}`, token, { method: 'POST' })
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
        <section className="panel run-queue">
          <div className="panel-title"><h2>{tr(locale, 'runQueue')}</h2><span>{snapshot.runs.length}</span></div>
          <CreateRunForm locale={locale} token={token} refresh={refresh} />
          {snapshot.runs.length === 0 ? <div className="empty-state">{tr(locale, 'emptyRuns')}</div> : null}
          <div className="run-list">{snapshot.runs.map((run) => (
            <button key={run.id} className={`run-row ${selectedRun?.id === run.id ? 'selected' : ''}`} onClick={() => setSelectedId(run.id)}>
              <span className={`status-dot ${run.status}`} />
              <span><strong>{run.id}</strong><small>{run.repo}<br />{run.branch}</small></span>
              <em>{run.step}</em>
            </button>
          ))}</div>
        </section>
        {selectedRun ? <RunDetail locale={locale} run={selectedRun} onAction={action} /> : <EmptyPanel text={tr(locale, 'emptyRuns')} />}
        {selectedRun ? <LogAndDiff locale={locale} run={selectedRun} events={snapshot.events} /> : <EmptyPanel text={tr(locale, 'liveLog')} />}
        <AuditTrail locale={locale} audit={snapshot.audit} />
        <CodexAccountPanel locale={locale} status={snapshot.codex_auth} onStartLogin={startCodexLogin} />
        {selectedRun ? <ResourcePanel run={selectedRun} /> : <EmptyPanel text="No active sandbox" />}
      </section>
    </>
  )
}

function CreateRunForm({ locale, token, refresh }: { locale: Locale; token: string; refresh: () => Promise<void> }) {
  const [repo, setRepo] = useState('')
  const [branch, setBranch] = useState('main')
  const [prompt, setPrompt] = useState('')
  const [error, setError] = useState('')

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await api('/api/codex-runs', token, {
        method: 'POST',
        body: JSON.stringify({ repo, branch, prompt, template: 'python-3.11' }),
      })
      setPrompt('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <form className="create-run-form" onSubmit={submit}>
      <label>{tr(locale, 'repo')}<input value={repo} onChange={(event) => setRepo(event.target.value)} placeholder="owner/repo or https://..." /></label>
      <label>{tr(locale, 'branch')}<input value={branch} onChange={(event) => setBranch(event.target.value)} /></label>
      <label>{tr(locale, 'prompt')}<textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder={tr(locale, 'promptPlaceholder')} /></label>
      <button className="primary-action" type="submit">{tr(locale, 'startRun')}</button>
      {error ? <p className="error-text">{error}</p> : null}
    </form>
  )
}

function ConversationPage({ locale, snapshot }: { locale: Locale; snapshot: DashboardSnapshot }) {
  const run = snapshot.selected_run ?? snapshot.runs[0] ?? null
  const [draft, setDraft] = useState('')
  if (!run) return <section className="panel empty-conversation"><h1>{tr(locale, 'chatTitle')}</h1><p>{tr(locale, 'noConversation')}</p></section>
  return (
    <section className="chat-layout">
      <aside className="panel chat-sessions">
        <div className="panel-title"><h2>{tr(locale, 'chatTitle')}</h2><span>{snapshot.runs.length}</span></div>
        {snapshot.runs.map((item) => <button key={item.id} className={item.id === run.id ? 'chat-item selected' : 'chat-item'}><strong>{item.repo}</strong><span>{item.id} / {item.status}</span></button>)}
      </aside>
      <section className="panel chat-thread">
        <div className="thread-header"><div><h1>{run.repo}</h1><span>{run.branch} / {run.sandbox_id}</span></div></div>
        <div className="messages">
          <article className="message user"><span>user</span><p>{run.prompt}</p></article>
          {snapshot.events.map((event) => (
            <article key={event.id} className={`message ${event.level === 'error' ? 'tool' : 'agent'}`}>
              <span>{event.event_type}</span>
              <p>{event.message}</p>
            </article>
          ))}
        </div>
        <form className="composer" onSubmit={(event) => event.preventDefault()}>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={tr(locale, 'composerPlaceholder')} />
          <button className="primary-action">{tr(locale, 'send')}</button>
        </form>
      </section>
      <aside className="chat-side">
        <div className="panel"><div className="panel-title"><h2>{tr(locale, 'liveLog')}</h2><span>{run.status}</span></div><pre>{snapshot.events.map((event) => `${event.at} [${event.level}] ${event.message}`).join('\n')}</pre></div>
        <div className="panel"><div className="panel-title"><h2>{tr(locale, 'diffSummary')}</h2><span>+{run.diff_summary.added} -{run.diff_summary.removed}</span></div><DiffLines run={run} /></div>
      </aside>
    </section>
  )
}

function Brand() {
  return <div className="brand"><div className="brand-mark">S</div><div><strong>SANDBOX</strong><span>CONTROL</span></div></div>
}

function LocaleSwitch({ locale, setLocale }: { locale: Locale; setLocale: (locale: Locale) => void }) {
  return <div className="locale-switch"><button className={locale === 'zh-CN' ? 'active' : ''} onClick={() => setLocale('zh-CN')}>中文</button><button className={locale === 'en-US' ? 'active' : ''} onClick={() => setLocale('en-US')}>EN</button></div>
}

function Sidebar({ locale, snapshot, page, setPage }: { locale: Locale; snapshot: DashboardSnapshot; page: Page; setPage: (page: Page) => void }) {
  const items: Page[] = ['codexSessions', 'conversations', 'infra', 'secrets']
  return (
    <aside className="sidebar">
      <Brand />
      <nav>{items.map((item) => <button key={item} className={page === item ? 'selected' : ''} onClick={() => setPage(item)}><span>▪</span>{tr(locale, item)}</button>)}</nav>
      <div className="side-stack">
        <SideStat title="Runs" value={String(snapshot.runs.length)} detail="real" />
        <SideStat title="Audit" value={String(snapshot.audit.length)} detail="events" />
        <div className="side-card"><div className="side-title">Infra</div><Meter label="Preflight" value={snapshot.preflight.overall_score} max={100} /></div>
      </div>
    </aside>
  )
}

function CommandBar({ locale, setLocale, logout }: { locale: Locale; setLocale: (locale: Locale) => void; logout: () => void }) {
  return <header className="command-bar"><div className="selector">Internal</div><div className="selector">Platform</div><div className="env-pill">single-node</div><div className="search">Real backend / no demo seed data</div><LocaleSwitch locale={locale} setLocale={setLocale} /><button className="avatar" onClick={logout}>{tr(locale, 'logout')}</button></header>
}

function InfraPreflight({ locale, snapshot }: { locale: Locale; snapshot: DashboardSnapshot }) {
  return (
    <section className="preflight">
      <div className="section-heading"><h2>{tr(locale, 'infraPreflight')}</h2><div className={`health ${snapshot.preflight.overall_status}`}>{snapshot.preflight.overall_score}%</div></div>
      <div className="preflight-grid">{snapshot.preflight.checks.map((check) => <div key={check.id} className={`check ${check.status}`}><div><strong>{check.label}</strong><span>{check.status.toUpperCase()}</span></div><p>{check.summary}</p></div>)}</div>
    </section>
  )
}

function RunDetail({ locale, run, onAction }: { locale: Locale; run: CodexRun; onAction: (action: string) => void }) {
  return (
    <section className="panel run-detail">
      <div className="run-header"><div><h1>{run.id}</h1><span className={`state ${run.status}`}>{run.status}</span></div><div className="actions"><button className="approve" onClick={() => onAction('approve')}>{tr(locale, 'approve')}</button><button className="reject" onClick={() => onAction('reject')}>{tr(locale, 'reject')}</button><button className="kill" onClick={() => onAction('kill')}>{tr(locale, 'kill')}</button></div></div>
      <div className="meta-grid"><Meta label="Repo" value={run.repo} /><Meta label="Branch" value={run.branch} /><Meta label="Sandbox" value={run.sandbox_id} /><Meta label="Template" value={run.template} /><Meta label="Owner" value={run.owner_name} /><Meta label="Step" value={run.step} /></div>
      <Workflow locale={locale} run={run} />
    </section>
  )
}

function Workflow({ locale, run }: { locale: Locale; run: CodexRun }) {
  return <div className="workflow"><h2>{tr(locale, 'workflow')}</h2><div className="step-track">{run.workflow.map((step) => <div key={step.id} className={`step ${step.status}`}><span /><strong>{step.label}</strong><small>{step.at ?? '--'}</small></div>)}</div></div>
}

function LogAndDiff({ locale, run, events }: { locale: Locale; run: CodexRun; events: RunEvent[] }) {
  return <section className="right-stack"><div className="panel log-panel"><div className="panel-title"><h2>{tr(locale, 'liveLog')}</h2><span>{events.length}</span></div><pre>{events.map((event) => `${event.at} [${event.level.toUpperCase()}] ${event.message}`).join('\n')}</pre></div><div className="panel diff-panel"><div className="panel-title"><h2>{tr(locale, 'diffSummary')} <small>{run.diff_summary.file}</small></h2><span>+{run.diff_summary.added} -{run.diff_summary.removed}</span></div><DiffLines run={run} /></div></section>
}

function DiffLines({ run }: { run: CodexRun }) {
  if (!run.diff_summary.hunks.length) return <div className="empty-state">No diff collected.</div>
  return <div className="diff-lines">{run.diff_summary.hunks.map((hunk, index) => <div key={`${hunk.line}-${index}`} className={hunk.kind}><span>{hunk.line}</span><code>{hunk.text}</code></div>)}</div>
}

function AuditTrail({ locale, audit }: { locale: Locale; audit: AuditEvent[] }) {
  return <section className="panel audit-panel"><div className="panel-title"><h2>{tr(locale, 'auditTrail')}</h2><span>{audit.length}</span></div><div className="audit-table">{audit.slice(0, 6).map((event) => <div key={event.id}><span>{event.at}</span><strong>{event.actor_name}</strong><em>{event.event_code}</em><code>{event.resource}</code></div>)}</div></section>
}

function CodexAccountPanel({ locale, status, onStartLogin }: { locale: Locale; status: CodexAuthStatus; onStartLogin: () => void }) {
  return <section className="panel codex-panel"><div className="panel-title"><h2>{tr(locale, 'codexAccount')}</h2><span>{status.mode}</span></div><div className={`account-state ${status.state}`}>{status.state}</div>{status.login_url ? <code className="login-url">{status.login_url}</code> : null}{status.user_code ? <div className="user-code">{status.user_code}</div> : null}<button className="primary-action" onClick={onStartLogin}>{tr(locale, 'startChatGptLogin')}</button><button className="ghost-action">{tr(locale, 'saveApiKey')}</button></section>
}

function ResourcePanel({ run }: { run: CodexRun }) {
  return <section className="panel resource-panel"><div className="panel-title"><h2>{run.sandbox_id}</h2><span>{run.status}</span></div><div className="radial" style={{ '--value': `${run.resources.cpu}%` } as React.CSSProperties}><strong>{run.resources.cpu}%</strong><span>vCPU</span></div><Meter label="Memory" value={run.resources.memory} max={100} /><Meter label="Disk" value={run.resources.disk} max={100} /><Meter label="Network" value={run.resources.network} max={100} /></section>
}

function EmptyPanel({ text }: { text: string }) {
  return <section className="panel"><div className="empty-state">{text}</div></section>
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

createRoot(document.getElementById('app')!).render(<App />)
