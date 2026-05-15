# AGENTS.zh-CN.md

## 项目约定

Sandbox Control 是一个 Python/FastAPI + React/Vite 内部平台，用于管理实验性单机 E2B 风格沙箱基础设施和远程 Codex 会话。

## 工程规则

- `README.md` 与 `README.zh-CN.md` 必须保持结构对齐。
- `AGENTS.md` 是英文源文件，本文件是中文镜像。
- 禁止提交密钥、密码、API key、Git PAT、Codex `auth.json`、运行态数据或真实 `.env`。
- 除非预检和运行时 smoke test 已证明成功，否则不能声称 Firecracker/E2B runtime 可用。
- 所有可见产品文案、状态、错误和审计事件名称都必须保留中英双语 i18n。
- 单机 E2B 是实验路径。即使 Firecracker 被阻塞，控制面仍可运行，但 UI 必须显示阻塞原因。

## 验证

- 后端：`uv run pytest`。
- 前端：在 `apps/web` 运行 `npm test` 和 `npm run build`。
- 产品 smoke：登录、切换语言、启动 Codex 登录、创建 run、批准 run、打开对话页、查看 Infra 预检。
