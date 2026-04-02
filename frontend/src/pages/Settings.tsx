import { useEffect, useState } from "react";
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Switch,
  Space, Tag, message, Typography, Popconfirm, Alert,
} from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";
import type { CheckPoint, PathTemplate, Factory, Department } from "../types";

// ─── 厂区选择器（集团管理员用） ───────────────────────────────────────────

function FactorySelector({
  value, onChange,
}: {
  value: string | null;
  onChange: (id: string) => void;
}) {
  const [factories, setFactories] = useState<Factory[]>([]);

  useEffect(() => {
    api.get("/factories").then(r => setFactories(r.data)).catch(() => {});
  }, []);

  return (
    <div style={{ marginBottom: 16, display: "flex", alignItems: "flex-start", gap: 8, flexWrap: "wrap" }}>
      <span style={{ whiteSpace: "nowrap", lineHeight: "32px" }}>选择厂区：</span>
      <Select
        style={{ width: "min(320px, 100%)", flex: 1 }}
        placeholder="请选择要管理的厂区"
        value={value}
        onChange={onChange}
        options={factories.map(f => ({ value: f.id, label: f.name }))}
      />
    </div>
  );
}

// ─── 厂区管理（集团管理员） ────────────────────────────────────────────────

function FactorySettings() {
  const [factories, setFactories] = useState<Factory[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Factory | null>(null);
  const [form] = Form.useForm();

  const fetchFactories = async () => {
    const resp = await api.get("/factories");
    setFactories(resp.data);
  };

  useEffect(() => { fetchFactories(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (f: Factory) => {
    setEditing(f);
    form.setFieldsValue({ name: f.name, address: f.address, timezone: f.timezone, is_active: f.is_active });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.patch(`/factories/${editing.id}`, values);
        message.success("更新成功");
      } else {
        await api.post("/factories", values);
        message.success("创建成功");
      }
      setModalOpen(false);
      fetchFactories();
    } catch {
      message.error("操作失败");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/factories/${id}`);
      message.success("已删除");
      fetchFactories();
    } catch {
      message.error("删除失败，该厂区可能存在关联数据");
    }
  };

  const columns = [
    { title: "厂区名称", dataIndex: "name" },
    { title: "地址", dataIndex: "address", render: (v: string | null) => v || "—" },
    { title: "时区", dataIndex: "timezone" },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "操作",
      render: (_: unknown, r: Factory) => (
        <Space>
          <Button type="link" onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除此厂区？" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增厂区</Button>
      </div>
      <Table dataSource={factories} columns={columns} rowKey="id" scroll={{ x: 760 }} />
      <Modal
        title={editing ? "编辑厂区" : "新增厂区"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width="min(640px, calc(100vw - 24px))"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="厂区名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="address" label="地址">
            <Input />
          </Form.Item>
          <Form.Item name="timezone" label="时区" initialValue="Asia/Shanghai">
            <Select options={[
              { value: "Asia/Shanghai", label: "亚洲/上海 (UTC+8)" },
              { value: "Asia/Hong_Kong", label: "亚洲/香港 (UTC+8)" },
              { value: "America/Toronto", label: "美洲/多伦多" },
              { value: "America/Vancouver", label: "美洲/温哥华" },
            ]} />
          </Form.Item>
          {editing && (
            <Form.Item name="is_active" label="状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}

// ─── 节点管理 ────────────────────────────────────────────────────────────

function DepartmentSettings({ factoryId }: { factoryId: string | null }) {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [form] = Form.useForm();

  const fetchDepartments = async () => {
    const params = factoryId ? { factory_id: factoryId } : {};
    const resp = await api.get("/departments", { params });
    setDepartments(resp.data);
  };

  useEffect(() => {
    if (factoryId !== undefined) fetchDepartments();
  }, [factoryId]);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (department: Department) => {
    setEditing(department);
    form.setFieldsValue({ name: department.name, is_active: department.is_active });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.patch(`/departments/${editing.id}`, values);
      } else {
        await api.post("/departments", factoryId ? { ...values, factory_id: factoryId } : values);
      }
      message.success(editing ? "更新成功" : "创建成功");
      setModalOpen(false);
      fetchDepartments();
    } catch {
      message.error("操作失败");
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!factoryId}>
          新增部门
        </Button>
      </div>
      <Table
        dataSource={departments}
        rowKey="id"
        scroll={{ x: 560 }}
        columns={[
          { title: "部门名称", dataIndex: "name" },
          { title: "状态", dataIndex: "is_active", render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag> },
          { title: "操作", render: (_: unknown, row: Department) => <Button type="link" onClick={() => openEdit(row)}>编辑</Button> },
        ]}
      />
      <Modal
        title={editing ? "编辑部门" : "新增部门"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width="min(560px, calc(100vw - 24px))"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="部门名称" rules={[{ required: true, message: "请输入部门名称" }]}>
            <Input />
          </Form.Item>
          {editing && (
            <Form.Item name="is_active" label="状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}

function CheckpointSettings({ factoryId }: { factoryId: string | null }) {
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CheckPoint | null>(null);
  const [form] = Form.useForm();

  const fetchCheckpoints = async () => {
    const params = factoryId ? { factory_id: factoryId } : {};
    const [checkpointResp, departmentResp] = await Promise.all([
      api.get("/checkpoints", { params }),
      api.get("/departments", { params }),
    ]);
    setCheckpoints(checkpointResp.data);
    setDepartments(departmentResp.data);
  };

  useEffect(() => {
    if (factoryId !== undefined) fetchCheckpoints();
  }, [factoryId]);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (cp: CheckPoint) => {
    setEditing(cp);
    form.setFieldsValue({ name: cp.name, is_gate: cp.is_gate, department_id: cp.department_id });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.patch(`/checkpoints/${editing.id}`, values);
        message.success("更新成功");
      } else {
        const body = factoryId ? { ...values, factory_id: factoryId } : values;
        await api.post("/checkpoints", body);
        message.success("创建成功");
      }
      setModalOpen(false);
      fetchCheckpoints();
    } catch {
      message.error("操作失败");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/checkpoints/${id}`);
      message.success("已删除");
      fetchCheckpoints();
    } catch {
      message.error("删除失败，该节点可能存在关联数据");
    }
  };

  const columns = [
    { title: "节点名称", dataIndex: "name" },
    {
      title: "所属部门",
      dataIndex: "department_id",
      render: (value: string | null) => departments.find((item) => item.id === value)?.name || "—",
    },
    {
      title: "类型",
      dataIndex: "is_gate",
      render: (v: boolean) => <Tag color={v ? "blue" : "default"}>{v ? "大门节点" : "内部节点"}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "操作",
      render: (_: unknown, r: CheckPoint) => (
        <Space>
          <Button type="link" onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除此节点？" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!factoryId}>
          新增节点
        </Button>
      </div>
      <Table dataSource={checkpoints} columns={columns} rowKey="id" scroll={{ x: 860 }} />
      <Modal
        title={editing ? "编辑节点" : "新增节点"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width="min(640px, calc(100vw - 24px))"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="节点名称" rules={[{ required: true, message: "请输入节点名称" }]}>
            <Input placeholder="如：厂区大门、1号仓库、2号仓库" />
          </Form.Item>
          <Form.Item name="department_id" label="所属部门">
            <Select
              allowClear
              placeholder="可选，未设置时沿用当前默认权限"
              options={departments.map((item) => ({ value: item.id, label: item.name }))}
            />
          </Form.Item>
          <Form.Item name="is_gate" label="是否大门节点" valuePropName="checked">
            <Switch checkedChildren="大门" unCheckedChildren="内部" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

// ─── 路径模板 ────────────────────────────────────────────────────────────

function TemplateSettings({ factoryId }: { factoryId: string | null }) {
  const [templates, setTemplates] = useState<PathTemplate[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<PathTemplate | null>(null);
  const [form] = Form.useForm();

  const fetchAll = async () => {
    const params = factoryId ? { factory_id: factoryId } : {};
    const [tResp, cResp] = await Promise.all([
      api.get("/path-templates", { params }),
      api.get("/checkpoints", { params }),
    ]);
    setTemplates(tResp.data);
    setCheckpoints(cResp.data);
  };

  useEffect(() => {
    if (factoryId !== undefined) fetchAll();
  }, [factoryId]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (tmpl: PathTemplate) => {
    setEditing(tmpl);
    const sortedSteps = [...tmpl.steps].sort((a, b) => a.step_order - b.step_order);
    form.setFieldsValue({
      name: tmpl.name,
      is_active: tmpl.is_active,
      steps: sortedSteps.map(s => ({
        checkpoint_id: s.checkpoint_id,
        direction: s.direction,
        step_order: s.step_order,
      })),
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    // 重新计算 step_order 按当前顺序
    const steps = (values.steps || []).map((s: { checkpoint_id: string; direction: string }, i: number) => ({
      ...s,
      step_order: i + 1,
    }));
    try {
      if (editing) {
        await api.patch(`/path-templates/${editing.id}`, { ...values, steps });
        message.success("更新成功");
      } else {
        const body = factoryId ? { ...values, steps, factory_id: factoryId } : { ...values, steps };
        await api.post("/path-templates", body);
        message.success("创建成功");
      }
      setModalOpen(false);
      fetchAll();
    } catch {
      message.error(editing ? "更新失败" : "创建失败");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/path-templates/${id}`);
      message.success("已删除");
      fetchAll();
    } catch {
      message.error("删除失败");
    }
  };

  const cpOptions = checkpoints.map(cp => ({ value: cp.id, label: cp.name }));

  const columns = [
    { title: "模板名称", dataIndex: "name" },
    {
      title: "步骤数",
      dataIndex: "steps",
      render: (steps: PathTemplate["steps"]) => steps?.length ?? 0,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "操作",
      render: (_: unknown, r: PathTemplate) => (
        <Space>
          <Button type="link" onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除此模板？" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!factoryId}>
          新建模板
        </Button>
      </div>
      <Table dataSource={templates} columns={columns} rowKey="id" scroll={{ x: 760 }} />
      <Modal
        title={editing ? "编辑路径模板" : "新建路径模板"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width="min(620px, calc(100vw - 24px))"
        styles={{ body: { maxHeight: "60vh", overflowY: "auto" } }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如：标准入库路径" />
          </Form.Item>
          {editing && (
            <Form.Item name="is_active" label="状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>
          )}
          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <span style={{ fontWeight: 500 }}>途经节点（无固定顺序）</span>
                  <Button size="small" type="dashed" onClick={() => add({ direction: "any" })}>
                    + 添加节点
                  </Button>
                </div>
                {fields.map((field) => (
                  <div key={field.key} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
                    <Form.Item name={[field.name, "checkpoint_id"]} rules={[{ required: true, message: "请选择节点" }]} style={{ marginBottom: 0, flex: 1 }}>
                      <Select placeholder="选择节点" options={cpOptions} />
                    </Form.Item>
                    <Form.Item name={[field.name, "direction"]} rules={[{ required: true }]} style={{ marginBottom: 0, width: 90 }}>
                      <Select options={[
                        { value: "entry", label: "进入" },
                        { value: "exit", label: "离开" },
                        { value: "any", label: "任意" },
                      ]} />
                    </Form.Item>
                    <Button danger size="small" onClick={() => remove(field.name)}>删除</Button>
                  </div>
                ))}
                {fields.length === 0 && (
                  <div style={{ color: "#aaa", fontSize: 12, padding: "8px 0" }}>暂无途经节点，点击"添加节点"开始配置</div>
                )}
              </div>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}

// ─── 主页面 ───────────────────────────────────────────────────────────────

export default function Settings() {
  const { user } = useAuthStore();
  const canChooseFactory = user?.role === "group_admin" || user?.role === "system_admin";
  const [selectedFactory, setSelectedFactory] = useState<string | null>(null);

  // factory_manager 使用自己的 factory_id；group/system admin 使用选择的厂区
  const factoryId = canChooseFactory ? selectedFactory : (user?.factory_id ?? null);

  const tabs = [
    ...(user?.role === "group_admin" ? [{ key: "factories", label: "厂区管理", children: <FactorySettings /> }] : []),
    {
      key: "departments",
      label: "部门管理",
      children: (
        <div>
          {canChooseFactory && (
            <>
              <FactorySelector value={selectedFactory} onChange={setSelectedFactory} />
              {!selectedFactory && (
                <Alert message="请先选择厂区" type="info" showIcon style={{ marginBottom: 16 }} />
              )}
            </>
          )}
          <DepartmentSettings factoryId={factoryId} />
        </div>
      ),
    },
    {
      key: "checkpoints",
      label: "节点管理",
      children: (
        <div>
          {canChooseFactory && (
            <>
              <FactorySelector value={selectedFactory} onChange={setSelectedFactory} />
              {!selectedFactory && (
                <Alert message="请先选择厂区" type="info" showIcon style={{ marginBottom: 16 }} />
              )}
            </>
          )}
          <CheckpointSettings factoryId={factoryId} />
        </div>
      ),
    },
    {
      key: "templates",
      label: "路径模板",
      children: (
        <div>
          {canChooseFactory && (
            <>
              <FactorySelector value={selectedFactory} onChange={setSelectedFactory} />
              {!selectedFactory && (
                <Alert message="请先选择厂区" type="info" showIcon style={{ marginBottom: 16 }} />
              )}
            </>
          )}
          <TemplateSettings factoryId={factoryId} />
        </div>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>系统设置</Typography.Title>
      <Tabs items={tabs} tabBarGutter={12} />
    </div>
  );
}
