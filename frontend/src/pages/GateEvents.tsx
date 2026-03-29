import { useEffect, useState } from "react";
import {
  Table,
  Tag,
  Button,
  Modal,
  Input,
  Select,
  Space,
  Typography,
} from "antd";
import { api } from "../api/client";
import type { GateEvent } from "../types";
import dayjs from "dayjs";

export default function GateEvents() {
  const [events, setEvents] = useState<GateEvent[]>([]);
  const [reviewing, setReviewing] = useState<GateEvent | null>(null);
  const [correctedPlate, setCorrectedPlate] = useState("");
  const [filterPlate, setFilterPlate] = useState("");
  const [filterStatus, setFilterStatus] = useState<string | undefined>();

  const fetchEvents = async () => {
    const params: Record<string, string> = {};
    if (filterPlate) params.plate = filterPlate;
    if (filterStatus) params.review_status = filterStatus;
    const resp = await api.get("/gate-events", { params });
    setEvents(resp.data);
  };

  useEffect(() => {
    fetchEvents();
  }, [filterPlate, filterStatus]);

  const handleReview = async (action: "confirm" | "reject") => {
    if (!reviewing) return;
    await api.patch(`/gate-events/${reviewing.id}/review`, {
      plate_number: correctedPlate,
      action,
    });
    setReviewing(null);
    fetchEvents();
  };

  const reviewStatusMap: Record<string, [string, string]> = {
    auto_confirmed: ["已自动确认", "blue"],
    pending_review: ["待审核", "orange"],
    manually_confirmed: ["人工确认", "green"],
    rejected: ["已拒绝", "red"],
  };

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
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "置信度",
      dataIndex: "confidence_score",
      key: "confidence_score",
      render: (s: number | null) =>
        s != null ? `${(s * 100).toFixed(1)}%` : "-",
    },
    {
      title: "状态",
      dataIndex: "review_status",
      key: "review_status",
      render: (s: string) => {
        const [label, color] = reviewStatusMap[s] || [s, "default"];
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: GateEvent) =>
        record.review_status === "pending_review" ? (
          <Button
            size="small"
            type="link"
            onClick={() => {
              setReviewing(record);
              setCorrectedPlate(record.plate_number);
            }}
          >
            审核
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="车牌搜索"
          onSearch={setFilterPlate}
          allowClear
          style={{ width: 200 }}
        />
        <Select
          placeholder="审核状态"
          allowClear
          style={{ width: 160 }}
          onChange={setFilterStatus}
        >
          <Select.Option value="pending_review">待审核</Select.Option>
          <Select.Option value="auto_confirmed">自动确认</Select.Option>
          <Select.Option value="manually_confirmed">人工确认</Select.Option>
          <Select.Option value="rejected">已拒绝</Select.Option>
        </Select>
        <Button
          onClick={() => {
            const params = new URLSearchParams();
            if (filterPlate) params.set("plate", filterPlate);
            window.open(
              `http://localhost:8000/gate-events/export?${params.toString()}`
            );
          }}
        >
          导出 Excel
        </Button>
      </Space>
      <Table
        dataSource={events}
        columns={columns}
        rowKey="id"
        size="small"
        rowClassName={(r) =>
          r.review_status === "pending_review" ? "table-row-warning" : ""
        }
      />

      <Modal
        title="审核出入记录"
        open={!!reviewing}
        onCancel={() => setReviewing(null)}
        footer={[
          <Button key="reject" danger onClick={() => handleReview("reject")}>
            拒绝
          </Button>,
          <Button
            key="confirm"
            type="primary"
            onClick={() => handleReview("confirm")}
          >
            确认
          </Button>,
        ]}
      >
        {reviewing && (
          <div>
            <p>
              识别车牌：
              <Typography.Text code>{reviewing.plate_number}</Typography.Text>
            </p>
            <p>
              置信度：
              {reviewing.confidence_score
                ? `${(reviewing.confidence_score * 100).toFixed(1)}%`
                : "-"}
            </p>
            <p>修正车牌：</p>
            <Input
              value={correctedPlate}
              onChange={(e) => setCorrectedPlate(e.target.value)}
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
