import { useEffect, useState } from "react";
import { Table, Tag, Button, Modal, Input, message, Select, Space } from "antd";
import { api } from "../api/client";
import type { Alert } from "../types";
import dayjs from "dayjs";

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [resolving, setResolving] = useState<Alert | null>(null);
  const [note, setNote] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");

  const fetchAlerts = async () => {
    const resp = await api.get(`/alerts?status=${statusFilter}`);
    setAlerts(resp.data);
  };

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter]);

  const handleResolve = async () => {
    if (!resolving) return;
    await api.patch(`/alerts/${resolving.id}/resolve`, { note });
    message.success("已处理");
    setResolving(null);
    fetchAlerts();
  };

  const typeMap: Record<string, string> = {
    long_stay: "长时间未出场",
    pending_review: "需人工审核",
  };

  const severityColor: Record<string, string> = {
    info: "blue",
    warning: "orange",
    critical: "red",
  };

  const columns = [
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      render: (t: string) => typeMap[t] || t,
    },
    { title: "内容", dataIndex: "message", key: "message" },
    {
      title: "级别",
      dataIndex: "severity",
      key: "severity",
      render: (s: string) => (
        <Tag color={severityColor[s] || "default"}>{s}</Tag>
      ),
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => dayjs(t).format("MM-DD HH:mm"),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => (
        <Tag color={s === "active" ? "red" : "green"}>
          {s === "active" ? "待处理" : "已解决"}
        </Tag>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: Alert) =>
        record.status === "active" ? (
          <Button
            size="small"
            type="link"
            onClick={() => {
              setResolving(record);
              setNote("");
            }}
          >
            处理
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          style={{ width: 120 }}
        >
          <Select.Option value="active">待处理</Select.Option>
          <Select.Option value="resolved">已解决</Select.Option>
        </Select>
      </Space>
      <Table dataSource={alerts} columns={columns} rowKey="id" size="small" />
      <Modal
        title="处理报警"
        open={!!resolving}
        onCancel={() => setResolving(null)}
        onOk={handleResolve}
      >
        <p>{resolving?.message}</p>
        <Input.TextArea
          placeholder="处理备注（可选）"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
        />
      </Modal>
    </div>
  );
}
