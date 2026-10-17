# Monad SafeLine · 需求文档（PRD）

> **基于姿态识别的高危流水线工人动作风险监测与链上事故存证**
> Monad Blitz V3 @上海 参赛项目
> 版本：v1.0 · 日期：2026-10-17

---

## 0. 一句话定位

**Monad SafeLine = 流水线上的"看得见的 EHS 数字员"**：当工人做出弯腰搬重物、跨越安全围栏、长时间单侧扭转、违规攀爬、靠近运转机械等高风险动作时，**摄像头在毫秒级内识别动作、规则引擎在毫秒级内判定风险、风险事件即时写入 Monad Testnet** —— 让"风险瞬间"成为"链上证据"，让 EHS 从纸面巡检升级为秒级可审计的链上存证。

**核心金句**：**动作发生的瞬间，证据已经在链上。**

---

## 1. 业务背景

### 1.1 行业现状

制造业、仓储物流、建筑工地、化工厂是高危行业。流水线工人每天执行 **搬运、攀爬、跨越、扭转、重复高举、靠近机械** 等动作，是工伤和职业病的主要诱因：

- **腰部过载**：弯腰搬重物姿势错误 → 腰肌劳损、腰椎间盘突出；
- **机械伤害**：进入机械危险半径 → 挤压、剪切、绞入；
- **高处坠落**：违规攀爬非设计工位 → 跌落伤害；
- **累积损伤**：长时间单侧扭转 → 单侧肌肉/关节累积劳损；
- **违规穿越**：越过安全围栏 → 误入危险作业区。

### 1.2 现有 EHS 管理的三大痛点

| 痛点 | 业务后果 |
|---|---|
| **事故难以还原** | 责任划分难、整改缺乏依据；工伤认定纠纷长期高发 |
| **巡检严重滞后** | EHS 经理无法秒级发现风险，等发现时往往已发生事故 |
| **证据不可信** | 纸质记录易篡改、监管/保险/法务调证效率低，企业 ESG 报告缺乏可信数据 |

### 1.3 监管与商业驱动

- **《工伤保险条例》** 与 **《生产安全事故应急预案管理办法》** 要求事故证据可追溯；
- **ISO 45001** 职业健康安全管理体系要求风险事件留痕；
- 企业 **ESG 报告** 中"S"（社会）需要可信的安全数据；
- **保险公司** 对"可验证的安全数据"给予费率优惠（参考 IoT 安全设备的车险 UBI 模式）；
- **工人与企业之间的工伤认定纠纷** 长期高发于制造业。

### 1.4 为什么选 Monad 区块链

流水线作业具有**天然的事件并行性**：

- 单工位 1 秒内可能触发多次风险事件（弯腰 + 扭转 + 靠近机械）；
- 整厂数百工位同时监测时，事件流之间**互不依赖**；
- 这正是 Monad **并行 EVM + 10,000 TPS + 亚秒级最终性** 的最佳发挥场景。

> **SafeLine 选 Monad 而非传统串行 EVM，是把"姿态事件的高并发"和"区块链的并行执行"做技术-业务的强匹配。**

---

## 2. 目标用户

| 用户 | 角色 | 核心诉求 |
|---|---|---|
| **EHS 经理** | 工厂 EHS 部门 | 秒级看到风险事件、生成可审计的链上存证 |
| **生产线主管** | 车间主任 | 实时收到本工位风险告警、推动整改闭环 |
| **企业管理者** | 厂长 / 集团 EHS | 跨工位/跨工厂风险看板、趋势分析、整改追踪 |
| **EHS 监管/审计** | 第三方监管、行业协会 | 调取链上存证、验证事件真实性与时间戳 |
| **保险 / 法务** | 保险公司、企业法务 | 事故定责、证据核验、保险定价 |
| **流水线工人** | 一线员工 | 收到即时语音/灯光提示，降低工伤风险 |

---

## 3. 核心价值主张

| 价值 | 实现方式 |
|---|---|
| ⚡ **实时识别** | 摄像头每帧 30 FPS，姿态估计 < 50ms，规则判定 < 5ms |
| 🔗 **实时上链** | 风险事件秒级写入 Monad Testnet，不可篡改、可追溯 |
| 📊 **可视化** | 现场大屏 + EHS 仪表盘，事件流、风险热区、整改闭环 |
| 🔍 **可审计** | 监管/保险/法务通过 `eventHash` + `txHash` 直接验证证据 |
| 🛡️ **不替代人** | 最终整改由授权人员决定；技术失败时降级到 `inconclusive`，绝不伪造"违规" |
| 🔐 **隐私优先** | 工人使用 `workerHash` 脱敏，链上不存原始 ID 或人脸 |

---

## 4. 范围与边界

### 4.1 范围内（MVP）

- 单工位 / 多工位摄像头实时姿态识别；
- 5 类高危动作规则引擎（弯腰搬重物、跨越围栏、单侧扭转、攀爬异常、靠近机械）；
- 风险事件实时上链（Monad Testnet `RiskRegistry` 合约）；
- 现场大屏 / EHS 仪表盘 / 存证查询三个 Web 页面；
- 完整 API 服务：会话、事件、上链查询；
- 链上存证：事件 hash、时间戳、关键元数据；
- 失败兜底：链断网时本地队列 + 重试 + UI 降级。

### 4.2 范围外（明确不做）

- ❌ 不做医疗诊断、伤病预测、康复处方；
- ❌ 不做人脸识别 / 身份追踪 / 行为画像；
- ❌ 不替代 EHS 经理的整改决定；
- ❌ 不在低置信度 / 遮挡时伪造"违规"，必须返回 `inconclusive`；
- ❌ 不做完整身份认证、SSO、细粒度权限（黑客松 MVP 范围）；
- ❌ 不在生产环境直接使用（仅 Monad Testnet 演示）。

---

## 5. 核心功能

### 5.1 风险动作目录（MVP 5 类）

| 编号 | 风险动作 | 关键判定 | 严重级别 | 业务含义 |
|---|---|---|---|---|
| **R1** | 弯腰搬重物过深 | 髋关节角度 < 阈值 + 持续 ≥ 1.5s | HIGH | 腰部过载，诱发腰肌劳损 |
| **R2** | 跨越安全围栏 | 足部关键点越过虚拟围栏边界 | CRITICAL | 进入危险作业区 |
| **R3** | 长时间单侧扭转 | 躯干-骨盆相对扭转角 > 阈值 + ≥ 5s | MEDIUM | 单侧肌肉累积损伤 |
| **R4** | 违规攀爬 | 双手+双脚同时离地 + 高度突变 | HIGH | 违规攀爬非设计工位 |
| **R5** | 靠近运转机械 | 关键点进入机械危险半径 + 机械 ON 信号 | CRITICAL | 机械伤害风险 |

### 5.2 实时识别与去抖

| 阶段 | 指标 |
|---|---|
| 帧率 | 30 FPS |
| 姿态估计延迟 | < 50 ms（CPU ONNX 推理） |
| 规则判定延迟 | < 5 ms |
| 事件触发延迟 | 端到端 < 200 ms |
| 去抖 | 连续 N 帧满足才触发事件（避免单帧抖动） |
| 冷却 | 同一类事件冷却 T 秒（避免重复告警） |
| 现场反馈 | 声光 + Web Speech 语音提示 |

### 5.3 链上存证

- **触发**：风险事件去抖通过 → 构造事件 payload → 计算 `eventHash`（Keccak-256）→ 写入 Monad Testnet；
- **存证内容**：
  - 链上：`eventHash`、`timestamp`、`tenantId`、`stationId`、`workerHash`、`riskType`、`severity`；
  - 链下索引：`eventId`（UUID）、`txHash`、`blockNumber`、`keypoints` 摘要、`modelVersion`、`ruleVersion`；
- **链上不可篡改**：任何后续调取都基于 `eventHash` 与 Tx 验证；
- **批量优化**：低风险事件可批量提交（Monad 高 TPS 用起来）；
- **失败兜底**：链上写入失败 → 本地持久化 + 重试队列 + UI 降级为 `pending`，不丢数据。

### 5.4 仪表盘与可视化

- **`/station` 现场大屏**：当前工位实时状态、最近 1 小时事件、风险等级徽标；
- **`/dashboard` EHS 仪表盘**：多工位/多工厂事件流、风险热区、整改闭环表；
- **`/proof` 存证查询**：输入 `eventHash` 展示链上记录 + Monad Explorer 链接。

### 5.5 数据安全与脱敏

- 工人使用 `workerHash = keccak256(tenantId + workerId)` 脱敏，链上不存原始 ID；
- 实时帧默认不长期持久化；
- 证据视频片段需明确告知 + 留存策略 + 到期删除；
- Demo 一律使用虚构数据。

---

## 6. 技术架构

### 6.1 整体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│  现场层                                                            │
│  摄像头 · 麦克风 · 工业 PC / 边缘盒子 · 现场大屏                     │
│  WebRTC / WebSocket 推流到服务端                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  实时应用层（Flask Web）                                            │
│  /station · /dashboard · /proof                                    │
│  /api/session/* · /api/events/* · /api/proof/*                    │
│  摄像头帧接收 · 姿态估计推理 · 规则引擎 · 风险事件构造 · 链上写入       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  模型层                                                            │
│  姿态估计：RTMPose 17 关键点（ONNX Runtime）                         │
│  动作分类：ST-GCN（11 类微调）                                       │
│  几何规则引擎：5 类高危动作                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  链上存证层（Monad Testnet）                                          │
│  风险事件 Service → Web3.py → RiskRegistry 合约                     │
│  payload → eventHash → 写链 → txHash 回填 → UI 展示                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 技术选型

| 模块 | 选型 | 说明 |
|---|---|---|
| 姿态估计 | RTMPose ONNX + ONNX Runtime | 17 关键点，本地推理，CPU/GPU 双 Provider |
| 动作分类 | PyTorch ST-GCN | 11 类动作，48 帧窗口 |
| 规则引擎 | NumPy + 几何规则 | 角度/距离/阶段/冷却/计数，5 类风险动作 |
| Web 后端 | Flask 3 | 路由、API、模板渲染 |
| Web 前端 | Jinja + Tailwind CDN + Font Awesome | 单文件 HTML 即可，CDN 资源 |
| 链交互 | Web3.py | 适配 Monad Testnet（EVM 兼容） |
| 智能合约 | Solidity 0.8.x | `RiskRegistry.sol`，单合约，事件日志 + 状态映射 |
| 本地存储 | JSON + SQLite | 事件队列、待上链缓存、链下索引 |
| 链网络 | Monad Testnet | 黑客松部署目标 |
| Harness | Node package scripts + Python unittest | 一键安装 / 启动 / 测试 / smoke |
| 部署 | Monad Testnet（演示） | 备用 Hardhat 本地节点 |

### 6.3 模块职责

| 模块 | 职责 |
|---|---|
| **Web 前端** | 摄像头采集、视频流、关键点可视化、风险事件展示、链上存证查询 |
| **Flask 路由** | 页面渲染、API 转发、链下存储、链上写入编排 |
| **姿态估计** | 单帧关键点提取（17 个 COCO 关键点） |
| **动作分类** | 48 帧窗口的 11 类动作分类（辅助规则引擎） |
| **规则引擎** | 5 类风险动作的实时判定、去抖、冷却、计数 |
| **链上服务** | 事件 hash 构造、链上写入、txHash 回填、链上查询 |
| **智能合约** | 事件存证存储、防重复、公开可验证 |
| **本地存储** | 事件队列、待上链缓存、链下索引、Demo 种子数据 |

---

## 7. 数据模型

### 7.1 链下事件模型（主存储 + 上链摘要）

```json
{
  "eventId": "evt-2026-10-17-00001",
  "tenantId": "factory-A",
  "stationId": "station-line3-04",
  "workerHash": "0x9f2c...3a",
  "riskType": "R1",
  "severity": "HIGH",
  "timestamp": 1760700000,
  "keypoints": {
    "frame_count": 47,
    "hip_angle_avg": 38.5,
    "hip_angle_min": 32.1,
    "duration_ms": 1620
  },
  "ruleVersion": "SAFE_LINE_V1",
  "modelVersion": "rtmpose+stgcn@2026-10-17",
  "eventHash": "0xabcd...1234",
  "txHash": "0xdef0...5678",
  "blockNumber": 12345678,
  "chainStatus": "confirmed | pending | failed"
}
```

### 7.2 链上事件（Solidity 事件）

```solidity
event RiskEventRecorded(
    bytes32 indexed eventHash,
    string  eventId,
    uint256 timestamp,
    string  tenantId,
    string  stationId,
    bytes32 workerHash,
    uint8   riskType,     // 1..5
    uint8   severity,     // 1..3
    uint256 blockNumber
);
```

### 7.3 智能合约 `RiskRegistry.sol` 接口

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract RiskRegistry {
    struct RiskRecord {
        bytes32 eventHash;
        string  eventId;
        uint256 timestamp;
        string  tenantId;
        string  stationId;
        bytes32 workerHash;
        uint8   riskType;
        uint8   severity;
        address recorder;
    }

    mapping(bytes32 => RiskRecord) public records;
    mapping(string  => bytes32) public eventIdToHash; // 防重复

    event RiskEventRecorded(
        bytes32 indexed eventHash,
        string  eventId,
        uint256 timestamp,
        string  tenantId,
        string  stationId,
        bytes32 workerHash,
        uint8   riskType,
        uint8   severity
    );

    function recordRisk(
        bytes32 eventHash,
        string calldata eventId,
        uint256 timestamp,
        string calldata tenantId,
        string calldata stationId,
        bytes32 workerHash,
        uint8 riskType,
        uint8 severity
    ) external returns (bool);

    function verify(bytes32 eventHash)
        external
        view
        returns (bool exists, RiskRecord memory record);

    function totalEvents() external view returns (uint256);
}
```

---

## 8. API 设计

| 端点 | 方法 | 作用 | 输入 | 输出 |
|---|---|---|---|---|
| `/api/session/start` | POST | 创建监测会话 | `{stationId, workerHash, ruleVersion}` | `{sessionId, modelVersion, ruleVersion}` |
| `/api/session/frame` | POST | 提交一帧 | `{sessionId, keypoints, timestamp}` | `{phase, repCount, errors[], pendingEvents[]}` |
| `/api/session/stop` | POST | 结束会话 | `{sessionId}` | `{summary, totalEvents}` |
| `/api/events` | GET | 查询事件列表 | `?stationId=&riskType=&from=&to=` | `{events: [...]}` |
| `/api/events/<id>` | GET | 查询单个事件 | path | `{event, onChain}` |
| `/api/proof/<eventHash>` | GET | 链上存证查询 | path | `{eventHash, txHash, blockNumber, chainStatus, explorerUrl}` |
| `/api/chain/status` | GET | 链状态 | — | `{network, latestBlock, pendingCount, contractAddress}` |
| `/api/demo/seed` | POST | 注入脱敏 Demo 事件 | `{count}` | `{events: [...]}` |
| `/` | GET | 首页 | — | HTML |
| `/station` | GET | 现场大屏 | `?stationId=` | HTML |
| `/dashboard` | GET | EHS 仪表盘 | — | HTML |
| `/proof` | GET | 存证查询 | `?eventHash=` | HTML |

---

## 9. UI 设计

### 9.1 风格基线

- **深色工业风** + **风险色板**（绿/黄/橙/红）；
- 顶部状态条：网络状态、当前工位、模型版本、规则版本；
- 主区：实时视频流 + 关键点骨架 + 风险事件流；
- 底部：链上状态 + 最近 5 笔 `txHash`（可点击 Monad Explorer）；
- 字体：系统字体 + JetBrains Mono（展示 hash）；
- 图标：Font Awesome 4.7 CDN；
- 框架：Tailwind CDN（与 luma 风格无关，独立选择）。

### 9.2 关键页面

| 页面 | 作用 |
|---|---|
| `/` 首页 | 项目介绍 + Demo 入口 + 链上存证总览 |
| `/station` 现场大屏 | 大字号当前状态、最近事件、链上确认状态 |
| `/dashboard` 仪表盘 | 多工位卡片 + 风险热区 + 趋势图 |
| `/proof` 存证查询 | 输入 `eventHash` 展示链上证据 + Explorer 跳转 |

### 9.3 配色（深色工业风）

| 用途 | 颜色 |
|---|---|
| 背景 | `#0b0f14`（深空蓝黑） |
| 告警 | `#ff5722`（告警橙） |
| 严重 | `#d32f2f`（严重红） |
| 安全 | `#10b981`（安全绿） |
| 警告 | `#f59e0b`（警告黄） |
| 主文本 | `#e5e7eb` |
| 辅文本 | `#9ca3af` |
| Monad 标识 | `#7c3aed`（紫，用于链上标识） |

---

## 10. 48 小时 MVP 计划

### 10.1 时间线（按 Monad Blitz V3 8:30–18:30 倒推）

| 时段 | 任务 | 产出 |
|---|---|---|
| **0–2h** | 需求冻结、目录搭建、依赖锁定 | 仓库结构、`package.json`、`requirements.txt` |
| **2–4h** | 智能合约 `RiskRegistry.sol` 编写 + 部署到 Monad Testnet | 合约地址 + 部署脚本 |
| **4–6h** | 后端：链交互层（Web3.py）、事件队列、上链服务 | `chain/registry.py` |
| **6–9h** | 姿态估计模块 + 5 类风险规则引擎 | `src/pose/`、`src/rules/safe_line.py` |
| **9–12h** | Flask 路由 + API 实现 + 链上存证查询 | `/api/*` 全打通 |
| **12–15h** | 前端：4 个页面（Tailwind 单文件） | `/`、`/station`、`/dashboard`、`/proof` |
| **15–17h** | Demo 种子数据 + 端到端 smoke | `npm run demo` 通过 |
| **17–18h** | 录屏脚本 + 路演 PPT | 5 分钟 Demo、3 分钟路演 |
| **18h 截止** | 提交 | README + Demo 视频 + 合约地址 |

### 10.2 交付物清单

- [ ] `docs/PRD.md`（本文档）
- [ ] `docs/architecture.md`（技术架构详解）
- [ ] `contracts/RiskRegistry.sol`（Solidity 合约）
- [ ] `scripts/deploy.py`（Monad Testnet 部署脚本）
- [ ] `src/pose/`（姿态估计）
- [ ] `src/rules/safe_line.py`（5 类风险规则）
- [ ] `chain/registry.py`（链交互服务）
- [ ] `web_app.py`（Flask 路由）
- [ ] `templates/`（4 个页面）
- [ ] `tools/harness.mjs` + `package.json`（npm scripts）
- [ ] `data/demo/safe_line_seed.json`（脱敏 Demo 数据）
- [ ] `README.md`（项目说明 + 跑通步骤）
- [ ] Demo 视频（≤ 5 分钟）
- [ ] 路演 PPT（≤ 8 页）
- [ ] 链上合约地址 + Explorer 链接

---

## 11. 验收标准（Demo 口径）

### 11.1 必须通过

- [ ] `npm run install` 在 Windows PowerShell 上一键安装；
- [ ] `npm run dev` 启动 4000 端口无报错；
- [ ] 智能合约部署到 Monad Testnet 且 `verify()` 可查；
- [ ] 提交一帧后，规则引擎在 < 100ms 内返回 `pendingEvents`；
- [ ] 风险事件 5 秒内在 Monad Explorer 可见（手动测试）；
- [ ] `/proof?eventHash=0x...` 能查到对应链上记录；
- [ ] 4 个页面在浏览器 1080p 下无横向滚动；
- [ ] `npm run demo` 输出 `status: passed`；
- [ ] README 包含 1 分钟跑通命令。

### 11.2 加分项

- [ ] 多工位并发事件并行上链（演示 Monad 并行 EVM 优势）；
- [ ] 链上存证总览面板（总事件数、唯一事件数、最后块高）；
- [ ] 风险热区图（dataviz 风格）；
- [ ] 失败兜底：链断网时本地队列 + 重试 + 降级提示；
- [ ] 录屏显示 5 类风险动作 + 链上确认全过程。

---

## 12. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 姿态识别受遮挡/光线影响 | 低置信度返回 `inconclusive`，不伪造违规 |
| 链上写入偶发失败 | 本地队列 + 指数退避重试 + UI 降级 |
| 工人隐私担忧 | 仅存 `workerHash`，不存原图与人脸 |
| 监管合规 | 演示用 Monad Testnet + 虚构数据，明确边界 |
| 工业场景数据稀缺 | 公开数据集 + 确定性 Demo 输入，规则版本化 |
| 误报/漏报争议 | 规则版本号、模型版本号、`eventHash` 全留痕，可解释 |
| Monad Testnet 不可用 | 备用本地 Hardhat 节点 + Mock 合约，保留可演示版本 |

---

## 13. Monad 技术亮点对应

| Monad 特性 | SafeLine 用法 | Demo 演示 |
|---|---|---|
| 并行 EVM | 多工位事件并行上链 | 同时触发 5 个工位风险事件，看区块内多笔交易并发 |
| 10,000 TPS | 高频姿态事件写入 | 1 分钟内写入 100+ 事件，展示 TPS 优势 |
| 亚秒级最终性 | 风险事件秒级确认 | 事件触发 → Explorer 确认 < 3s |
| EVM 兼容 | Solidity 合约 | 复用 OpenZeppelin/标准 EVM 工具链 |
| 链下计算 + 链上存证 | 姿态/规则在链下，hash 上链 | 计算与存证职责清晰，符合"少上链"原则 |

---

## 14. 商业价值（赛后路线）

| 阶段 | 价值 |
|---|---|
| 试点 | 单工厂、单工位、1 类风险动作并行运行，与人工 EHS 比对 |
| 扩展 | 多工位、多工厂、多风险动作；接入企业 EHS 系统 |
| 增值 | 保险费率优惠、ESG 报告自动化、监管存证服务 |
| 生态 | 作为 EHS 数据上链标准，向其他安全设备厂商开放 |

---

## 15. 文档导航

- [架构详解](architecture.md)
- [任务清单](tasks.md)
- [验收标准](acceptance.md)
- [链上合约说明](chain.md)
- [风险规则说明](rules.md)

---

> **最终叙事**：SafeLine 把流水线上的"风险瞬间"变成"链上证据"，让 EHS 从纸面巡检升级为秒级可审计的链上存证。**动作发生的瞬间，证据已经在链上。** 🛡️
