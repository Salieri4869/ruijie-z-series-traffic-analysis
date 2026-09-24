# Z 系列防火墙管理系统

通过 Web 界面操控锐捷 Z 系列防火墙：登录、查询会话信息、按应用下发策略，并支持在指定网卡上抓包、做 JA3/JA4 指纹分析。

---

## 功能概览

| 模块 | 能力 |
| --- | --- |
| 防火墙对接 | RSA 加密登录、Cookie 维持、应用树/会话信息查询、策略下发 |
| 抓包 | 基于 Scapy 的异步抓包，过滤条件可配置 |
| 流量分析 | 抓包产物走 pyshark 提取 JA3/JA4 指纹，支持按 IP 过滤去重 |
| 前端 | 单页界面，含登录、应用联想下拉、抓包启停、实时结果推送 |
| 配置 | 账号密码等敏感项走 `.env`，由 pydantic-settings 统一读取 |

---

## 目录结构

```
.
├── main.py              # 应用入口、生命周期（login / logout）
├── config.py            # 配置模型 + 单例
├── firewall.py          # 防火墙 API 封装（FireWallAPI）
├── endpoints.py         # 接口路径构造
├── models.py            # Pydantic / dataclass 请求模型
├── route.py             # FastAPI 路由
├── utils/
│   ├── sniffer.py       # Scapy 异步抓包
│   ├── pysharkja.py     # JA3/JA4 指纹解析
│   └── connector.py     # WebSocket 连接管理
├── templates/
│   └── firewall.html    # 前端页面
├── static/              # CSS / JS
├── .env.example         # 配置模板（提交到 Git）
├── .env                 # 真实配置（不提交）
├── requirements.txt
└── README.md
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> 需要系统层依赖：libpcap（抓包）与 Wireshark/tshark（pyshark 解析）。

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入防火墙地址、账号、密码
```

### 3. 启动

```bash
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000`。

---

## 配置说明

所有敏感配置与可调参数集中在 `.env`，由 `config.py` 中的 `Settings` 读取并做类型校验。

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `FIREWALL_HOST` | 防火墙地址（含协议与端口） | `https://192.168.66.1` |
| `FIREWALL_USERNAME` | 登录账号 | `admin` |
| `FIREWALL_PASSWORD` | 登录密码 | （空） |
| `RSA_ENCRYPT_DISABLE` | 是否关闭传输层加密（开发环境用） | `true` |
| `SNIFFER_INTERFACE` | 抓包网卡名，留空则回落 `scapy.config.conf.iface` | （空） |
| `SNIFFER_FILTER` | BPF 抓包过滤表达式 | `not arp and host ...` |
| `PAGE_TITLE` | 前端页面标题 | `Z系列防火墙管理系统` |
| `DEBUG` | 调试开关 | `false` |

优先级：`系统环境变量 > .env > 代码默认值`，因此容器部署时只需设环境变量，无需挂载 `.env`。

---

## 架构要点

### 防火墙单例

`firewall.py` 末尾保留一个模块级全局实例：

```python
firewall = FireWallAPI()
```

`route.py` 与 `main.py` 都从 `firewall` 模块 import 它。`FireWallAPI.__init__` 自行读取配置，调用方无需传参。生命周期由 `main.py` 的 `lifespan` 控制：启动时登录并拉取应用树，关闭时登出。

> ⚠️ 该实例在 import 时已创建，但此时尚未登录（Cookie 在 `lifespan` 里才写入），路由处理前必须保证 lifespan 已跑完——FastAPI 保证这一点。

### 网卡选择优先级

`config.py` 中：

```
.env 的 SNIFFER_INTERFACE（非空）  ▶  优先
        ↓
scapy.config.conf.iface             ▶  自动回落
```

### 抓包链路

`Sniffer` 用 `AsyncSniffer` 抓包，每个包通过 `packet_callback` 丢进 `asyncio.Queue`；`/ws` 端点消费队列并广播给前端。停止抓包后可按四种模式处理产物：原始保存、按 IP 过滤、JA 指纹分析、或两者叠加。

### 登录过期处理

前端在 `getSessionInfo` 里检测 `data.msg === '登录状态已过期'`，自动触发重新登录。后端 `get_session_info` 在 code 非 20000 时直接返回该提示文案。

---

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/login` | 触发登录并刷新 Cookie |
| GET | `/tree` | 获取应用树并构建索引 |
| GET | `/get_session_info` | 查询会话（参数见 `SessionInfo`） |
| POST | `/add_policy/action` | 下发策略，body 为 `PolicyAction` |
| POST | `/capture/start` | 开始抓包 |
| POST | `/capture/stop` | 停止抓包，body 为 `StopCaptureReq` |
| WS | `/ws` | 实时抓包数据推送 |

抓包请求体示例：

```json
{
  "output_file": "Capture Session",
  "mode": "ja_ip_filter"
}
```

`mode` 取值：`none` / `ja` / `ip_filter` / `ja_ip_filter`。

---

## 开发说明

- 新增接口路径：在 `endpoints.py` 的 `APIEndpoints` 加 `@property`，不要在业务代码里拼接 URL。
- 新增配置项：在 `Settings` 中声明字段，`.env.example` 同步加一行。
- `route.py` 中的 `app_ip`（`AppIP`）、`executor`（`ProcessPoolExecutor`）、`queue` 均为模块级全局对象，方便多请求共享；如需按用户隔离状态需重构。
- `firewall.py` 末尾的 `if __name__ == '__main__'` 是旧式同步调试代码，已与异步改造后的 `login()` 不兼容，建议删除。

---

## 安全提示

- `.env` 必须加入 `.gitignore`，不得提交真实账号密码。
- 生产环境 `CORS` 的 `allow_origins` 应收窄到具体域名，`verify=False` 的 httpx 调用应改为校验证书。
- 抓包能力权限敏感，上线前需加身份认证与鉴权。

---

## 依赖

详见 [requirements.txt](./requirements.txt)。核心库：

- `fastapi` / `uvicorn` — Web 框架与服务器
- `pydantic` / `pydantic-settings` — 数据校验与配置管理
- `httpx` — 异步 HTTP 客户端
- `scapy` — 抓包
- `pyshark` — pcap 解析与 JA 指纹提取
- `pycryptodome` — RSA 加密
