import { useEffect, useState } from "react";
import {
  Table, Button, Tag, Drawer, Form, Input, Select, Space, Switch,
  Popconfirm, Typography, message, Modal,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";
import type { User, UserRole, Factory, Department } from "../types";
import dayjs from "dayjs";

const roleLabels: Record<UserRole, string> = {
  system_admin: "系统管理员",
  group_admin: "集团管理员",
  factory_manager: "厂区管理员",
  operator: "操作员",
};
const roleColors: Record<UserRole, string> = {
  system_admin: "purple",
  group_admin: "blue",
  factory_manager: "green",
  operator: "default",
};

export default function Users() {
  const { user: me, tokenRole } = useAuthStore();
  const effectiveRole = me?.role ?? tokenRole;
  const isSuper = effectiveRole === "system_admin" || effectiveRole === "group_admin";
  const [users, setUsers] = useState<User[]>([]);
  const [factories, setFactories] = useState<Factory[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [form] = Form.useForm();
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetTargetId, setResetTargetId] = useState<string | null>(null);
  const [resetForm] = Form.useForm();
  const [formRole, setFormRole] = useState<UserRole | undefined>(undefined);
  const selectedFactoryId = Form.useWatch("factory_id", form);
  const effectiveFactoryId = selectedFactoryId ?? me?.factory_id ?? editingUser?.factory_id ?? null;
  const shouldSelectFactory = isSuper && formRole && formRole !== "group_admin" && formRole !== "system_admin";
  const shouldSelectDepartment = formRole && formRole !== "group_admin" && formRole !== "system_admin";

  const fetchUsers = async () => {
    const resp = await api.get("/users");
    setUsers(resp.data);
  };

  useEffect(() => {
    fetchUsers();
    if (isSuper) {
      api.get("/factories").then(r => setFactories(r.data)).catch(() => {});
    }
    api.get("/departments").then(r => setDepartments(r.data)).catch(() => {});
  }, [effectiveRole]);

  const openCreate = () => {
    setEditingUser(null);
    form.resetFields();
    if (effectiveRole === "factory_manager" && me?.factory_id) {
      setFormRole("operator");
      form.setFieldsValue({
        role: "operator",
        factory_id: me.factory_id,
        department_id: undefined,
        is_active: true,
      });
    } else {
      setFormRole(undefined);
      if (isSuper) {
        form.setFieldsValue({
          factory_id: undefined,
          department_id: undefined,
          is_active: true,
        });
      }
    }
    setDrawerOpen(true);
  };

  const openEdit = (u: User) => {
    setEditingUser(u);
    setFormRole(u.role);
    form.setFieldsValue({
      phone: u.phone,
      name: u.name,
      role: u.role,
      factory_id: u.factory_id,
      department_id: u.department_id,
      is_active: u.is_active,
    });
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

  const openResetPassword = (userId: string) => {
    setResetTargetId(userId);
    resetForm.resetFields();
    setResetModalOpen(true);
  };

  const handleResetPassword = async () => {
    const values = await resetForm.validateFields();
    try {
      await api.post(`/users/${resetTargetId}/reset-password`, { new_password: values.new_password });
      message.success("密码已重置");
      setResetModalOpen(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(error.response?.data?.detail || "重置失败");
    }
  };

  const handleBatchStatus = async (is_active: boolean) => {
    const resp = await api.post("/users/batch-status", { ids: selectedIds, is_active });
    message.success(`已${is_active ? "启用" : "停用"} ${resp.data.updated} 个用户`);
    setSelectedIds([]);
    fetchUsers();
  };

  const availableRoles: UserRole[] = effectiveRole === "system_admin"
    ? ["system_admin", "group_admin", "factory_manager", "operator"]
    : effectiveRole === "group_admin"
      ? ["group_admin", "factory_manager", "operator"]
      : ["operator"];
  const departmentOptions = departments
    .filter((item) => !effectiveFactoryId || item.factory_id === effectiveFactoryId)
    .map((item) => ({ value: item.id, label: item.name }));

  useEffect(() => {
    const currentDepartmentId = form.getFieldValue("department_id");
    if (currentDepartmentId && !departmentOptions.some((item) => item.value === currentDepartmentId)) {
      form.setFieldValue("department_id", undefined);
    }
  }, [departmentOptions, form]);

  useEffect(() => {
    if (formRole === "group_admin" || formRole === "system_admin") {
      form.setFieldsValue({ factory_id: undefined, department_id: undefined });
      return;
    }
    if (effectiveRole === "factory_manager" && me?.factory_id) {
      form.setFieldValue("factory_id", me.factory_id);
    }
  }, [effectiveRole, form, me?.factory_id, formRole]);

  const columns = [
    { title: "流水号", dataIndex: "serial_no", key: "serial_no", render: (value: string | null) => value || "—" },
    { title: "姓名", dataIndex: "name", key: "name" },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    {
      title: "部门",
      dataIndex: "department_id",
      key: "department_id",
      render: (value: string | null) => departments.find((item) => item.id === value)?.name || "—",
    },
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
        <Space>
          <Button type="link" onClick={() => openEdit(record)}>编辑</Button>
          {isSuper && (
            <Button type="link" onClick={() => openResetPassword(record.id)}>重置密码</Button>
          )}
        </Space>
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
        scroll={{ x: 1100 }}
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as string[]),
        }}
      />

      <Modal
        title="重置密码"
        open={resetModalOpen}
        onOk={handleResetPassword}
        onCancel={() => setResetModalOpen(false)}
        okText="确认重置"
      >
        <Form form={resetForm} layout="vertical">
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[{ required: true, min: 6, message: "密码至少6位" }]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={editingUser ? "编辑用户" : "新建用户"}
        open={drawerOpen}
        width="min(520px, 100vw)"
        onClose={() => setDrawerOpen(false)}
        footer={
          <Button type="primary" onClick={handleSubmit} block>保存</Button>
        }
      >
        <Form form={form} layout="vertical" onValuesChange={(changed) => {
          if ("role" in changed) setFormRole(changed.role as UserRole | undefined);
        }}>
          <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          {!editingUser && (
            <>
              <Form.Item name="password" label="初始密码" rules={[{ required: true }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={availableRoles.map(r => ({ value: r, label: roleLabels[r] }))} />
          </Form.Item>
          {shouldSelectFactory && (
            <Form.Item
              name="factory_id"
              label="所属厂区"
              rules={[{ required: true, message: "请选择所属厂区" }]}
            >
              <Select
                placeholder="请选择所属厂区"
                options={factories.map(f => ({ value: f.id, label: f.name }))}
              />
            </Form.Item>
          )}
          {effectiveRole === "factory_manager" && me?.factory_id && (
            <Form.Item name="factory_id" hidden>
              <Input />
            </Form.Item>
          )}
          {shouldSelectDepartment && (
            <Form.Item
              name="department_id"
              label="所属部门"
              rules={[{ required: true, message: "请选择所属部门" }]}
            >
              <Select
                placeholder={effectiveFactoryId ? "请选择所属部门" : "请先选择所属厂区"}
                options={departmentOptions}
                disabled={!effectiveFactoryId}
              />
            </Form.Item>
          )}
          {editingUser && (
            <Form.Item name="is_active" label="启用状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>
          )}
        </Form>
      </Drawer>
    </div>
  );
}
