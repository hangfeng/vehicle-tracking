import { useEffect, useState, useRef } from "react";
import { Row, Col, Statistic, Card, Table, Tag, Space, DatePicker, Select, Button, Radio } from "antd";
import {
  CarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  AlertOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { api } from "../api/client";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { AlertReport, DashboardRecentAccessRecord, DashboardStats, TrafficReport } from "../types";
import { useAuthStore } from "../store/auth";
import dayjs, { type Dayjs } from "dayjs";

const { RangePicker } = DatePicker;

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentRecords, setRecentRecords] = useState<DashboardRecentAccessRecord[]>([]);
  const [trafficTrend, setTrafficTrend] = useState<TrafficReport | null>(null);
  const [alertData, setAlertData] = useState<AlertReport | null>(null);
  const [reportDateMode, setReportDateMode] = useState<"single" | "range">("range");
  const [reportSingleDate, setReportSingleDate] = useState<Dayjs>(dayjs());
  const [reportDateRange, setReportDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(6, "day"),
    dayjs(),
  ]);
  const [reportGranularity, setReportGranularity] = useState("day");
  const { user } = useAuthStore();
  const wsRef = useRef<WebSocket | null>(null);

  const fetchData = async () => {
    try {
      const reportParams = reportDateMode === "single"
        ? {
            start_date: reportSingleDate.format("YYYY-MM-DD"),
            end_date: reportSingleDate.format("YYYY-MM-DD"),
            granularity: reportGranularity,
          }
        : {
            start_date: reportDateRange[0].format("YYYY-MM-DD"),
            end_date: reportDateRange[1].format("YYYY-MM-DD"),
            granularity: reportGranularity,
          };
      const [statsRes, recordsRes, trendRes, alertRes] = await Promise.all([
        api.get("/dashboard/stats"),
        api.get("/dashboard/recent-access-records?limit=10"),
        api.get("/reports/traffic", { params: reportParams }),
        api.get("/reports/alerts", { params: { start_date: reportParams.start_date, end_date: reportParams.end_date } }),
      ]);
      setStats(statsRes.data);
      setRecentRecords(recordsRes.data);
      setTrafficTrend(trendRes.data);
      setAlertData(alertRes.data);
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
  }, [user, reportDateMode, reportSingleDate, reportDateRange, reportGranularity]);

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
  const alertTypeLabels: Record<string, string> = {
    long_stay: "长时间在厂",
    pending_review: "低置信度待审",
    path_deviation: "路径偏离",
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={5}>
          <Card>
            <Statistic
              title="在厂车辆"
              value={stats?.vehicles_in_factory ?? "-"}
              prefix={<CarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={5}>
          <Card>
            <Statistic
              title="今日入场"
              value={stats?.entries_today ?? "-"}
              prefix={<ArrowDownOutlined />}
              valueStyle={{ color: "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={5}>
          <Card>
            <Statistic
              title="今日出场"
              value={stats?.exits_today ?? "-"}
              prefix={<ArrowUpOutlined />}
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={5}>
          <Card>
            <Statistic
              title="待审核"
              value={stats?.pending_review_count ?? "-"}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: "#fa8c16" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
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
      <Card title="快捷报表" style={{ marginBottom: 24 }}>
        <Space style={{ marginBottom: 16 }} wrap>
          <Radio.Group
            value={reportDateMode}
            onChange={(e) => setReportDateMode(e.target.value)}
            optionType="button"
            buttonStyle="solid"
          >
            <Radio.Button value="single">按某一天</Radio.Button>
            <Radio.Button value="range">按时间段</Radio.Button>
          </Radio.Group>
          {reportDateMode === "single" ? (
            <DatePicker
              value={reportSingleDate}
              onChange={(value) => value && setReportSingleDate(value)}
            />
          ) : (
            <RangePicker
              value={reportDateRange}
              onChange={(value) => value && setReportDateRange(value as [Dayjs, Dayjs])}
            />
          )}
          <Select
            value={reportGranularity}
            onChange={setReportGranularity}
            options={[
              { value: "day", label: "按天" },
              { value: "week", label: "按周" },
              { value: "month", label: "按月" },
            ]}
            style={{ width: 120 }}
          />
          <Button type="primary" onClick={fetchData}>查询</Button>
        </Space>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trafficTrend?.by_day ?? []}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="entries" name="进场" stroke="#52c41a" />
            <Line type="monotone" dataKey="exits" name="出场" stroke="#f5222d" />
          </LineChart>
        </ResponsiveContainer>
      </Card>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="近 7 日进出汇总">
            <Table
              dataSource={trafficTrend?.by_day ?? []}
              rowKey="date"
              pagination={false}
              size="small"
              scroll={{ x: 420 }}
              columns={[
                { title: "日期", dataIndex: "date" },
                { title: "进场次数", dataIndex: "entries" },
                { title: "出场次数", dataIndex: "exits" },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="近 7 日报警汇总">
            <Table
              dataSource={alertData?.by_type ?? []}
              rowKey="type"
              pagination={false}
              size="small"
              scroll={{ x: 360 }}
              columns={[
                { title: "报警类型", dataIndex: "type", render: (value: string) => alertTypeLabels[value] ?? value },
                { title: "次数", dataIndex: "count" },
              ]}
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
          scroll={{ x: 1100 }}
        />
      </Card>
    </div>
  );
}
