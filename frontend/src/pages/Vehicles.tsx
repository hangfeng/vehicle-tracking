import { useEffect, useState } from "react";
import { Table, Tag, Button, Modal, Form, Input, message, Space, Upload } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { UploadProps } from "antd";
import { api } from "../api/client";
import type { Vehicle } from "../types";
import dayjs from "dayjs";

export default function Vehicles() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [adding, setAdding] = useState(false);
  const [form] = Form.useForm();

  const fetchVehicles = async () => {
    const resp = await api.get("/vehicles");
    setVehicles(resp.data);
  };

  useEffect(() => {
    fetchVehicles();
  }, []);

  const handleAdd = async (values: Record<string, string>) => {
    await api.post("/vehicles", values);
    message.success("车辆已添加");
    setAdding(false);
    form.resetFields();
    fetchVehicles();
  };

  const uploadProps: UploadProps = {
    accept: ".xlsx,.xls",
    showUploadList: false,
    customRequest: async ({ file, onSuccess, onError }) => {
      const formData = new FormData();
      formData.append("file", file as File);
      try {
        const resp = await api.post("/vehicles/import", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        const { created, skipped, errors } = resp.data;
        message.success(`导入完成：新增 ${created} 辆，跳过 ${skipped} 辆${errors.length ? `，${errors.length} 条错误` : ""}`);
        if (onSuccess) onSuccess(resp.data);
        fetchVehicles();
      } catch (err) {
        message.error("导入失败");
        if (onError) onError(err as Error);
      }
    },
  };

  const statusMap: Record<string, [string, string]> = {
    in_factory: ["在厂", "green"],
    out: ["离厂", "default"],
    unknown: ["未知", "orange"],
  };

  const columns = [
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    { title: "类型", dataIndex: "vehicle_type", key: "vehicle_type" },
    {
      title: "所属公司",
      dataIndex: "company",
      key: "company",
      render: (v: string | null) => v || "-",
    },
    {
      title: "联系人",
      dataIndex: "contact_name",
      key: "contact_name",
      render: (v: string | null) => v || "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => {
        const [label, color] = statusMap[s] || [s, "default"];
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: "最后记录",
      dataIndex: "last_seen_at",
      key: "last_seen_at",
      render: (t: string | null) =>
        t ? dayjs(t).format("MM-DD HH:mm") : "-",
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          onClick={() => setAdding(true)}
        >
          添加车辆
        </Button>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />}>导入 Excel</Button>
        </Upload>
      </Space>
      <Table dataSource={vehicles} columns={columns} rowKey="id" size="small" />
      <Modal
        title="添加车辆"
        open={adding}
        onCancel={() => setAdding(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleAdd} layout="vertical">
          <Form.Item
            name="plate_number"
            label="车牌号"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="vehicle_type" label="车辆类型">
            <Input placeholder="truck" />
          </Form.Item>
          <Form.Item name="company" label="所属公司">
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label="联系人">
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label="联系电话">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
