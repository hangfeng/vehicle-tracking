import { useEffect, useState, useRef } from "react";
import { Row, Col, Statistic, Card, Table, Tag, Space } from "antd";
import {
  CarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  AlertOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { api } from "../api/client";
import type { DashboardRecentAccessRecord, DashboardStats } from "../types";
import { useAuthStore } from "../store/auth";
import dayjs from "dayjs";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentRecords, setRecentRecords] = useState<DashboardRecentAccessRecord[]>([]);
  const { user } = useAuthStore();
  const wsRef = useRef<WebSocket | null>(null);

  const fetchData = async () => {
    try {
      const [statsRes, recordsRes] = await Promise.all([
        api.get("/dashboard/stats"),
        api.get("/dashboard/recent-access-records?limit=10"),
      ]);
      setStats(statsRes.data);
      setRecentRecords(recordsRes.data);
    } catch {
      // ignore fetch errors on background refresh
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);

    if (user?.factory_id) {
      const ws = new WebSocket(
        `ws://localhost:8000/dashboard/ws/${user.factory_id}`
      );
      ws.onmessage = () => fetchData();
      wsRef.current = ws;
    }

    return () => {
      clearInterval(interval);
      wsRef.current?.close();
    };
  }, [user]);

  const formatStayDuration = (minutes: number | null) => {
    if (minutes === null) return "—";
    const hours = Math.floor(minutes / 60);
    const remainMinutes = minutes % 60;
    if (hours === 0) return `${remainMinutes} 分钟`;
    if (remainMinutes === 0) return `${hours} 小时`;
    return `${hours} 小时 ${remainMinutes} 分钟`;
  };

  const columns = [
    { title: "编号", dataIndex: "record_no", key: "record_no" },
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    {
      title: "入场时间",
      dataIndex: "entry_time",
      key: "entry_time",
      render: (t: string | null) => t ? dayjs(t).format("MM-DD HH:mm:ss") : "—",
    },
    {
      title: "出场时间",
      dataIndex: "exit_time",
      key: "exit_time",
      render: (t: string | null) => t ? dayjs(t).format("MM-DD HH:mm:ss") : "—",
    },
    {
      title: "在厂时长",
      dataIndex: "stay_duration_minutes",
      key: "stay_duration_minutes",
      render: (minutes: number | null) => formatStayDuration(minutes),
    },
    {
      title: "经过节点",
      dataIndex: "path_nodes",
      key: "path_nodes",
      render: (pathNodes: DashboardRecentAccessRecord["path_nodes"]) => (
        <Space direction="vertical" size={0}>
          {pathNodes.map((node) => (
            <span key={`${node.checkpoint_id}-${node.event_time}`}>
              {node.checkpoint_name} · {dayjs(node.event_time).format("HH:mm:ss")}
            </span>
          ))}
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (status: DashboardRecentAccessRecord["status"]) => {
        if (status === "completed") return <Tag color="blue">已完成进出</Tag>;
        if (status === "in_factory") return <Tag color="green">仍在厂内</Tag>;
        return <Tag color="orange">仅出场记录</Tag>;
      },
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={5}>
          <Card>
            <Statistic
              title="在厂车辆"
              value={stats?.vehicles_in_factory ?? "-"}
              prefix={<CarOutlined />}
            />
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <Statistic
              title="今日入场"
              value={stats?.entries_today ?? "-"}
              prefix={<ArrowDownOutlined />}
              valueStyle={{ color: "#3f8600" }}
            />
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <Statistic
              title="今日出场"
              value={stats?.exits_today ?? "-"}
              prefix={<ArrowUpOutlined />}
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <Statistic
              title="待审核"
              value={stats?.pending_review_count ?? "-"}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: "#fa8c16" }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="活跃报警"
              value={stats?.active_alerts_count ?? "-"}
              prefix={<AlertOutlined />}
              valueStyle={{ color: "#ff4d4f" }}
            />
          </Card>
        </Col>
      </Row>
      <Card title="最近出入记录">
        <Table
          dataSource={recentRecords}
          columns={columns}
          rowKey="record_no"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
}
