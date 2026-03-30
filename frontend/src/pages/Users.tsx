import { useEffect, useState } from "react";
import {
  Table, Button, Tag, Drawer, Form, Input, Select, Space,
  Popconfirm, Typography, message,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";
import type { User, UserRole } from "../types";
import dayjs from "dayjs";

const roleLabels: Record<UserRole, string> = {
  group_admin: "集团管理员",
  factory_manager: "厂区管理员",
  operator: "操作员",
};
const roleColors: Record<UserRole, string> = {
  group_admin: "blue",
  factory_manager: "green",
  operator: "default",
};

export default function Users() {
  const { user: me } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    const resp = await api.get("/users");
    setUsers(resp.data);
  };

  useEffect(() => { fetchUsers(); }, []);

  const openCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setDrawerOpen(true);
  };

  const openEdit = (u: User) => {
    setEditingUser(u);
    form.setFieldsValue({ name: u.name, role: u.role, factory_id: u.factory_id });
    setDrawerOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editingUser) {
        await api.patch(`/users/${editingUser.id}`, values);
        message.success("更新成功");
      } else {
        await api.post("/users", values);
        message.success("创建成功");
      }
      setDrawerOpen(false);
      fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || "操作失败");
    }
  };

  const handleBatchStatus = async (is_active: boolean) => {
    const resp = await api.post("/users/batch-status", { ids: selectedIds, is_active });
    message.success(`已${is_active ? "启用" : "停用"} ${resp.data.updated} 个用户`);
    setSelectedIds([]);
    fetchUsers();
  };

  const availableRoles: UserRole[] = me?.role === "group_admin"
    ? ["group_admin", "factory_manager", "operator"]
    : ["operator"];

  const columns = [
    { title: "姓名", dataIndex: "name", key: "name" },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    {
      title: "角色",
      dataIndex: "role",
      key: "role",
      render: (r: UserRole) => <Tag color={roleColors[r]}>{roleLabels[r]}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: User) => (
        <Button type="link" onClick={() => openEdit(record)}>编辑</Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>用户管理</Typography.Title>
        <Space>
          {selectedIds.length > 0 && (
            <>
              <Popconfirm title="确认启用选中用户？" onConfirm={() => handleBatchStatus(true)}>
                <Button>批量启用</Button>
              </Popconfirm>
              <Popconfirm title="确认停用选中用户？" onConfirm={() => handleBatchStatus(false)}>
                <Button danger>批量停用</Button>
              </Popconfirm>
            </>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户</Button>
        </Space>
      </div>

      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as string[]),
        }}
      />

      <Drawer
        title={editingUser ? "编辑用户" : "新建用户"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={
          <Button type="primary" onClick={handleSubmit} block>保存</Button>
        }
      >
        <Form form={form} layout="vertical">
          {!editingUser && (
            <>
              <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="password" label="初始密码" rules={[{ required: true }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="role" label="角色" rules={[{ required: true }]}>
              <Select options={availableRoles.map(r => ({ value: r, label: roleLabels[r] }))} />
            </Form.Item>
          )}
        </Form>
      </Drawer>
    </div>
  );
}
