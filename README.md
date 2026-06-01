<div align="center">

<picture>
  <img alt="iDO" src="assets/iDO_banner.png" width="100%" height="auto">
</picture>

### iDO: Turn every moment into momentum

[English](README.md) | [简体中文](README.zh-CN.md)

A locally deployed AI desktop assistant that understands your activity stream, uses LLMs to summarize context, helps organize your work and knowledge, and recommends next steps—with all processing done entirely on your device.

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

</div>

---

## ✨ Key Features

- **💻 Cross-Platform**: Works seamlessly on macOS, Windows, and Linux
- **🔒 Privacy-First**: All data processing happens locally on your device
- **🍅 Pomodoro Focus**: Intelligent timer with task linking, focus scoring, and session review
- **📚 Knowledge Capture**: AI turns activities into searchable knowledge cards with smart merge
- **✅ Smart Todos**: AI-generated tasks with scheduling, priorities, and Pomodoro linking
- **📓 Daily Diary**: AI-generated work summaries to reflect on your progress
- **💬 Contextual Chat**: Ask questions about your activities with grounded answers

---

## 📸 Feature Demos

### Knowledge

![Knowledge demo](assets/knowledge.gif)

AI turns your daily activities into searchable knowledge cards. Find what you learned, organize with categories, and use Smart Merge to combine duplicates.

**Features**:

- Full-text search across all cards
- Category/keyword filtering
- Smart duplicate detection and merging
- Create manual notes

### Todos

![Todos demo](assets/todo.gif)

AI-generated tasks from your context. Schedule on calendar, set priorities, and link to Pomodoro sessions. Drag to calendar to schedule.

**Features**:

- Manual creation supported
- Calendar scheduling with start/end times
- Recurrence rules (daily, weekly, etc.)
- Send to Chat for AI execution

### Pomodoro

Focus Mode: Start a Pomodoro session to capture and analyze your focused work. Configure work/break durations and track progress.

**What it does**: Focus Mode with intelligent Pomodoro timer for capturing and analyzing your focused work

**Features**:

- 4 preset modes: Classic (25/5), Deep (50/10), Quick (15/3), Focus (90/15)
- Task association with AI-generated todos
- Real-time countdown with circular progress
- Phase notifications (work/break transitions)

### Pomodoro Review

Review your focus sessions and track your productivity. View activity timelines, AI-powered focus analysis, and weekly statistics.

**Features**:

- Session history with duration and timestamps
- AI focus quality evaluation (strengths, weaknesses, suggestions)
- Work type analysis (deep work, distractions, focus streaks)
- Weekly focus goal tracking

### Diary

![Diary demo](assets/diary.gif)

AI-generated daily work summaries. Scroll through history, select dates to generate, and edit summaries to reflect on your progress.

**Features**:

- Daily automated summaries
- Select specific dates to generate
- Editable content
- Scrollable history with load more

### Chat

![Chat demo](assets/chat.gif)

Conversational AI about your activities with streaming responses. Ask questions, analyze images, and get grounded answers from your data.

**Features**:

- Streaming responses for real-time feedback
- Image drag-and-drop support (PNG, JPG, GIF)
- Model selection per conversation
- Send todos/knowledge from other pages

### Dashboard

![Dashboard demo](assets/dashboard.gif)

View Token usage and Agent task statistics. Track token consumption, API calls, and costs across all your models.

**What it does**: View Token usage and Agent task statistics

**Metrics**:

- Total tokens processed and API calls made
- Total cost by model with currency display
- Usage trends over week/month/year
- Per-model price tracking (input/output tokens)

---

## 🏗️ Architecture

<div align="center">
  <img src="assets/arch-en.png" width="60%" alt="Architecture"/>
</div>

iDO works in three intelligent layers:

1. **Perception Layer** - Monitors keyboard, mouse, screen activity in real-time
2. **Processing Layer** - AI filters noise and organizes meaningful activities
3. **Consumption Layer** - Delivers insights, tasks, and context when you need them

### Tech Stack

**Frontend:** React 19 + TypeScript 5 + Vite 6 + Tailwind CSS 4 + shadcn/ui + Zustand 5 + TanStack React Query 5

**Backend:** Python 3.14+ + Tauri 2.x + PyTauri 0.8 + FastAPI + SQLite

**AI/ML:** OpenAI-compatible APIs + smolagents framework + LLM-powered summarization

---

## 🚀 Quick Start

### Prerequisites

- [Node.js 22+](https://nodejs.org/)
- [Python 3.14+](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- [pnpm](https://pnpm.io/) - Fast package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/UbiquantAI/iDO.git
cd iDO

# Install dependencies
pnpm setup

# Start development with type generation
pnpm tauri:dev:gen-ts
```

### Available Commands

| Command                 | Description                               |
| ----------------------- | ----------------------------------------- |
| `pnpm dev`              | Frontend only                             |
| `pnpm tauri:dev:gen-ts` | Full app with TS generation (recommended) |
| `pnpm format`           | Format code                               |
| `pnpm check-i18n`       | Validate translations                     |
| `uv run ty check`       | Backend type checking                     |
| `pnpm tsc`              | Frontend type checking                    |
| `pnpm bundle`           | Production build (macOS/Linux)            |
| `pnpm bundle:win`       | Production build (Windows)                |

---

## 🎯 Core Features

### Perception Layer

- **Smart Capture**: Only records when user is active
- **Screenshot Deduplication**: Image hashing avoids redundant captures
- **Activity Detection**: Classifies "operation" vs "browsing" behavior
- **Window Tracking**: Knows which app you're using

### Processing Layer

- **Event Extraction**: LLM extracts meaningful actions from screenshots
- **Activity Aggregation**: Groups related actions into activities (10min intervals)
- **Smart Filtering**: AI separates signal from noise

### Consumption Layer

- **AI Task Generation**: Automatically creates todos from your activities
- **Knowledge Capture**: Long-term memory from daily work
- **Daily Diaries**: AI-generated work summaries
- **Pomodoro Timer**: Focus sessions with task linking and focus scoring

### Knowledge Management

- **AI-Powered Search**: Find anything you've done
- **Knowledge Merge**: Smart duplicate detection and merging
- **Favorites & Categories**: Organize your knowledge base

### Pomodoro Focus Mode

- **Configurable Timer**: Work duration, break duration, rounds
- **Task Association**: Link sessions to AI-generated todos
- **Focus Scoring**: AI evaluates each session's focus quality
- **Session Review**: Detailed breakdowns with activity timelines
- **Progress Tracking**: Weekly focus statistics and trends

---

## 📁 Project Structure

```
ido/
├── src/                     # React frontend
│   ├── views/              # Page components
│   ├── components/         # UI components
│   ├── lib/
│   │   ├── stores/         # Zustand stores
│   │   ├── client/         # Auto-generated API client
│   │   └── types/          # TypeScript types
│   ├── hooks/              # Custom React hooks
│   └── locales/            # i18n translations
├── backend/                 # Python backend
│   ├── handlers/           # API handlers
│   ├── core/               # Core systems
│   ├── perception/         # Perception layer
│   ├── processing/         # Processing pipeline
│   ├── agents/             # AI agents
│   └── llm/                # LLM integration
├── src-tauri/              # Tauri app
└── scripts/                # Build scripts
```

---

## 📖 Documentation

- 📚 [User Guide](docs/user-guide/README.md)
- 📚 [Developer Guide](docs/developers/README.md)
- 📚 [API Reference](docs/developers/reference/)
- 📚 [Architecture](docs/developers/architecture/README.md)

---

## 🤝 Contributing

We welcome contributions! Check out the [Contributing Guide](docs/developers/getting-started/development-workflow.md) to get started.

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Tauri](https://tauri.app/) - Modern desktop framework
- Powered by [PyTauri](https://pytauri.github.io/) - Python ↔ Rust bridge
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Icons from [Lucide](https://lucide.dev/)
- Agent framework [smolagents](https://github.com/huggingface/smolagents)

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

**[📖 Documentation](docs/README.md)** • **[👥 User Guide](docs/user-guide/README.md)** • **[💻 Developer Guide](docs/developers/README.md)**

Made with ❤️ by the iDO team

</div>
