import { useEffect, useState } from "react";
import {
  Button,
  DatePicker,
  Input,
  Radio,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
} from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import type {
  AccessDetailRow,
  CheckPoint,
  CheckpointEventBusinessType,
  CheckpointEventSource,
  Department,
  UserDetailRow,
  User,
  VehicleDetailRow,
} from "../types";
import dayjs, { type Dayjs } from "dayjs";

const { RangePicker } = DatePicker;

const accessColumnOptions = [
  { value: "serial_no", label: "流水号" },
  { value: "event_time", label: "时间" },
  { value: "plate_number", label: "车牌" },
  { value: "direction", label: "方向" },
  { value: "checkpoint_name", label: "节点" },
  { value: "department_name", label: "部门" },
  { value: "business_type", label: "业务类型" },
  { value: "document_no", label: "单号" },
  { value: "source", label: "来源" },
  { value: "entered_by_user_name", label: "操作用户" },
  { value: "note", label: "备注" },
] as const;

const defaultAccessColumns = accessColumnOptions.map((item) => item.value);

const businessTypeLabels: Record<CheckpointEventBusinessType, string> = {
  delivery: "送货",
  shipment: "出货",
  other: "其他",
};

const sourceLabels: Record<CheckpointEventSource, string> = {
  manual: "人工录入",
  ai: "AI识别",
  import: "导入",
};

export default function Reports() {
  const [accessRows, setAccessRows] = useState<AccessDetailRow[]>([]);
  const [accessLoading, setAccessLoading] = useState(false);
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [vehicleRows, setVehicleRows] = useState<VehicleDetailRow[]>([]);
  const [vehicleLoading, setVehicleLoading] = useState(false);
  const [vehicleFilters, setVehicleFilters] = useState({
    serial_no: "",
    plate_number: "",
    status: undefined as string | undefined,
    company: "",
  });
  const [userRows, setUserRows] = useState<UserDetailRow[]>([]);
  const [userLoading, setUserLoading] = useState(false);
  const [userFilters, setUserFilters] = useState({
    serial_no: "",
    name: "",
    phone: "",
    role: undefined as string | undefined,
    department_id: undefined as string | undefined,
  });
  const [selectedAccessColumns, setSelectedAccessColumns] = useState<string[]>(defaultAccessColumns);
  const [accessDateMode, setAccessDateMode] = useState<"single" | "range">("range");
  const [accessSingleDate, setAccessSingleDate] = useState<Dayjs>(dayjs());
  const [accessDateRange, setAccessDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(7, "day"),
    dayjs(),
  ]);
  const [accessFilters, setAccessFilters] = useState({
    serial_no: "",
    plate_number: "",
    direction: undefined as string | undefined,
    checkpoint_id: undefined as string | undefined,
    department_id: undefined as string | undefined,
    entered_by_user_id: undefined as string | undefined,
    business_type: undefined as string | undefined,
    document_no: "",
    source: undefined as string | undefined,
  });

  useEffect(() => {
    api.get("/checkpoints").then((resp) => setCheckpoints(resp.data)).catch(() => {});
    api.get("/departments").then((resp) => setDepartments(resp.data)).catch(() => {});
    api.get("/users").then((resp) => setUsers(resp.data)).catch(() => {});
  }, []);

  const fetchAccessDetails = async () => {
    setAccessLoading(true);
    try {
      const accessParams = accessDateMode === "single"
        ? {
            start_date: accessSingleDate.format("YYYY-MM-DD"),
            end_date: accessSingleDate.format("YYYY-MM-DD"),
          }
        : {
            start_date: accessDateRange[0].format("YYYY-MM-DD"),
            end_date: accessDateRange[1].format("YYYY-MM-DD"),
          };
      const params = {
        ...accessParams,
        ...accessFilters,
      };
      const resp = await api.get("/reports/access-details", { params });
      setAccessRows(resp.data);
    } finally {
      setAccessLoading(false);
    }
  };

  const exportAccessDetails = async () => {
    const accessParams = accessDateMode === "single"
      ? {
          start_date: accessSingleDate.format("YYYY-MM-DD"),
          end_date: accessSingleDate.format("YYYY-MM-DD"),
        }
      : {
          start_date: accessDateRange[0].format("YYYY-MM-DD"),
          end_date: accessDateRange[1].format("YYYY-MM-DD"),
        };
    const resp = await api.get("/reports/access-details/export", {
      params: { ...accessParams, ...accessFilters },
      responseType: "blob",
    });
    const blobUrl = window.URL.createObjectURL(new Blob([resp.data]));
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `access_detail_${accessParams.start_date}_${accessParams.end_date}.xlsx`;
    link.click();
    window.URL.revokeObjectURL(blobUrl);
  };

  const fetchVehicleDetails = async () => {
    setVehicleLoading(true);
    try {
      const resp = await api.get("/reports/vehicle-details", { params: vehicleFilters });
      setVehicleRows(resp.data);
    } finally {
      setVehicleLoading(false);
    }
  };

  const fetchUserDetails = async () => {
    setUserLoading(true);
    try {
      const resp = await api.get("/reports/user-details", { params: userFilters });
      setUserRows(resp.data);
    } finally {
      setUserLoading(false);
    }
  };

  const accessColumnMap: Record<string, object> = {
    serial_no: { title: "流水号", dataIndex: "serial_no", render: (value: string | null) => value || "—" },
    event_time: { title: "时间", dataIndex: "event_time", render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm:ss") },
    plate_number: { title: "车牌", dataIndex: "plate_number" },
    direction: { title: "方向", dataIndex: "direction", render: (value: string) => value === "entry" ? "入场" : "出场" },
    checkpoint_name: { title: "节点", dataIndex: "checkpoint_name" },
    department_name: { title: "部门", dataIndex: "department_name", render: (value: string | null) => value || "—" },
    business_type: { title: "业务类型", dataIndex: "business_type", render: (value: CheckpointEventBusinessType) => businessTypeLabels[value] || value },
    document_no: { title: "单号", dataIndex: "document_no", render: (value: string | null) => value || "—" },
    source: { title: "来源", dataIndex: "source", render: (value: CheckpointEventSource) => sourceLabels[value] || value },
    entered_by_user_name: { title: "操作用户", dataIndex: "entered_by_user_name", render: (value: string | null) => value || "—" },
    note: { title: "备注", dataIndex: "note", render: (value: string | null) => value || "—" },
  };

  const accessColumns = selectedAccessColumns.map((key) => ({
    key,
    ...accessColumnMap[key],
  }));
  const vehicleColumns = [
    { title: "流水号", dataIndex: "serial_no", render: (value: string | null) => value || "—" },
    { title: "车牌", dataIndex: "plate_number" },
    { title: "车辆类型", dataIndex: "vehicle_type" },
    { title: "所属公司", dataIndex: "company", render: (value: string | null) => value || "—" },
    { title: "联系人", dataIndex: "contact_name", render: (value: string | null) => value || "—" },
    { title: "联系电话", dataIndex: "contact_phone", render: (value: string | null) => value || "—" },
    { title: "状态", dataIndex: "status", render: (value: string) => value === "in_factory" ? "在厂" : value === "out" ? "离厂" : "未知" },
    { title: "最后记录时间", dataIndex: "last_seen_at", render: (value: string | null) => value ? dayjs(value).format("YYYY-MM-DD HH:mm:ss") : "—" },
    { title: "备注", dataIndex: "note", render: (value: string | null) => value || "—" },
  ];
  const userColumns = [
    { title: "流水号", dataIndex: "serial_no", render: (value: string | null) => value || "—" },
    { title: "姓名", dataIndex: "name" },
    { title: "手机号", dataIndex: "phone" },
    { title: "角色", dataIndex: "role", render: (value: string) => value === "group_admin" ? "集团管理员" : value === "factory_manager" ? "厂区管理员" : value === "operator" ? "操作员" : "系统管理员" },
    { title: "厂区", dataIndex: "factory_name", render: (value: string | null) => value || "—" },
    { title: "部门", dataIndex: "department_name", render: (value: string | null) => value || "—" },
    { title: "状态", dataIndex: "is_active", render: (value: boolean) => value ? "启用" : "停用" },
    { title: "创建时间", dataIndex: "created_at", render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm:ss") },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>报表中心</Typography.Title>
      </div>

      <Tabs
        items={[
          {
            key: "access-details",
            label: "出入管理明细",
            children: (
              <div>
                <Space style={{ marginBottom: 16 }} wrap>
                  <Radio.Group
                    value={accessDateMode}
                    onChange={(e) => setAccessDateMode(e.target.value)}
                    optionType="button"
                    buttonStyle="solid"
                  >
                    <Radio.Button value="single">按某一天查询</Radio.Button>
                    <Radio.Button value="range">按时间段查询</Radio.Button>
                  </Radio.Group>
                  {accessDateMode === "single" ? (
                    <DatePicker
                      value={accessSingleDate}
                      onChange={(value) => value && setAccessSingleDate(value)}
                    />
                  ) : (
                    <RangePicker
                      value={accessDateRange}
                      onChange={(value) => value && setAccessDateRange(value as [Dayjs, Dayjs])}
                    />
                  )}
                </Space>

                <Space style={{ marginBottom: 16 }} wrap>
                  <Input
                    placeholder="流水号"
                    style={{ width: 220 }}
                    value={accessFilters.serial_no}
                    onChange={(e) => setAccessFilters((prev) => ({ ...prev, serial_no: e.target.value }))}
                  />
                  <Input
                    placeholder="车牌"
                    style={{ width: 180 }}
                    value={accessFilters.plate_number}
                    onChange={(e) => setAccessFilters((prev) => ({ ...prev, plate_number: e.target.value }))}
                  />
                  <Select
                    placeholder="方向"
                    allowClear
                    style={{ width: 120 }}
                    value={accessFilters.direction}
                    onChange={(value) => setAccessFilters((prev) => ({ ...prev, direction: value }))}
                    options={[
                      { value: "entry", label: "入场" },
                      { value: "exit", label: "出场" },
                    ]}
                  />
                  <Select
                    placeholder="节点"
                    allowClear
                    style={{ width: 180 }}
                    value={accessFilters.checkpoint_id}
                    onChange={(value) => setAccessFilters((prev) => ({ ...prev, checkpoint_id: value }))}
                    options={checkpoints.map((item) => ({ value: item.id, label: item.name }))}
                  />
                  <Select
                    placeholder="部门"
                    allowClear
                    style={{ width: 180 }}
                    value={accessFilters.department_id}
                    onChange={(value) => setAccessFilters((prev) => ({ ...prev, department_id: value }))}
                    options={departments.map((item) => ({ value: item.id, label: item.name }))}
                  />
                  <Select
                    placeholder="操作用户"
                    allowClear
                    style={{ width: 180 }}
                    value={accessFilters.entered_by_user_id}
                    onChange={(value) => setAccessFilters((prev) => ({ ...prev, entered_by_user_id: value }))}
                    options={users.map((item) => ({ value: item.id, label: item.name }))}
                  />
                  <Select
                    placeholder="业务类型"
                    allowClear
                    style={{ width: 140 }}
                    value={accessFilters.business_type}
                    onChange={(value) => setAccessFilters((prev) => ({ ...prev, business_type: value }))}
                    options={[
                      { value: "delivery", label: "送货" },
                      { value: "shipment", label: "出货" },
                      { value: "other", label: "其他" },
                    ]}
                  />
                  <Input
                    placeholder="单号"
                    style={{ width: 180 }}
                    value={accessFilters.document_no}
                    onChange={(e) => setAccessFilters((prev) => ({ ...prev, document_no: e.target.value }))}
                  />
                  <Select
                    placeholder="来源"
                    allowClear
                    style={{ width: 140 }}
                    value={accessFilters.source}
                    onChange={(value) => setAccessFilters((prev) => ({ ...prev, source: value }))}
                    options={[
                      { value: "manual", label: "人工录入" },
                      { value: "ai", label: "AI识别" },
                      { value: "import", label: "导入" },
                    ]}
                  />
                </Space>

                <Space style={{ marginBottom: 16 }} wrap>
                  <Select
                    mode="multiple"
                    style={{ minWidth: 520 }}
                    value={selectedAccessColumns}
                    onChange={setSelectedAccessColumns}
                    options={accessColumnOptions.map((item) => ({ value: item.value, label: item.label }))}
                    placeholder="选择显示字段"
                  />
                  <Button type="primary" onClick={fetchAccessDetails} loading={accessLoading}>查询明细</Button>
                  <Button icon={<DownloadOutlined />} onClick={exportAccessDetails}>导出当前结果</Button>
                </Space>

                <Table
                  dataSource={accessRows}
                  columns={accessColumns}
                  rowKey={(row) => `${row.serial_no ?? row.event_time}-${row.plate_number}`}
                  loading={accessLoading}
                  scroll={{ x: 1400 }}
                />
              </div>
            ),
          },
          {
            key: "vehicle-details",
            label: "车辆明细",
            children: (
              <div>
                <Space style={{ marginBottom: 16 }} wrap>
                  <Input placeholder="流水号" style={{ width: 220 }} value={vehicleFilters.serial_no} onChange={(e) => setVehicleFilters((prev) => ({ ...prev, serial_no: e.target.value }))} />
                  <Input placeholder="车牌" style={{ width: 180 }} value={vehicleFilters.plate_number} onChange={(e) => setVehicleFilters((prev) => ({ ...prev, plate_number: e.target.value }))} />
                  <Select
                    placeholder="状态"
                    allowClear
                    style={{ width: 140 }}
                    value={vehicleFilters.status}
                    onChange={(value) => setVehicleFilters((prev) => ({ ...prev, status: value }))}
                    options={[
                      { value: "in_factory", label: "在厂" },
                      { value: "out", label: "离厂" },
                      { value: "unknown", label: "未知" },
                    ]}
                  />
                  <Input placeholder="所属公司" style={{ width: 180 }} value={vehicleFilters.company} onChange={(e) => setVehicleFilters((prev) => ({ ...prev, company: e.target.value }))} />
                  <Button type="primary" onClick={fetchVehicleDetails} loading={vehicleLoading}>查询车辆</Button>
                </Space>
                <Table dataSource={vehicleRows} columns={vehicleColumns} rowKey={(row) => `${row.serial_no ?? row.plate_number}`} loading={vehicleLoading} scroll={{ x: 1200 }} />
              </div>
            ),
          },
          {
            key: "user-details",
            label: "用户明细",
            children: (
              <div>
                <Space style={{ marginBottom: 16 }} wrap>
                  <Input placeholder="流水号" style={{ width: 220 }} value={userFilters.serial_no} onChange={(e) => setUserFilters((prev) => ({ ...prev, serial_no: e.target.value }))} />
                  <Input placeholder="姓名" style={{ width: 180 }} value={userFilters.name} onChange={(e) => setUserFilters((prev) => ({ ...prev, name: e.target.value }))} />
                  <Input placeholder="手机号" style={{ width: 180 }} value={userFilters.phone} onChange={(e) => setUserFilters((prev) => ({ ...prev, phone: e.target.value }))} />
                  <Select
                    placeholder="角色"
                    allowClear
                    style={{ width: 150 }}
                    value={userFilters.role}
                    onChange={(value) => setUserFilters((prev) => ({ ...prev, role: value }))}
                    options={[
                      { value: "system_admin", label: "系统管理员" },
                      { value: "group_admin", label: "集团管理员" },
                      { value: "factory_manager", label: "厂区管理员" },
                      { value: "operator", label: "操作员" },
                    ]}
                  />
                  <Select
                    placeholder="部门"
                    allowClear
                    style={{ width: 180 }}
                    value={userFilters.department_id}
                    onChange={(value) => setUserFilters((prev) => ({ ...prev, department_id: value }))}
                    options={departments.map((item) => ({ value: item.id, label: item.name }))}
                  />
                  <Button type="primary" onClick={fetchUserDetails} loading={userLoading}>查询用户</Button>
                </Space>
                <Table dataSource={userRows} columns={userColumns} rowKey={(row) => `${row.serial_no ?? row.phone}`} loading={userLoading} scroll={{ x: 1200 }} />
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
