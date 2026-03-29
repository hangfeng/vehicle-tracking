import { useEffect, useState, useRef } from "react";
import { Row, Col, Statistic, Card, Table, Tag } from "antd";
import {
  CarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  AlertOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { api } from "../api/client";
import type { DashboardStats, GateEvent } from "../types";
import { useAuthStore } from "../store/auth";
import dayjs from "dayjs";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentEvents, setRecentEvents] = useState<GateEvent[]>([]);
  const { user } = useAuthStore();
  const wsRef = useRef<WebSocket | null>(null);

  const fetchData = async () => {
    try {
      const [statsRes, eventsRes] = await Promise.all([
        api.get("/dashboard/stats"),
        api.get("/gate-events?limit=10"),
      ]);
      setStats(statsRes.data);
      setRecentEvents(eventsRes.data);
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

  const columns = [
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    {
      title: "方向",
      dataIndex: "direction",
      key: "direction",
      render: (d: string) => (
        <Tag color={d === "entry" ? "green" : "red"}>
          {d === "entry" ? "入场" : "出场"}
        </Tag>
      ),
    },
    {
      title: "时间",
      dataIndex: "captured_at",
      key: "captured_at",
      render: (t: string) => dayjs(t).format("HH:mm:ss"),
    },
    {
      title: "状态",
      dataIndex: "review_status",
      key: "review_status",
      render: (s: string) =>
        s === "pending_review" ? (
          <Tag color="orange">待审核</Tag>
        ) : (
          <Tag color="blue">已确认</Tag>
        ),
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
          dataSource={recentEvents}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
}
