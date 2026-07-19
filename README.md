# Agent-Customer

电商客服 Agent 桌面应用程序，基于 PyQt6 构建，支持电商渠道接入，结合 AI 大模型实现智能自动回复、知识检索与客服辅助决策。

## 功能特性

- **渠道接入能力**：当前已接入电商平台实时消息通道，可持续扩展更多渠道
- **AI 智能回复**：基于自研 Agent 框架（不依赖 Agno），多轮工具调用 + 会话上下文管理
- **AI 主动推荐**：客服代理可主动获取商品列表、发送商品卡片给用户
- **双知识库体系**：产品知识库 + 客服知识库，分别检索商品信息与售后/物流/退款等政策
- **商品知识自动同步**：可从已接入电商平台拉取商品列表，调用多模态 LLM 提取产品知识入库
- **关键词转人工**：自动识别用户意图，支持关键词触发转人工服务
- **消息队列处理**：异步消息队列 + 处理器链，支持高并发场景
- **自动重连机制**：WebSocket 连接支持断线自动重连和心跳检测

### AI Agent 可用工具

| 工具名称 | 功能描述 |
|----------|----------|
| `get_shop_products` | 获取店铺商品列表（支持价格区间、销量、库存、标签等） |
| `send_goods_link` | 向用户发送商品卡片链接 |
| `get_product_knowledge` | 查询指定商品的详细知识（成分、规格、用法、价格等） |
| `search_customer_service_knowledge` | 搜索客服知识库（售后、物流、退款等政策问答） |
| `transfer_conversation` | 转接会话给人工客服 |

## 环境要求

- Python >= 3.11
- Windows 操作系统（打包为 exe 后可在 Windows 上独立运行）

## 安装

```bash
# 安装依赖
uv sync
```

## 启动

```bash
python app.py
```

启动后可在左侧导航栏进入 `本地测试` 页面，直接输入问题演示 Agent 的问答与知识检索能力；页面左侧显示 Agent 对话，右侧显示本次问题命中的 RAG 检索结果，无需依赖真实平台来发送测试消息。

## 配置

首次运行后会在项目根目录生成 `config.json` 配置文件，主要配置项：

| 配置项 | 说明 |
| --- | --- |
| `llm` | LLM 模型配置（模型名称、API 地址、密钥） |
| `embedder` | 向量嵌入模型配置 |
| `knowledge_base` | 知识库存储路径 |
| `business_hours` | 人工客服工作时间（8:00-23:00） |
| `prompt` | AI 客服提示词配置 |

## 开发规范

### 新增/修改接口前

1. **先用 curl 或 Python 脚本测试接口**，确认真实请求参数、请求头、响应结构
2. **根据实际响应结构修改解析代码**，不要凭猜测写字段名
3. **修改后用 mock 数据或真实调用验证解析逻辑**

> 例如：修改已接入平台的商品列表接口时，先用 curl 测试接口，确认真实数据所在字段、字段命名风格以及价格单位，再修改解析代码，不要凭猜测编写字段名。

## 演示数据

如果你当前主要用于功能展示，可以先注入一批本地演示数据：

```bash
python scripts/inject_hardcore_data.py
```

脚本会自动补齐以下内容，方便演示知识检索、客服问答和转人工流程：

- 一个演示店铺和演示账号
- 多条商品知识
- 多条客服政策知识
- 常用转人工关键词

如需直接走免真实登录的演示流程，可在账号管理界面使用 `mock_` 或 `test_` 开头的账号名创建测试账号。

## 构建 Windows 可执行文件

在 Windows 上运行：

```bash
python scripts/build_win_exe.py --clean
```

打包产物位于 `dist/AgentCustomer/` 目录。

## 项目结构

```
text
Agent-Customer/
├── Agent/                  # AI 代理模块（自研 Agent 框架）
│   └── CustomerAgent/
│       ├── custom/         # 自研实现：LLM 客户端、会话管理、工具执行器
│       └── tools/          # Agent 工具集（商品/知识/转人工）
├── Channel/                # 渠道集成（当前包含已接入平台实现）
│   └── pinduoduo/
│       ├── core/           # 连接、生命周期、状态、消息处理拆分模块
│       └── utils/API/      # 平台 API 封装
├── Message/                # 消息处理（队列 + 处理器链）
│   ├── core/               # consumer / handlers / queue
│   └── handlers/           # 预处理器、AI、关键词处理器
├── bridge/                 # 桥接模块（Context/Reply）
├── core/                   # 核心服务（DI 容器、缓存、连接状态）
├── database/               # 数据库（SQLAlchemy + 知识服务 + 商品同步）
├── ui/                     # PyQt6 用户界面
├── utils/                  # 工具模块（日志、路径等）
├── scripts/                # 构建脚本
└── app.py                  # 应用入口
```

## 技术栈

| 类别 | 技术 |
|------|------|
| UI 框架 | PyQt6 + pyqt6-fluent-widgets |
| AI 框架 | 自研 Agent 框架 + OpenAI 兼容 API |
| 数据库 | SQLAlchemy + SQLite |
| 中文分词 | jieba（知识库检索） |
| Token 统计 | tiktoken |
| 异步通信 | asyncio + websockets |
| 文档解析 | pypdf + python-docx + openpyxl + xlrd |
| 日志 | Loguru |
| 配置 | Pydantic |

## License

MIT
