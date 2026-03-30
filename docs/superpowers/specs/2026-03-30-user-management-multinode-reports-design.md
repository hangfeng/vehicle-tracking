# 用户管理 + 多节点追踪 + 批量操作 + 报表中心 设计规格

**版本：** MVP 扩展 v1
**日期：** 2026-03-30
**基础系统：** 厂区车辆进出管理系统（已上线）

---

## 1. 背景与目标

在现有系统（摄像头车牌识别、出入记录、看板、报警）基础上，新增四个功能模块：

| 模块 | 核心价值 |
|---|---|
| 用户管理 | 管理员在界面上管理账号和权限，无需直接操作数据库 |
| 多节点追踪 | 追踪车辆在厂内各区域（仓库、质检区等）的完整路径 |
| 批量操作 | 提升效率：批量审核记录、Excel 导入车辆、批量管理用户 |
| 报表中心 | 日/周/月统计分析，支持自定义筛选导出 PDF/Excel |

**设计原则：不改动、不删除现有 `locations`/`gate_events` 表，新功能并行新增。**

---

## 2. 用户角色权限

### 用户管理权限矩阵

| 操作 | group_admin | factory_manager | operator |
|---|---|---|---|
| 查看所有用户 | ✅ | ❌ | ❌ |
| 查看本厂区用户 | ✅ | ✅ | ❌ |
| 创建 group_admin | ✅ | ❌ | ❌ |
| 创建 factory_manager | ✅ | ❌ | ❌ |
| 创建本厂区 operator | ✅ | ✅ | ❌ |
| 编辑任意用户 | ✅ | ❌ | ❌ |
| 编辑本厂区 operator | ✅ | ✅ | ❌ |
| 批量启用/停用用户 | ✅（全局） | ✅（本厂区 operator） | ❌ |

---

## 3. 数据模型

### 3.1 新增表（不删除现有表）

#### `checkpoints` — 节点配置

```sql
id              UUID PRIMARY KEY
factory_id      UUID FK→factories
name            VARCHAR(100)          -- 例："北门"、"仓库A入口"
identification_method  ENUM(camera, manual)
is_gate         BOOLEAN               -- true=大门（影响在厂状态），false=内部节点
camera_config   JSONB NULL            -- {"rtsp_url": "...", "confidence_threshold": 0.85}
is_active       BOOLEAN DEFAULT true
created_at      TIMESTAMP
```

#### `path_templates` — 路径模板

```sql
id              UUID PRIMARY KEY
factory_id      UUID FK→factories
name            VARCHAR(100)
is_active       BOOLEAN DEFAULT true
created_at      TIMESTAMP
```

#### `path_template_steps` — 模板步骤

```sql
id              UUID PRIMARY KEY
template_id     UUID FK→path_templates
checkpoint_id   UUID FK→checkpoints
step_order      INTEGER               -- 1, 2, 3...
direction       ENUM(entry, exit, any)
```

#### `vehicle_journeys` — 车辆行程

```sql
id              UUID PRIMARY KEY
vehicle_id      UUID FK→vehicles
factory_id      UUID FK→factories
template_id     UUID FK→path_templates NULL  -- null=无模板/自由行程
started_at      TIMESTAMP
completed_at    TIMESTAMP NULL
status          ENUM(active, completed, deviated)
```

#### `journey_events` — 行程节点事件

```sql
id              UUID PRIMARY KEY
journey_id      UUID FK→vehicle_journeys
gate_event_id   UUID FK→gate_events NULL     -- 现有大门事件
checkpoint_id   UUID FK→checkpoints
direction       ENUM(entry, exit)
occurred_at     TIMESTAMP
is_deviation    BOOLEAN DEFAULT false
notes           TEXT NULL
```

### 3.2 现有表改动

#### `vehicles` 表新增字段

```sql
current_checkpoint_id  UUID FK→checkpoints NULL  -- NULL=不在厂内
```

#### `alerts` 表新增 alert_type 枚举值

```
path_deviation  -- 车辆偏离路径模板
```

---

## 4. API 端点

### 4.1 用户管理

```
GET    /users                    -- 列表（group_admin全局，factory_manager本厂区）
POST   /users                    -- 创建用户
GET    /users/{id}               -- 详情
PATCH  /users/{id}               -- 更新（name, role, factory_id, is_active）
POST   /users/batch-status       -- 批量启用/停用 {ids: [...], is_active: bool}
```

**创建用户请求体：**
```json
{
  "phone": "13900000003",
  "name": "张三",
  "password": "initial_password",
  "role": "operator",
  "factory_id": "uuid"
}
```

### 4.2 节点管理（CheckPoint）

```
GET    /checkpoints              -- 列表（按 factory_id 过滤）
POST   /checkpoints              -- 创建
PATCH  /checkpoints/{id}         -- 更新
DELETE /checkpoints/{id}         -- 删除（有关联事件时拒绝）
```

### 4.3 路径模板

```
GET    /path-templates           -- 列表
POST   /path-templates           -- 创建（含 steps 数组）
GET    /path-templates/{id}      -- 详情（含步骤）
PATCH  /path-templates/{id}      -- 更新
DELETE /path-templates/{id}      -- 删除
```

**创建模板请求体：**
```json
{
  "name": "标准进厂路径",
  "steps": [
    {"checkpoint_id": "uuid", "step_order": 1, "direction": "entry"},
    {"checkpoint_id": "uuid", "step_order": 2, "direction": "entry"},
    {"checkpoint_id": "uuid", "step_order": 3, "direction": "exit"}
  ]
}
```

### 4.4 车辆行程

```
GET    /vehicles/{id}/journey    -- 当前活跃行程
GET    /vehicles/{id}/journeys   -- 历史行程列表
POST   /vehicle-journeys         -- 启动新行程
POST   /journey-events           -- 记录节点事件（手动或摄像头）
```

**启动行程请求体：**
```json
{
  "vehicle_id": "uuid",
  "factory_id": "uuid",
  "template_id": "uuid or null"
}
```

**记录节点事件请求体：**
```json
{
  "journey_id": "uuid",
  "checkpoint_id": "uuid",
  "direction": "entry",
  "license_plate": "粤B12345",
  "confidence": 0.92,
  "image_url": "http://...",
  "notes": null
}
```

### 4.5 批量操作

```
POST   /gate-events/batch-review -- 批量审核 {ids: [...], action: "confirm"|"reject"}
POST   /vehicles/import          -- Excel 批量导入（multipart/form-data）
POST   /users/batch-status       -- 见 4.1
```

**Excel 导入格式（车辆）：**

| 列名 | 必填 | 说明 |
|---|---|---|
| 车牌号 | ✅ | 唯一键 |
| 所属公司 | ✅ | |
| 联系人 | ❌ | |
| 联系电话 | ❌ | |

### 4.6 报表

```
GET    /reports/traffic          -- 进出流量统计
GET    /reports/vehicles         -- 车辆行为分析
GET    /reports/alerts           -- 报警汇总
GET    /reports/export           -- 导出（format=excel|pdf）
```

**通用查询参数：**
```
start_date   YYYY-MM-DD
end_date     YYYY-MM-DD
factory_id   UUID（group_admin 可选）
checkpoint_id UUID（可选）
vehicle_id   UUID（可选）
granularity  day|week|month
```

**流量统计响应：**
```json
{
  "total_entries": 120,
  "total_exits": 118,
  "avg_stay_duration_minutes": 95,
  "by_day": [
    {"date": "2026-03-30", "entries": 15, "exits": 14}
  ],
  "by_checkpoint": [
    {"checkpoint_id": "uuid", "name": "北门", "entries": 60, "exits": 58}
  ]
}
```

---

## 5. 前端页面

### 5.1 新增页面

| 路由 | 页面 | 权限 |
|---|---|---|
| `/users` | 用户管理 | group_admin, factory_manager |
| `/reports` | 报表中心 | 全部角色（内容按权限过滤） |

### 5.2 现有页面扩展

| 页面 | 新增内容 |
|---|---|
| `/gate-events` | 批量审核（多选 + 批量确认/拒绝按钮） |
| `/vehicles` | 批量导入按钮（上传 Excel）；车辆详情增加行程时间轴 |
| 系统设置 | 新增"节点管理"和"路径模板"标签页 |
| 导航栏 | 新增"用户管理"和"报表"入口 |

### 5.3 用户管理页面交互

- 列表：表格显示 phone、name、role、factory、状态、操作
- 多选 → 批量启用/停用
- 新建/编辑：侧滑抽屉表单
- factory_manager 只看到本厂区 operator，不显示角色选择

### 5.4 报表中心页面结构

- 顶部：时间范围选择器（快捷：今日/本周/本月/自定义）+ 厂区/节点筛选
- 指标卡：总进次数、总出次数、平均在厂时长、报警次数
- 折线图：进出趋势（按选定粒度）
- 节点热力表：各节点流量排行
- 报警汇总：按类型分类
- 右上角导出按钮（Excel/PDF）

---

## 6. 路径偏离检测逻辑

**行程启动方式：**
- 操作员在"出入记录"页手动为车辆选择模板并启动行程
- 或不选模板直接启动（自由行程）
- 一辆车同一时间只能有一个 `active` 行程

**偏离检测流程：**
1. 记录 `journey_event` 时，查询当前行程的 `template_id`（如果有）
2. 比对当前事件与模板期望的下一步骤（checkpoint_id + direction）
3. 不匹配 → `is_deviation=true` + 创建 `path_deviation` 报警
4. 所有模板步骤按序完成 → `vehicle_journeys.status=completed`
5. 无模板（自由行程） → 仅记录，不触发偏离报警

---

## 7. 本期不在范围内

- 节点实时视频预览
- 多厂区路径模板共享
- 报表定时自动发送邮件
- 叉车管理
- 移动端 App

---

## 8. 技术依赖新增

| 依赖 | 用途 |
|---|---|
| `reportlab` | PDF 导出 |
| `openpyxl` | 已有，Excel 导入/导出 |
| `pandas` | 报表数据聚合计算 |

---

## 9. 迁移策略

- Alembic 新增迁移：创建 5 张新表 + `vehicles.current_checkpoint_id`
- 现有 `locations`/`gate_events` 数据保留不动
- 后续版本可选择将 `gate_events` 数据迁移至 `journey_events`（本期不做）
