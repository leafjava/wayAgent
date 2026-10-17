# TokenTruth

> **让投资者问得明白，让项目方讲得清楚**
> 基于可验证 AI 知识库的代币尽调与沟通平台 · Monad Testnet

每一份回答、每一次披露、每一次风险变化都有时间戳、版本号和链上哈希。

## 它是什么

TokenTruth 是一个**双边平台**：

- **投资者侧**：把白皮书、代币经济、解锁规则、市场数据、新闻、社区讨论整理为 AI 知识库，自然语言提问即可获得带来源、带时间、带可信度、带风险提示的回答；
- **项目方侧**：把公司资料、产品文件统一为可维护的 AI 知识库，辅助生成介绍材料、视频脚本、新闻稿、FAQ，直接回答投资者问题；
- **执行侧**：在用户授权并符合相关要求的前提下，辅助制定投资计划、跟踪价格、对接平台执行；
- **可信层**：每次研究报告、项目方披露、风险状态变化都生成哈希并锚定到 Monad Testnet。

## 4 大功能模块

| 模块 | 作用 |
|---|---|
| 💬 **问得明白** | AI 知识库 + 自然语言问答（投资者） |
| 📊 **帮我分析** | 基本面 + 市场 + 社区 + 风险综合分析 |
| 📈 **跟踪执行** | 关注列表 + 投资计划 + 用户授权后对接平台 |
| 📢 **项目方后台** | 资料版本管理 + 6 类内容模板自动生成 + 投资者问答 |

## AI 引擎：DeepSeek 接入

`/chat` 页面默认调用本地关键词引擎，**配置 DeepSeek API key 后自动切换为 LLM 模式**：

```powershell
# 编辑 .env（不是 .env.example）
notepad .env

# 加入：
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=20
```

LLM 模式工作流：

1. 检索项目资料中 top-5 上下文（按可信度 + 关键词打分）
2. 拼装 system prompt（"只基于项目资料回答，每条结论带 [N] 引用"）
3. DeepSeek 返回严格 JSON：`{conclusion, reasoning, citationIndexes, risks, confidence, followups}`
4. 把 `[N]` 索引映射回原始引用，6 字段结构化返回
5. **失败兜底**：网络/限流时自动降级到本地模板引擎

## 6 种链上存证场景

每次存证都写到 Monad：

1. 项目方披露新版本（PROJECT_DISCLOSURE）
2. 投资者研究报告（RESEARCH_REPORT）
3. 风险状态变更（RISK_STATUS_CHANGE）
4. 投资者问答（INVESTOR_QA，可选）
5. 项目方内容发布（CONTENT_PUBLISH）
6. 用户授权执行（EXECUTION_CONSENT）

## 快速开始

> **3 分钟跑通**：Node.js 18+、Python 3.10+。无需 GPU，无需钱包，无需私钥（默认 mock 链）。

```powershell
cd D:\webProject\HacksonProjectList\TokenTruth
npm install          # 创建 .venv 并安装最小依赖
npm run dev          # 启动 http://127.0.0.1:4000
```

打开浏览器：

| 路径 | 作用 |
|---|---|
| `/` | 项目目录 + 4 大功能入口 |
| `/chat?projectId=demo-mon` | 投资者问答：靠什么赚钱？代币有什么权利？ |
| `/analyze?projectId=demo-mon` | 基本面 + 市场 + 社区 + 风险综合分析 |
| `/track` | 关注列表 + 投资计划 + 授权执行 |
| `/company?projectId=demo-mon` | 项目方后台：6 类内容模板自动生成 |
| `/edit_doc?projectId=demo-mon&docType=whitepaper` | 编辑资料 → 新版本上链 |
| `/proof?hash=0x...` | 链上存证查询 + Monad Explorer 跳转 |

## 验证与测试

```powershell
npm run test         # 单元测试（问答 / 分析 / 公司侧 / 链 / 路由 / 存储）
npm run demo         # 端到端 smoke：8 页面 + 5 个核心问答 + 上链 + 资料更新
npm run check        # 编译检查 + 单元测试
```

`npm run demo` 输出 `status: passed`，含 5 类核心问答 + 资料更新 + diff + 链上存证。

## 部署到 Monad Testnet（真链）

```powershell
$env:PRIVATE_KEY = "0x..."
$env:MONAD_RPC = "https://testnet-rpc.monad.xyz"
$env:MONAD_CHAIN_ID = "10143"
$env:TOKENTRUTH_CHAIN_MODE = "live"
pip install py-solc-x web3 eth-account requests
npm run chain:deploy
$env:DISCLOSURE_REGISTRY_ADDRESS = "0x..."
npm run dev
```

## 目录结构

```text
TokenTruth/
├── contracts/DisclosureRegistry.sol    # Solidity 0.8.20 链上存证合约
├── scripts/
│   ├── deploy.py                       # 部署到 Monad Testnet
│   └── seed_projects.py                # 灌入 demo 项目 + 触发链上存证
├── src/
│   ├── projects/{store,seed_data}.py   # 项目/资料/版本 SQLite
│   ├── knowledge/
│   │   ├── qa_engine.py                # 自然语言问答引擎
│   │   └── analyzer.py                 # 基本面+市场+社区分析
│   ├── tracking/watchlist.py           # 关注+投资计划+授权执行
│   ├── company/{content_gen,version_diff}.py
│   ├── risk/status_engine.py          # 风险状态管理
│   ├── chain/registry.py               # Web3.py + mock
│   ├── i18n/dicts/{zh-CN,en-US}.json   # 中英双语
│   └── config_loader.py
├── templates/                          # 8 个页面
│   ├── {base,home,project,chat,analyze,track,company,edit_doc,proof}.html
├── static/                             # design-system.css + 4 个页面 JS
├── tools/{harness.mjs,dev_server.py,smoke_test.py,harness_support.py}
├── tests/harness/                      # 5 套单元测试
├── web_app.py                          # Flask 主入口
├── config/default.json                 # QA 意图 + 风险阈值
├── data/demo/seed_projects.json        # demo 项目数据
└── docs/                               # PRD + 支撑文档
```

## 边界与安全

- ❌ 不做人脸识别 / 身份追踪；工人用脱敏 `workerHash`（在另一个项目 SafeLine 中）
- ❌ 不在低置信度 / 遮挡时伪造"违规"
- ❌ 不替代 EHS 整改决定
- ❌ 仅 Monad Testnet，不进生产
- ❌ **不自动买币/卖币**，所有执行需用户明确授权
- ❌ **不托管资金**，不绕过 KYC
- ❌ **不提供投资建议**（"该买/该卖"指令）

## 文档导航

- [PRD](docs/PRD.md)
- [架构详解](docs/architecture.md)
- [任务清单](docs/tasks.md)
- [验收标准](docs/acceptance.md)
- [链上合约说明](docs/chain.md)

## License

MIT
