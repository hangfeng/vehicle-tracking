import { Layout, Menu } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  CarOutlined,
  AlertOutlined,
  SwapOutlined,
  UserOutlined,
  BarChartOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";

const { Sider, Content, Header } = Layout;

const roleLabels = {
  system_admin: "系统管理员",
  group_admin: "集团管理员",
  factory_manager: "厂区管理员",
  operator: "操作员",
} as const;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, tokenRole, authError, logout } = useAuthStore();
  const effectiveRole = user?.role ?? tokenRole;

  const allItems = [
    { key: "/", icon: <DashboardOutlined />, label: "实时看板", roles: ["system_admin", "group_admin", "factory_manager", "operator"] },
    { key: "/gate-events", icon: <SwapOutlined />, label: "出入管理", roles: ["system_admin", "group_admin", "factory_manager", "operator"] },
    { key: "/vehicles", icon: <CarOutlined />, label: "车辆管理", roles: ["system_admin", "group_admin", "factory_manager", "operator"] },
    { key: "/alerts", icon: <AlertOutlined />, label: "报警中心", roles: ["system_admin", "group_admin", "factory_manager", "operator"] },
    { key: "/users", icon: <UserOutlined />, label: "用户管理", roles: ["system_admin", "group_admin", "factory_manager"] },
    { key: "/reports", icon: <BarChartOutlined />, label: "报表中心", roles: ["system_admin", "group_admin", "factory_manager", "operator"] },
    { key: "/settings", icon: <SettingOutlined />, label: "系统设置", roles: ["system_admin", "group_admin", "factory_manager"] },
  ];

  const menuItems = allItems
    .filter(item => !effectiveRole || item.roles.includes(effectiveRole))
    .map(({ key, icon, label }) => ({ key, icon, label }));

  const identityText = user
    ? `${user.name} · ${roleLabels[user.role]}`
    : effectiveRole
      ? `当前用户信息未同步 · ${roleLabels[effectiveRole]}`
      : "未识别登录身份";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={200} theme="dark">
        <div style={{ color: "#fff", padding: "16px", fontWeight: "bold", fontSize: 16 }}>
          车辆管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: "#fff",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #f0f0f0",
        }}>
          <span style={{ color: "#475569" }}>
            {identityText}
            {authError ? "（用户资料同步失败）" : ""}
          </span>
          <span
            style={{ cursor: "pointer", color: "#6b7280" }}
            onClick={logout}
          >
            退出登录
          </span>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
