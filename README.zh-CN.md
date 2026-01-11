<div align="center">

<picture>
  <img alt="iDO" src="assets/iDO_banner.png" width="100%" height="auto">
</picture>

### iDO: Turn every moment into momentum

[English](README.md) | [简体中文](README.zh-CN.md)

本地部署的 AI 桌面助手，读懂你的活动流，使用 LLM 总结上下文，帮你整理所做的事情、所学的知识并推荐下一步任务——所有处理都在你的设备上完成。

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

</div>

---

## ✨ 核心特性

- **💻 跨平台支持**：在 macOS、Windows 和 Linux 上无缝运行
- **🔒 隐私优先**：所有数据处理都在你的设备本地完成
- **🍅 番茄钟专注**：智能计时器，支持任务关联、专注评分和会话回顾
- **📚 知识捕获**：AI 将活动转化为可搜索的知识卡片，支持智能合并
- **✅ 智能待办**：AI 生成任务，支持日程安排、优先级设置和番茄钟关联
- **📓 每日日记**：AI 生成工作摘要，帮助你反思进度
- **💬 上下文对话**：基于你的活动数据回答问题

---

## 📸 功能演示

### 知识

![知识演示](assets/knowledge.gif)

AI 将你的日常活动转化为可搜索的知识卡片。查找你学到的东西，通过分类组织，使用智能合并来整合重复内容。

**功能**：
- 全文搜索所有卡片
- 分类/关键词过滤
- 智能重复检测和合并
- 创建手动笔记

### 待办

![待办演示](assets/todo.gif)

从你的上下文中生成 AI 任务。在日历上安排，设置优先级，关联番茄钟会话。拖放到日历进行安排。

**功能**：
- 支持手动创建
- 日程安排（开始/结束时间）
- 循环规则（每日、每周等）
- 发送到 Chat 进行 AI 执行

### 番茄钟

通过智能番茄钟会话保持专注，与任务管理无缝衔接。可配置工作/休息时长，追踪专注评分，查看详细会话分解。

**功能**：
- 4种模式：经典 (25/5)、深度 (50/10)、快速 (15/3)、专注 (90/15)
- 与 AI 生成的任务关联
- 实时倒计时与环形进度
- 阶段通知（工作/休息切换）

### 番茄钟回顾

回顾过去的专注会话，查看详细分解。活动时间线、AI 专注分析和每周统计数据。

**功能**：
- 带时间戳的会话历史
- AI 专注质量评估（优势、劣势、建议）
- 工作类型分析（深度工作、分心、专注 streaks）
- 每周专注目标追踪

### 日记

![日记演示](assets/diary.gif)

AI 生成的每日工作摘要。浏览历史，选择日期生成，编辑摘要以反思你的进度。

**功能**：
- 每日自动摘要
- 选择特定日期生成
- 可编辑内容
- 滚动历史（加载更多）

### 聊天

![聊天演示](assets/chat.gif)

关于你的活动的对话式 AI，支持流式响应。提出问题、分析图片，从你的数据中获得有依据的回答。

**功能**：
- 流式响应，实时反馈
- 图片拖放支持（PNG、JPG、GIF）
- 每个对话可选择模型
- 从其他页面发送待办/知识

### 仪表盘

![仪表盘演示](assets/dashboard.gif)

追踪 LLM 使用统计、Token 消耗、API 调用和成本，查看所有模型的交互趋势图表。

**指标**：
- Token 处理总量和 API 调用次数
- 按模型显示成本，支持多币种
- 周/月/年使用趋势
- 按模型价格追踪（输入/输出 Token）

---

## 🏗️ 系统架构

<div align="center">
  <img src="assets/arch-zh.png" width="60%" alt="架构"/>
</div>

iDO 分三个智能层级工作：

1. **感知层** - 实时监控键盘、鼠标、屏幕活动
2. **处理层** - AI 过滤噪音并组织有意义的活动
3. **呈现层** - 在你需要时提供洞察、任务和上下文

### 技术栈

**前端：** React 19 + TypeScript 5 + Vite 6 + Tailwind CSS 4 + shadcn/ui + Zustand 5 + TanStack React Query 5

**后端：** Python 3.14+ + Tauri 2.x + PyTauri 0.8 + FastAPI + SQLite

**AI/ML：** OpenAI 兼容 API + smolagents 框架 + LLM 驱动的总结

---

## 🚀 快速开始

### 环境要求

- [Node.js 22+](https://nodejs.org/)
- [Python 3.14+](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) - 快速 Python 包管理器
- [pnpm](https://pnpm.io/) - 快速包管理器

### 安装

```bash
# 克隆仓库
git clone https://github.com/UbiquantAI/iDO.git
cd iDO

# 安装依赖
pnpm setup

# 启动开发（推荐，带类型生成）
pnpm tauri:dev:gen-ts
```

### 可用命令

| 命令 | 描述 |
|------|------|
| `pnpm dev` | 仅前端 |
| `pnpm tauri:dev:gen-ts` | 完整应用（推荐） |
| `pnpm format` | 格式化代码 |
| `pnpm check-i18n` | 验证翻译 |
| `uv run ty check` | 后端类型检查 |
| `pnpm tsc` | 前端类型检查 |
| `pnpm bundle` | 生产构建（macOS/Linux） |
| `pnpm bundle:win` | 生产构建（Windows） |

---

## 🎯 核心功能

### 感知层

- **智能捕获**：仅在用户活跃时记录
- **截图去重**：图像哈希避免冗余捕获
- **活动检测**：区分"操作"与"浏览"行为
- **窗口跟踪**：了解你正在使用的应用

### 处理层

- **事件提取**：LLM 从截图中提取有意义的操作
- **活动聚合**：将相关操作分组为活动（10分钟间隔）
- **智能过滤**：AI 分离信号与噪音

### 呈现层

- **AI 任务生成**：从活动中自动创建待办
- **知识捕获**：从日常工作中建立长期记忆
- **每日日记**：AI 生成的工作摘要
- **番茄钟计时器**：带任务关联和专注评分的专注会话

### 知识管理

- **AI 驱动搜索**：查找你做过的任何事
- **知识合并**：智能重复检测和合并
- **收藏与分类**：组织你的知识库

### 番茄钟专注模式

- **可配置计时器**：工作时长、休息时长、轮数
- **任务关联**：将会话与 AI 生成的待办关联
- **专注评分**：AI 评估每次会话的专注质量
- **会话回顾**：包含活动时间线的详细分解
- **进度追踪**：周度专注统计和趋势

---

## 📁 项目结构

```
ido/
├── src/                     # React 前端
│   ├── views/              # 页面组件
│   ├── components/         # UI 组件
│   ├── lib/
│   │   ├── stores/         # Zustand 状态管理
│   │   ├── client/         # 自动生成的 API 客户端
│   │   └── types/          # TypeScript 类型
│   ├── hooks/              # 自定义 React Hooks
│   └── locales/            # i18n 翻译
├── backend/                 # Python 后端
│   ├── handlers/           # API 处理器
│   ├── core/               # 核心系统
│   ├── perception/         # 感知层
│   ├── processing/         # 处理管道
│   ├── agents/             # AI 代理
│   └── llm/                # LLM 集成
├── src-tauri/              # Tauri 应用
└── scripts/                # 构建脚本
```

---

## 📖 文档

- 📚 [用户指南](docs/user-guide/README.md)
- 📚 [开发者指南](docs/developers/README.md)
- 📚 [API 参考](docs/developers/reference/)
- 📚 [架构设计](docs/developers/architecture/README.md)

---

## 🤝 贡献

我们欢迎各种形式的贡献！查看[贡献指南](docs/developers/getting-started/development-workflow.md)了解如何开始。

---

## 📄 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 基于 [Tauri](https://tauri.app/) 构建 - 现代桌面框架
- 由 [PyTauri](https://pytauri.github.io/) 驱动 - Python ↔ Rust 桥接
- UI 组件来自 [shadcn/ui](https://ui.shadcn.com/)
- 图标来自 [Lucide](https://lucide.dev/)
- Agent 框架 [smolagents](https://github.com/huggingface/smolagents)

---

## 👥 Maintainers

<div>
  <a href="https://github.com/IcyFeather233">
    <img src="https://github.com/IcyFeather233.png" width="64" height="64" alt="IcyFeather233" style="border-radius: 50%;" />
  </a>
  <a href="https://github.com/thinksoso">
    <img src="https://github.com/thinksoso.png" width="64" height="64" alt="thinksoso" style="border-radius: 50%;" />
  </a>
</div>

## 🙌 Contributors

<div>
  <a href="https://github.com/TexasOct">
    <img src="https://github.com/TexasOct.png" width="64" height="64" alt="TexasOct" style="border-radius: 50%;" />
  </a>
  <a href="https://github.com/EvagelineFEI">
    <img src="https://github.com/EvagelineFEI.png" width="64" height="64" alt="EvagelineFEI" style="border-radius: 50%;" />
  </a>
</div>

---

<div align="center">

**[📖 文档](docs/README.md)** • **[👥 用户指南](docs/user-guide/README.md)** • **[💻 开发者指南](docs/developers/README.md)**

iDO 团队用 ❤️ 制作

</div>
