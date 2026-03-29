# 厂区车辆进出管理系统 · 设计规格

**日期：** 2026-03-29
**状态：** 已确认
**范围：** MVP — 单厂区车辆进出记录，架构支持多厂区扩展

---

## 1. 产品定位

帮助有厂区的公司实现车辆进出的透明化记录与管理。物流公司根据外部安排自行调度车辆，本系统不介入调度，只负责：

- 摄像头自动识别进出车牌，生成进出记录
- 管理人员实时查看在厂车辆状态
- 提供可查询、可导出的历史记录
- 异常情况（长时间未出场、识别需人工审核）发出报警

后续可扩展：多厂区、调度任务、叉车管理等。

---

## 2. 用户角色

| 角色 | 权限范围 |
|------|----------|
| 集团管理员 | 查看所有厂区数据，管理厂区和账号 |
| 厂区管理员 | 管理本厂区数据、账号、摄像头配置、报警规则 |
| 操作员 | 查看记录、人工审核识别结果、处理报警 |

---

## 3. 技术架构

**方案：前后端分离 + 独立 AI 识别服务**

```
用户层
  ├── Web 管理后台（React + Vite）
  └── 摄像头终端（推流至 AI 识别服务）

API 层
  └── FastAPI 主服务（REST API + WebSocket 实时推送）

服务层
  ├── AI 识别服务（Python + OpenCV，独立进程）
  └── 通知服务（WebSocket 推送 + 邮件/短信报警）

数据层
  ├── PostgreSQL（主数据库，所有表含 factory_id）
  ├── Redis（实时车辆状态缓存 + 消息队列）
  └── MinIO / S3（抓拍图片存储）
```

**关键决策：**
- AI 识别服务独立部署，主服务通过 HTTP 调用，互不影响
- 所有业务表含 `factory_id`，为多厂区扩展预留，查询时自动过滤
- Redis 缓存当前在厂车辆状态，WebSocket 实时推送看板数据
- 低置信度识别结果标记为待人工审核，不自动入库为最终记录

---

## 4. 数据模型

### factories
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | varchar | 厂区名称 |
| address | text | 地址 |
| timezone | varchar | 时区 |
| status | enum | active / inactive |
| created_at | timestamp | 创建时间 |

### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| factory_id | UUID FK | 所属厂区（集团管理员为 null） |
| name | varchar | 姓名 |
| phone | varchar | 手机号（登录账号） |
| password_hash | varchar | 密码哈希 |
| role | enum | group_admin / factory_manager / operator |
| is_active | bool | 是否启用 |
| last_login | timestamp | 最后登录时间 |

### vehicles
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| factory_id | UUID FK | 所属厂区 |
| plate_number | varchar | 车牌号（唯一索引） |
| vehicle_type | varchar | 货车/集装箱车/其他 |
| company | varchar | 所属物流公司 |
| contact_name | varchar | 联系人 |
| contact_phone | varchar | 联系电话 |
| status | enum | in_factory / out / unknown |
| last_seen_at | timestamp | 最后记录时间 |
| note | text | 备注 |

### gate_events（核心表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| factory_id | UUID FK | 所属厂区 |
| gate_id | UUID FK | 出入口 |
| vehicle_id | UUID FK | 车辆（人工确认后关联） |
| plate_number | varchar | 识别车牌（原始结果） |
| direction | enum | entry / exit |
| captured_at | timestamp | 抓拍时间 |
| image_url | varchar | 抓拍图片路径 |
| confidence_score | float | AI识别置信度（0-1） |
| review_status | enum | auto_confirmed / pending_review / manually_confirmed / rejected |
| reviewed_by | UUID FK | 审核人 |
| reviewed_at | timestamp | 审核时间 |
| is_manual | bool | 是否人工录入 |

### locations（出入口配置）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| factory_id | UUID FK | 所属厂区 |
| name | varchar | 出入口名称（如"北门"） |
| type | enum | gate / checkpoint |
| camera_ip | varchar | 摄像头地址 |
| is_active | bool | 是否启用 |

### alerts
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| factory_id | UUID FK | 所属厂区 |
| vehicle_id | UUID FK | 关联车辆 |
| type | enum | long_stay / pending_review |
| message | text | 报警内容 |
| severity | enum | info / warning / critical |
| status | enum | active / resolved |
| created_at | timestamp | 触发时间 |
| resolved_by | UUID FK | 处理人 |
| resolved_at | timestamp | 处理时间 |

---

## 5. 核心功能模块

### 5.1 实时看板
- 统计卡片：在厂车辆数 / 今日入场次数 / 今日出场次数 / 待审核记录数
- 今日出入折线图（按小时）
- 最近出入记录列表（WebSocket 实时刷新）
- 活跃报警横幅（点击跳转处理）

### 5.2 出入记录
- 列表：时间、车牌、方向、出入口、抓拍图片缩略图、识别置信度、审核状态
- 待审核记录标红，操作员可修正车牌、确认或拒绝
- 筛选：日期范围 / 车牌模糊搜索 / 方向 / 出入口 / 审核状态
- 导出 Excel

### 5.3 车辆管理
- 车辆档案列表：车牌、公司、当前状态（在厂/离厂）、最后记录时间
- 新增/编辑车辆档案
- 车辆详情：历史出入记录

### 5.4 报警中心
- 报警类型：
  - `long_stay`：车辆入场后超过配置时长未出场
  - `pending_review`：AI 识别置信度低于阈值，需人工审核
- 处理流程：查看详情 → 填写备注 → 标记已解决
- 历史报警记录

### 5.5 用户管理（厂区管理员+以上）
- 账号列表、新增/禁用账号、角色分配

### 5.6 系统设置（厂区管理员）
- 出入口摄像头配置
- 报警规则：长时间未出场阈值（默认8小时）、AI置信度阈值（默认0.85）

---

## 6. AI 识别服务

- 摄像头推流 → AI 服务持续检测 → 触发事件时调用主服务 API 写入 `gate_events`
- 识别结果含：车牌号、置信度分、抓拍图片
- 置信度 ≥ 0.85：自动确认入库，状态为 `auto_confirmed`
- 置信度 < 0.85：入库状态为 `pending_review`，触发报警通知操作员

---

## 7. 数据流

```
摄像头 → AI识别服务 → POST /api/gate-events → FastAPI主服务
                                                    ↓
                                            写入 PostgreSQL
                                                    ↓
                                            更新 Redis 车辆状态
                                                    ↓
                                        WebSocket 推送前端看板
```

---

## 8. 前端界面

- 布局：左侧固定导航 + 顶部状态栏 + 右侧主内容区
- 导航项：实时看板 / 出入记录 / 车辆管理 / 报警中心 / 系统设置
- 响应式：主要支持桌面端（1280px+），不需要移动端适配（MVP阶段）

---

## 9. 不在本期范围内

- 叉车管理与厂内轨迹
- 任务调度
- 司机移动端 App
- 多厂区切换（架构预留，功能暂不实现）
- 与外部物流系统对接

---

## 10. 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + Vite + TypeScript + Ant Design |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + Alembic |
| AI服务 | Python + OpenCV + PaddleOCR（车牌识别） |
| 数据库 | PostgreSQL 15 |
| 缓存/队列 | Redis 7 |
| 图片存储 | MinIO（本地）/ S3（云端） |
| 部署 | Docker Compose（单机，MVP阶段） |
