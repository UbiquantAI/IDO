# Features Overview

Learn about iDO's main features and how to use them effectively.

## 🎯 What is iDO?

iDO is a local-first AI desktop copilot that:

- **📊 Tracks your activity** - Monitors what you do on your computer
- **🤖 Summarizes with AI** - Uses LLMs to understand context
- **✅ Recommends tasks** - Suggests what to do next based on your patterns
- **🔒 Keeps data private** - Everything stays on your device

## Main Features

### 1. Pomodoro Focus Mode

**What it does**: Intelligent Pomodoro timer with task linking, mode selection, and focus tracking

**How to use**:
1. Navigate to **Pomodoro** in the sidebar
2. Left panel shows your scheduled todos - click one to select
3. Or enter a custom task description manually
4. Choose a mode: Classic (25/5), Deep (50/10), Quick (15/3), Focus (90/15)
5. Click **Start** to begin

**Interface**:
- **Left sidebar**: Scheduled todos with count badge for quick selection
- **Main panel**: Timer display with mode selector and task input
- **Task association**: Link sessions to AI-generated todos or manual intent

**Features**:
- 4 preset modes with customizable duration
- Links sessions to AI-generated todos
- Real-time countdown with circular progress
- Phase notifications (work/break transitions)
- Activity capture during work phases

### 2. Pomodoro Review

**What it does**: Session history with statistics overview, activity timelines, and AI-powered focus analysis

**How to use**:
1. Navigate to **Pomodoro Review** in the sidebar
2. View period statistics (weekly total, daily average, completion rate)
3. Check the weekly focus chart for trends
4. Select a date using the date picker
5. Browse sessions and click to view detailed breakdown
6. Review AI-generated focus analysis in the session dialog

**Interface**:
- **Statistics Overview Cards**: Weekly total, focus hours, daily average, completion rate
- **Weekly Focus Chart**: Bar chart showing daily focus minutes with goal line
- **Time Period Selector**: Switch between week/month/year views
- **Date Picker**: Select specific dates to view sessions
- **Session List**: Click sessions to open detailed dialog
- **Session Detail Dialog**: Shows focus metrics, activity timeline, LLM analysis

**Features**:
- Period statistics with visual overview
- Activity timeline during each session
- AI-powered focus quality evaluation (strengths, weaknesses, suggestions)
- Work type analysis (deep work, distractions, focus streaks)
- Weekly focus goal tracking
- Distraction percentage analysis

### 3. Knowledge

**What it does**: Turns your daily activities into searchable, long-term knowledge cards with AI-powered organization

**How to use**:
1. Navigate to **Knowledge** in the sidebar
2. Use left sidebar to filter by category/keyword
3. Search or filter (All/Favorites/Recent)
4. Click a card to view details or edit
5. Use **Smart Merge** to find and combine similar knowledge
6. Create new notes manually

**Interface**:
- **Left Sidebar**: Category filter showing keyword counts
- **Search Bar**: Full-text search across titles, descriptions, keywords
- **Filter Tabs**: All / Favorites / Recent (last 7 days)
- **Action Buttons**: Smart Merge, New Note
- **Knowledge Cards Grid**: Scrollable card list with hover actions
- **Detail Dialog**: View/edit knowledge details

**Features**:
- AI-generated from activities
- Full-text search across all cards
- Favorites with quick toggle
- Category/keyword filtering
- Smart duplicate detection and merging with configurable thresholds
- Create manual notes
- Retry dialog for LLM errors

### 4. Todos

**What it does**: AI-generated tasks with calendar scheduling, priority levels, and Pomodoro linking

**How to use**:
1. Navigate to **Todos** in the sidebar
2. Toggle between Cards View and Calendar View
3. Use left sidebar to filter by category/keyword
4. Click a todo to view details or edit
5. Drag todos to calendar to schedule
6. Click **Create Todo** to add manually
7. Send todos to Chat for agent execution

**Interface**:
- **View Mode Toggle**: Switch between Cards and Calendar views
- **Left Sidebar**: Category filter
- **Cards View**: Grid of todo cards with hover actions
- **Calendar View**: Full calendar with drag-to-schedule
- **Pending Section**: Quick access to unscheduled todos (calendar view)
- **Detail Dialog**: View/edit schedule, recurrence, send to chat
- **Create Todo Dialog**: Manual todo creation

**Features**:
- Auto-generated from activities
- Manual creation supported
- Calendar scheduling with start/end times
- Recurrence rules (daily, weekly, etc.)
- Keywords and priority levels
- Drag-and-drop to calendar
- Send to Chat for AI execution
- Linked to Pomodoro sessions
- Filter by category

### 5. Diary

**What it does**: AI-generated daily work summaries to reflect on your progress and track achievements

**How to use**:
1. Navigate to **Diary** in the sidebar
2. Scroll through past diaries or use date picker
3. Click a diary card to view full content
4. Edit summaries as needed
5. Select a date and click **Generate Diary** to create new

**Interface**:
- **Action Bar**: Refresh, Load More, Date Picker, Generate button
- **Diary Cards**: Scrollable list of daily summaries
- **Diary Card**: Shows date, key highlights, work categories

**Features**:
- AI-generated daily summaries
- Scrollable history with load more
- Select specific dates to generate
- Editable content
- Key highlights extraction
- Work type categorization
- Delete diaries

### 6. Chat

**What it does**: Conversational interface about your activity history with streaming responses and image support

**How to use**:
1. Navigate to **Chat** in the sidebar
2. Select an existing conversation or create a new one
3. Type a question about your activities
4. Get streaming responses grounded in your data
5. Optionally drag & drop images to analyze

**Interface**:
- **Left Sidebar**: Conversation list with new/delete actions (desktop)
- **Mobile Overlay**: Slide-out conversation list (mobile)
- **Message Area**: Scrollable message history with streaming support
- **Activity Context**: Shown when conversation is linked to an activity
- **Input Area**: Text input with image drag-drop, model selector

**Features**:
- Context-aware responses grounded in your activity data
- Streaming AI responses for real-time feedback
- Image drag-and-drop support (PNG, JPG, GIF)
- Model selection per conversation
- Auto-generated conversation titles
- Activity context linking
- Send todos/knowledge to chat from other pages
- Retry failed responses
- Cancel streaming responses

**Example questions**:
- "What did I work on yesterday?"
- "How much time did I spend coding this week?"
- "What were my main activities?"
- "Summarize my focus sessions from last week"

### 7. Dashboard

**What it does**: LLM usage statistics, token tracking, cost analysis, and productivity insights

**How to use**:
1. Navigate to **Dashboard** in the sidebar
2. Filter by all models or select a specific model
3. View token usage, API calls, and cost metrics
4. Check usage trends over time with interactive chart

**Interface**:
- **Model Filter**: Dropdown to select all models or specific model
- **LLM Stats Cards Grid**:
  - Total Tokens (with description)
  - Total API Calls (with description)
  - Total Cost (single model view)
  - Models Used (all models view)
  - Model Price (single model view)
- **Usage Trend Chart**: Interactive chart with dimension and range selectors
- **Trend Dimensions**: Focus minutes, LLM tokens, API calls
- **Trend Ranges**: Week, Month, Year

**Features**:
- Real-time LLM usage statistics
- Token count and API call tracking
- Cost analysis per model
- Usage trend visualization
- Model performance comparison
- Currency-aware cost display
- Responsive layout for all screen sizes

**Metrics tracked**:
- Total tokens processed
- Total API calls made
- Total cost (currency-formatted)
- Models used in selected period
- Per-million-token pricing (input/output)

## Interface Overview

### Sidebar Navigation

| Icon | Page | Description |
|------|------|-------------|
| Timer | Pomodoro | Focus timer with task linking |
| History | Pomodoro Review | Session history and metrics |
| BookOpen | Knowledge | AI-generated knowledge cards |
| CheckSquare | Todos | AI-generated tasks |
| NotebookPen | Diary | Daily work summaries |
| MessageSquare | Chat | Conversational AI about your history |
| BarChart | Dashboard | Focus statistics and trends |
| Settings | Settings | App configuration (bottom) |

### Data Storage

All data is stored locally:

- **macOS**: `~/.config/ido/`
- **Windows**: `%APPDATA%\ido\`
- **Linux**: `~/.config/ido/`

Contains:
- `ido.db` - SQLite database
- `screenshots/` - Captured screenshots
- `logs/` - Application logs

## Privacy Features

### What iDO Respects

✅ **Local storage** - Everything stays on your device
✅ **Your API key** - Use your own LLM provider
✅ **Selective capture** - Choose which monitors to record
✅ **No telemetry** - iDO doesn't phone home
✅ **Open source** - Audit the code yourself

### What to Be Aware Of

⚠️ **Screenshots contain visible content** - Don't capture sensitive screens
⚠️ **LLM sees screenshots** - Sent to OpenAI/your provider
⚠️ **Database is unencrypted** - Store in encrypted volume if needed
⚠️ **Logs may contain info** - Review before sharing

## Performance

- **CPU usage**: ~2-5% during capture
- **Memory**: ~200-500 MB RAM
- **Disk**: ~100-500 MB per day (varies by interval and quality)
- **Screenshot interval**: 0.2 seconds (5 screenshots/sec/monitor)

## Next Steps

- **[Installation Guide](./installation.md)** - Set up iDO
- **[FAQ](./faq.md)** - Common questions
- **[Troubleshooting](./troubleshooting.md)** - Fix issues

## Need Help?

- 🐛 **Report Issues**: [GitHub Issues](https://github.com/UbiquantAI/iDO/issues)
- 💬 **Ask Questions**: [GitHub Discussions](https://github.com/UbiquantAI/iDO/discussions)
- 📖 **Documentation**: [Full Docs](../README.md)

---

**Navigation**: [← Installation](./installation.md) • [User Guide Home](./README.md) • [FAQ →](./faq.md)
