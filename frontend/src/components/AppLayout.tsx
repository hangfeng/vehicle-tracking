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

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const allItems = [
    { key: "/", icon: <DashboardOutlined />, label: "实时看板", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/gate-events", icon: <SwapOutlined />, label: "出入记录", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/vehicles", icon: <CarOutlined />, label: "车辆管理", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/alerts", icon: <AlertOutlined />, label: "报警中心", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/users", icon: <UserOutlined />, label: "用户管理", roles: ["group_admin", "factory_manager"] },
    { key: "/reports", icon: <BarChartOutlined />, label: "报表中心", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/settings", icon: <SettingOutlined />, label: "系统设置", roles: ["group_admin", "factory_manager"] },
  ];

  const menuItems = allItems
    .filter(item => !user || item.roles.includes(user.role))
    .map(({ key, icon, label }) => ({ key, icon, label }));

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
            {user?.name} · {user?.role}
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
