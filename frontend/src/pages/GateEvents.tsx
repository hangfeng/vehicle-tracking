import { useEffect, useState } from "react";
import {
  AutoComplete,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";
import type { CheckPoint, CheckpointEvent, Department, Factory, Vehicle } from "../types";
import dayjs from "dayjs";

const sourceLabels: Record<string, string> = {
  manual: "人工录入",
  ai: "AI识别",
  import: "导入",
};

export default function GateEvents() {
  const { user: me } = useAuthStore();
  const [events, setEvents] = useState<CheckpointEvent[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [myFactory, setMyFactory] = useState<Factory | null>(null);
  const [inFactoryVehicles, setInFactoryVehicles] = useState<Vehicle[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [filterPlate, setFilterPlate] = useState("");
  const [filterCheckpointId, setFilterCheckpointId] = useState<string | undefined>();
  const [filterDepartmentId, setFilterDepartmentId] = useState<string | undefined>();
  const [form] = Form.useForm();
  const selectedDirection = Form.useWatch("direction", form);
  const selectedBusinessType = Form.useWatch("business_type", form);

  const fetchMeta = async () => {
    const [checkpointResp, departmentResp] = await Promise.all([
      api.get("/checkpoints"),
      api.get("/departments"),
    ]);
    setCheckpoints(checkpointResp.data);
    setDepartments(departmentResp.data);
  };

  const fetchInFactoryVehicles = async () => {
    const resp = await api.get("/vehicles/in-factory-candidates");
    setInFactoryVehicles(resp.data);
  };

  const fetchEvents = async () => {
    const params: Record<string, string> = {};
    if (filterPlate) params.plate = filterPlate;
    if (filterCheckpointId) params.checkpoint_id = filterCheckpointId;
    if (filterDepartmentId) params.department_id = filterDepartmentId;
    const resp = await api.get("/checkpoint-events", { params });
    setEvents(resp.data);
  };

  useEffect(() => {
    fetchMeta().catch(() => {});
    fetchInFactoryVehicles().catch(() => {});
    if (me?.factory_id) {
      api.get<Factory>(`/factories/${me.factory_id}`).then(r => setMyFactory(r.data)).catch(() => {});
    }
  }, [me?.factory_id]);

  useEffect(() => {
    fetchEvents().catch(() => {});
  }, [filterPlate, filterCheckpointId, filterDepartmentId]);

  const checkpointMap = Object.fromEntries(checkpoints.map((item) => [item.id, item]));
  const departmentMap = Object.fromEntries(departments.map((item) => [item.id, item]));
  const vehicleOptions = inFactoryVehicles.map((item) => ({
    value: item.plate_number,
    label: `${item.plate_number} · ${item.company || "未登记"}`,
  }));

  // Operators can only record checkpoints belonging to their department;
  // factory_manager and above can record any checkpoint.
  const accessibleCheckpoints = me?.role === "operator" && me?.department_id
    ? checkpoints.filter(cp => cp.department_id === me.department_id)
    : checkpoints;
  const myDepartment = me?.department_id ? departments.find(d => d.id === me.department_id) : null;

  const handleCreate = async () => {
    const values = await form.validateFields();
    try {
      await api.post("/checkpoint-events", values);
      message.success("录入成功");
      setModalOpen(false);
      form.resetFields();
      fetchEvents();
      fetchInFactoryVehicles();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "录入失败");
    }
  };

  const columns = [
    {
      title: "流水号",
      dataIndex: "serial_no",
      render: (value: string | null) => value || "—",
    },
    {
      title: "时间",
      dataIndex: "event_time",
      render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm:ss"),
    },
    { title: "车牌", dataIndex: "plate_number" },
    {
      title: "方向",
      dataIndex: "direction",
      render: (value: string) => (
        <Tag color={value === "entry" ? "green" : "red"}>
          {value === "entry" ? "入场" : "出场"}
        </Tag>
      ),
    },
    {
      title: "节点",
      dataIndex: "checkpoint_id",
      render: (value: string) => checkpointMap[value]?.name || value,
    },
    {
      title: "部门",
      dataIndex: "department_id",
      render: (value: string | null) => (value ? departmentMap[value]?.name || value : "未设置"),
    },
    {
      title: "业务类型",
      dataIndex: "business_type",
      render: (value: string) => ({ delivery: "送货", shipment: "出货", other: "其他" }[value] || value),
    },
    {
      title: "单号",
      dataIndex: "document_no",
      render: (value: string | null) => value || "—",
    },
    {
      title: "来源",
      dataIndex: "source",
      render: (value: string) => sourceLabels[value] || value,
    },
    {
      title: "操作用户",
      dataIndex: "entered_by_user_name",
      render: (value: string | null, record: CheckpointEvent) => {
        if (value) return value;
        if (record.source === "ai") return "AI识别";
        return "—";
      },
    },
    {
      title: "备注",
      dataIndex: "note",
      render: (value: string | null) => value || "—",
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>出入管理</Typography.Title>
        <Button type="primary" onClick={() => setModalOpen(true)}>新增录入</Button>
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="车牌搜索"
          allowClear
          style={{ width: 220 }}
          onSearch={setFilterPlate}
        />
        <Select
          placeholder="筛选节点"
          allowClear
          style={{ width: 220 }}
          value={filterCheckpointId}
          onChange={setFilterCheckpointId}
          options={checkpoints.map((item) => ({ value: item.id, label: item.name }))}
        />
        <Select
          placeholder="筛选部门"
          allowClear
          style={{ width: 220 }}
          value={filterDepartmentId}
          onChange={setFilterDepartmentId}
          options={departments.map((item) => ({ value: item.id, label: item.name }))}
        />
      </Space>

      <Table dataSource={events} columns={columns} rowKey="id" scroll={{ x: 1400 }} />

      <Modal
        title="新增出入管理记录"
        open={modalOpen}
        width="min(680px, calc(100vw - 24px))"
        onOk={handleCreate}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="操作员">
            <span>{me?.name || "—"}</span>
          </Form.Item>
          {myFactory && (
            <Form.Item label="所属厂区">
              <span>{myFactory.name}</span>
            </Form.Item>
          )}
          {myDepartment && (
            <Form.Item label="所属部门">
              <span>{myDepartment.name}</span>
            </Form.Item>
          )}
          <Form.Item name="checkpoint_id" label="节点" rules={[{ required: true, message: "请选择节点" }]}>
            <Select
              placeholder="请选择节点"
              options={accessibleCheckpoints.map((item) => ({ value: item.id, label: item.name }))}
            />
          </Form.Item>
          <Form.Item name="direction" label="方向" rules={[{ required: true, message: "请选择方向" }]}>
            <Select options={[
              { value: "entry", label: "入场" },
              { value: "exit", label: "出场" },
            ]} />
          </Form.Item>
          <Form.Item
            name="plate_number"
            label="车牌"
            rules={[{ required: true, message: selectedDirection === "exit" ? "请选择在场车辆或手工输入车牌" : "请输入车牌" }]}
          >
            <AutoComplete
              placeholder={selectedDirection === "exit" ? "优先选择当前在场车辆，也可直接输入" : "选择历史车辆或直接输入新车牌"}
              options={vehicleOptions}
              filterOption={(inputValue, option) => String(option?.value || "").toLowerCase().includes(inputValue.toLowerCase())}
            />
          </Form.Item>
          <Form.Item name="business_type" label="业务类型" initialValue="other" rules={[{ required: true, message: "请选择业务类型" }]}>
            <Select options={[
              { value: "delivery", label: "送货" },
              { value: "shipment", label: "出货" },
              { value: "other", label: "其他" },
            ]} />
          </Form.Item>
          <Form.Item
            name="document_no"
            label="单号"
            rules={[
              {
                required: selectedBusinessType === "delivery" || selectedBusinessType === "shipment",
                message: "送货或出货记录必须填写单号",
              },
            ]}
          >
            <Input placeholder="可由扫描枪录入或手工填写" />
          </Form.Item>
          <Form.Item name="note" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
