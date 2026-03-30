import { useState } from "react";
import {
  DatePicker, Select, Button, Card, Row, Col, Statistic,
  Table, Tabs, Space, Typography,
} from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { api } from "../api/client";
import type { TrafficReport, AlertReport } from "../types";
import dayjs, { type Dayjs } from "dayjs";

const { RangePicker } = DatePicker;

export default function Reports() {
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(7, "day"),
    dayjs(),
  ]);
  const [granularity, setGranularity] = useState("day");
  const [trafficData, setTrafficData] = useState<TrafficReport | null>(null);
  const [alertData, setAlertData] = useState<AlertReport | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = {
        start_date: dateRange[0].format("YYYY-MM-DD"),
        end_date: dateRange[1].format("YYYY-MM-DD"),
        granularity,
      };
      const [tResp, aResp] = await Promise.all([
        api.get("/reports/traffic", { params }),
        api.get("/reports/alerts", { params }),
      ]);
      setTrafficData(tResp.data);
      setAlertData(aResp.data);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    const p = new URLSearchParams({
      start_date: dateRange[0].format("YYYY-MM-DD"),
      end_date: dateRange[1].format("YYYY-MM-DD"),
      format: "excel",
    });
    window.open(`/api/reports/export?${p.toString()}`, "_blank");
  };

  const alertTypeLabels: Record<string, string> = {
    long_stay: "长时间在厂",
    pending_review: "低置信度待审",
    path_deviation: "路径偏离",
  };

  const alertColumns = [
    {
      title: "报警类型",
      dataIndex: "type",
      render: (t: string) => alertTypeLabels[t] ?? t,
    },
    { title: "次数", dataIndex: "count" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>报表中心</Typography.Title>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>导出 Excel</Button>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <RangePicker
          value={dateRange}
          onChange={(v) => v && setDateRange(v as [Dayjs, Dayjs])}
          presets={[
            { label: "今日", value: [dayjs(), dayjs()] },
            { label: "本周", value: [dayjs().startOf("week"), dayjs()] },
            { label: "本月", value: [dayjs().startOf("month"), dayjs()] },
          ]}
        />
        <Select
          value={granularity}
          onChange={setGranularity}
          options={[
            { value: "day", label: "按天" },
            { value: "week", label: "按周" },
            { value: "month", label: "按月" },
          ]}
          style={{ width: 100 }}
        />
        <Button type="primary" onClick={fetchReports} loading={loading}>查询</Button>
      </Space>

      {trafficData && (
        <Tabs
          items={[
            {
              key: "traffic",
              label: "进出流量",
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="总进场次数" value={trafficData.total_entries} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="总出场次数" value={trafficData.total_exits} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="平均在厂时长"
                          value={trafficData.avg_stay_duration_minutes ?? "N/A"}
                          suffix={trafficData.avg_stay_duration_minutes != null ? "分钟" : ""}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="活跃报警"
                          value={alertData?.total_active ?? 0}
                          valueStyle={{ color: alertData && alertData.total_active > 0 ? "#cf1322" : undefined }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Card title="进出趋势" style={{ marginBottom: 24 }}>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={trafficData.by_day}>
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="entries" name="进场" stroke="#52c41a" />
                        <Line type="monotone" dataKey="exits" name="出场" stroke="#f5222d" />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>
                </div>
              ),
            },
            {
              key: "alerts",
              label: "报警汇总",
              children: alertData ? (
                <div>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="待处理报警"
                          value={alertData.total_active}
                          valueStyle={{ color: "#cf1322" }}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="已解决报警"
                          value={alertData.total_resolved}
                          valueStyle={{ color: "#52c41a" }}
                        />
                      </Card>
                    </Col>
                  </Row>
                  <Card title="报警类型分布">
                    <Table
                      dataSource={alertData.by_type}
                      columns={alertColumns}
                      rowKey="type"
                      pagination={false}
                    />
                  </Card>
                </div>
              ) : null,
            },
          ]}
        />
      )}

      {!trafficData && !loading && (
        <div style={{ textAlign: "center", padding: "48px 0", color: "#9ca3af" }}>
          请选择时间范围并点击查询
        </div>
      )}
    </div>
  );
}
