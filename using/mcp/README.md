# MCP

> 用好 AI

MCP（Model Context Protocol，模型上下文协议）让 AI 能连接外部系统 — 查数据库、调 API、读写文件、操作工具。没有它，AI 只能「给建议」；有了它，AI 能「真动手」。

---

## 一、为什么需要 MCP

### AI 的天然限制

大模型本质上是一个封闭系统：你给它文本，它返回文本。它不能访问互联网，不能查你的数据库，不能调你的 API，不能写文件到你的磁盘。

这意味着很多实际任务它做不了：

> - 「统计最近 7 天的 iOS 崩溃率」— 它没有 Crashlytics 的数据
> - 「帮我在 Jira 上创建一个 Bug 单」— 它连不上 Jira
> - 「读一下项目根目录的配置文件」— 它看不到你的文件系统

之前几篇讲的 [Prompt](../prompt/)、[Rules](../rules/)、[Skills](../skills/) 都在解决「AI 怎么思考和执行」的问题。但如果 AI 没有「手」去触达真实世界，再好的思考也只能停留在纸面上。

**MCP 就是给 AI 装上「手」的标准协议。**

### 没有 MCP 之前

AI 接入外部工具的方式是：每对接一个工具，写一套适配代码。

接 GitHub？写一套。接 Slack？再写一套。接数据库？再写一套。换一个 AI 工具？全部重写。

M 个 AI 应用 × N 个外部工具 = M × N 个适配器。工作量随工具数量爆炸式增长。

### MCP 的解决方式

MCP 定义了一个统一协议：**工具端实现一次 MCP Server，就能被所有支持 MCP 的 AI 调用；AI 端实现一次 MCP Client，就能接入所有 MCP Server。** M × N 变成 M + N。

这和 USB 的故事一样 — USB 出现之前，每个外设有自己的接口；USB 出现之后，一个标准走天下。MCP 就是 AI 世界的 USB。

---

## 二、MCP 的工作方式

### 三个角色

| 角色 | 作用 | 示例 |
|------|------|------|
| **Host（宿主）** | 面向用户的 AI 应用 | Claude Desktop、Cursor、Claude Code |
| **Client（客户端）** | Host 内部负责通信的模块 | 自动管理，用户无需关心 |
| **Server（服务端）** | 工具和数据源的提供方 | GitHub Server、数据库 Server、文件系统 Server |

你使用 AI 应用（Host），AI 应用通过 MCP 协议（Client）连接到各种工具（Server）。

### 一次调用的流程

以「查询数据库」为例：

```
你说：「查一下最近 7 天的活跃用户数」
    ↓
AI 理解意图，决定需要查询数据库
    ↓
AI 通过 MCP 协议调用数据库 Server
    ↓
Server 执行 SQL 查询，返回结果
    ↓
AI 基于结果生成回答：「最近 7 天活跃用户 12,483 人，环比增长 8.2%」
```

整个过程中，MCP 负责的是中间那一步 — **让 AI 的「意图」变成对外部系统的「操作」，再把「结果」传回给 AI**。

### Server 提供的三种能力

| 能力 | 作用 | 示例 |
|------|------|------|
| **Tools（工具）** | 可被 AI 调用的函数 | 查询数据库、发消息、创建文件 |
| **Resources（资源）** | 可被读取的数据 | 文件内容、配置信息、API 响应 |
| **Prompts（模板）** | 预定义的 Prompt 模板 | 代码审查模板、分析报告模板 |

最常用的是 Tools — AI 判断需要做某个操作时，调用对应的 Tool，拿到结果后继续推理。

### 两种通信方式

| 模式 | 通信方式 | 适用场景 |
|------|---------|---------|
| **Stdio** | 本地进程间通信（stdin/stdout） | 本地工具：文件操作、命令执行、浏览器桥接 |
| **HTTP** | 网络请求 | 远程服务：云端 API、跨机器调用 |

Stdio 模式下，AI 工具启动时会把 MCP Server 作为本地子进程运行，通过标准输入输出通信，速度快、无需网络。HTTP 模式则适合连接远程服务，和调用 REST API 的体验类似。

---

## 三、常见的 MCP Server

社区已经有大量现成的 MCP Server，覆盖了常见的开发场景：

| MCP Server | 能力 | 典型场景 |
|-----------|------|---------|
| **filesystem** | 读写本地文件 | 读取配置、生成代码文件 |
| **github** | 操作 GitHub 仓库 | 创建 PR、查看 Issue、读取代码 |
| **postgres / mysql** | 数据库查询 | 数据分析、表结构查看 |
| **browser** | 浏览器自动化 | 网页抓取、前端测试 |
| **sentry** | 错误监控 | 崩溃分析、日志查询 |
| **slack / 飞书** | 消息通知 | 发送通知、查询聊天记录 |
| **brave-search** | 搜索引擎 | 查询最新信息 |

不需要自己写这些 Server，直接配置即可使用。

### 配置方式

以 Claude Code 为例，在配置文件中声明要连接的 Server：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-filesystem"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-github"]
    }
  }
}
```

配置完成后，AI 就可以在对话中调用这些工具 — 不需要修改 AI 应用的任何代码。

### 工具描述决定调用质量

AI 完全依赖 Tool 的名称、描述和参数定义来决定「什么时候调用」和「怎么传参」。描述写得不好，AI 要么不调用，要么传错参数。

| 写法 | 效果 |
|------|------|
| ❌ `name: "query"`, `description: "查询数据"` | AI 不知道查什么数据、参数传什么 |
| ✅ `name: "search_documents"`, `description: "在知识库中搜索文档，返回最相关的前 5 条结果"` | AI 能准确理解能力边界和使用场景 |

核心原则：**把工具描述当作给 AI 看的 API 文档来写** — 名称有语义，描述说清功能边界，参数给出示例值。

### 去哪里找现成的 MCP Server

在动手自己写之前，先看看有没有现成的。MCP 官方维护了一个 Server 目录，覆盖了数据库、云服务、开发工具、生产力工具等常见场景：

- [MCP 官方 Server 仓库](https://github.com/modelcontextprotocol/servers)
- [MCP 协议规范文档](https://modelcontextprotocol.io)

---

## 四、MCP 与相关概念的区别

MCP 容易和 Function Calling、Plugin 混淆。三者的关系：

| 概念 | 层次 | 作用 | 类比 |
|------|------|------|------|
| **Function Calling** | 调用机制 | LLM 发出「我要调用某个函数」的指令 | 拧螺丝这个动作 |
| **Plugin** | 工具封装 | 把一个工具的 API 包装成 AI 可调用的格式 | 一把螺丝刀 |
| **MCP** | 标准协议 | 定义 AI 和所有工具之间的通信标准 | USB 接口标准 |

Function Calling 是最底层的机制，Plugin 是对单个工具的封装，MCP 是让所有工具用统一方式接入的协议。

另一个关键区别：**Function Calling 是特定厂商的 API 特性**（如 OpenAI 的 Function Calling 只能用于 OpenAI 模型），**MCP 是开放标准**，任何 AI 模型都可以通过它接入工具。

---

## 五、安全性：MCP 如何做到可控

企业使用 AI 最关心的是：AI 能调外部工具了，怎么保证它不乱来？

MCP 在协议层面提供了几个安全机制：

- **权限控制**：可以限制 MCP Server 只暴露特定的 Tools。比如一个只读的代码审查 Server，只允许 Read 和 Grep，不允许 Write 和 Edit
- **操作确认**：AI 调用工具前可以要求用户确认，而不是静默执行
- **操作审计**：所有工具调用都有记录，可以追溯「谁在什么时候调了什么工具」
- **沙箱隔离**：MCP Server 作为独立进程运行，和 AI 应用隔离

这些机制让 AI 在「能力扩展」和「安全可控」之间找到了平衡 — AI 可以调工具，但在受控的范围内调。

---

## 六、从 iOS 开发者视角理解

MCP 很像 iOS 开发中的 REST API 调用。

iOS App 通过网络请求和后端交互：

```
App → URLSession → REST API → 后端服务 → 数据库
```

AI 通过 MCP 和外部系统交互：

```
AI → MCP Client → MCP Server → 外部系统（数据库 / API / 文件）
```

结构完全一致。MCP Server 就是后端服务，MCP 协议就是 HTTP，AI 就是发起请求的客户端。

一个实际例子：你让 AI 助手「统计最近 7 天 iOS 崩溃率」，背后的流程是：

1. AI 通过 MCP 调用 Crashlytics Server，查询崩溃数据
2. AI 通过 MCP 调用数据库 Server，查询用户量数据
3. AI 基于两份数据计算崩溃率，生成分析报告
4. AI 通过 MCP 调用飞书 Server，把报告发到团队群

每一步的 MCP 调用，就是一次「网络请求」。

---

## 七、小结

| 维度 | 要点 |
|------|------|
| **MCP 是什么** | AI 连接外部系统的标准协议 |
| **解决什么问题** | 让 AI 从「只能给建议」变成「能真动手执行」 |
| **核心价值** | 统一标准（M+N 代替 M×N）+ 安全可控（权限管理 + 操作审计） |
| **工作方式** | Host（AI 应用）→ Client → Server（工具） |
| **和 Function Calling 的区别** | MCP 是开放标准协议，不绑定特定 AI 厂商 |
