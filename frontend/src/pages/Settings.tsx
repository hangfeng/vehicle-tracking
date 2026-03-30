import { useEffect, useState } from "react";
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Switch,
  Space, Tag, message, Typography, Popconfirm,
} from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import type { CheckPoint, PathTemplate } from "../types";

function CheckpointSettings() {
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CheckPoint | null>(null);
  const [form] = Form.useForm();

  const fetchCheckpoints = async () => {
    const resp = await api.get("/checkpoints");
    setCheckpoints(resp.data);
  };

  useEffect(() => { fetchCheckpoints(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (cp: CheckPoint) => {
    setEditing(cp);
    form.setFieldsValue({
      name: cp.name,
      identification_method: cp.identification_method,
      is_gate: cp.is_gate,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.patch(`/checkpoints/${editing.id}`, values);
        message.success("更新成功");
      } else {
        await api.post("/checkpoints", values);
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
    { title: "名称", dataIndex: "name" },
    {
      title: "识别方式",
      dataIndex: "identification_method",
      render: (v: string) => <Tag>{v === "camera" ? "摄像头" : "手动"}</Tag>,
    },
    {
      title: "类型",
      dataIndex: "is_gate",
      render: (v: boolean) => <Tag color={v ? "blue" : "default"}>{v ? "大门" : "内部节点"}</Tag>,
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
            <Button type="link" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增节点</Button>
      </div>
      <Table dataSource={checkpoints} columns={columns} rowKey="id" />
      <Modal
        title={editing ? "编辑节点" : "新增节点"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="节点名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="identification_method" label="识别方式" rules={[{ required: true }]}>
            <Select options={[
              { value: "camera", label: "摄像头" },
              { value: "manual", label: "手动录入" },
            ]} />
          </Form.Item>
          <Form.Item name="is_gate" label="是否大门节点" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function TemplateSettings() {
  const [templates, setTemplates] = useState<PathTemplate[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchAll = async () => {
    const [tResp, cResp] = await Promise.all([
      api.get("/path-templates"),
      api.get("/checkpoints"),
    ]);
    setTemplates(tResp.data);
    setCheckpoints(cResp.data);
  };

  useEffect(() => { fetchAll(); }, []);

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      await api.post("/path-templates", values);
      message.success("创建成功");
      setModalOpen(false);
      fetchAll();
    } catch {
      message.error("创建失败");
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
        <Popconfirm title="确认删除此模板？" onConfirm={() => handleDelete(r.id)}>
          <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => { form.resetFields(); setModalOpen(true); }}
        >
          新建模板
        </Button>
      </div>
      <Table dataSource={templates} columns={columns} rowKey="id" />
      <Modal
        title="新建路径模板"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <span>步骤列表</span>
                  <Button
                    size="small"
                    onClick={() => add({ step_order: fields.length + 1, direction: "entry" })}
                  >
                    + 添加步骤
                  </Button>
                </div>
                {fields.map((field, index) => (
                  <Space key={field.key} style={{ display: "flex", marginBottom: 8 }} align="start">
                    <Form.Item name={[field.name, "checkpoint_id"]} rules={[{ required: true }]} noStyle>
                      <Select placeholder="选择节点" style={{ width: 160 }} options={cpOptions} />
                    </Form.Item>
                    <Form.Item name={[field.name, "direction"]} rules={[{ required: true }]} noStyle>
                      <Select style={{ width: 100 }} options={[
                        { value: "entry", label: "进入" },
                        { value: "exit", label: "离开" },
                        { value: "any", label: "任意" },
                      ]} />
                    </Form.Item>
                    <Form.Item name={[field.name, "step_order"]} initialValue={index + 1} hidden>
                      <Input />
                    </Form.Item>
                    <Button danger onClick={() => remove(field.name)}>删除</Button>
                  </Space>
                ))}
              </div>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}

export default function Settings() {
  return (
    <div>
      <Typography.Title level={4}>系统设置</Typography.Title>
      <Tabs
        items={[
          { key: "checkpoints", label: "节点管理", children: <CheckpointSettings /> },
          { key: "templates", label: "路径模板", children: <TemplateSettings /> },
        ]}
      />
    </div>
  );
}
