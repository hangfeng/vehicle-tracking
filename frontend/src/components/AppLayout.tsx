import { Button, Drawer, Grid, Layout, Menu, Space } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  CarOutlined,
  AlertOutlined,
  SwapOutlined,
  UserOutlined,
  BarChartOutlined,
  SettingOutlined,
  MenuOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import { useAuthStore } from "../store/auth";

const { Sider, Content, Header } = Layout;
const { useBreakpoint } = Grid;

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
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [menuOpen, setMenuOpen] = useState(false);

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

  const renderedMenu = (
    <>
      <div style={{ color: "#fff", padding: "16px", fontWeight: "bold", fontSize: 16 }}>
        车辆管理
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => {
          navigate(key);
          setMenuOpen(false);
        }}
      />
    </>
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {isMobile ? (
        <Drawer
          title={null}
          placement="left"
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          closable={false}
          bodyStyle={{ padding: 0, background: "#001529" }}
          width={240}
        >
          {renderedMenu}
        </Drawer>
      ) : (
        <Sider width={200} theme="dark">
          {renderedMenu}
        </Sider>
      )}
      <Layout>
        <Header style={{
          background: "#fff",
          padding: isMobile ? "0 12px" : "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #f0f0f0",
          gap: 12,
        }}>
          <Space size={12} style={{ minWidth: 0, flex: 1, justifyContent: "space-between" }}>
            <Space size={12} style={{ minWidth: 0 }}>
              {isMobile && (
                <Button
                  type="text"
                  icon={<MenuOutlined />}
                  onClick={() => setMenuOpen(true)}
                />
              )}
              <span style={{ color: "#475569", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {identityText}
                {authError ? "（用户资料同步失败）" : ""}
              </span>
            </Space>
            <span
              style={{ cursor: "pointer", color: "#6b7280", flexShrink: 0 }}
              onClick={logout}
            >
              退出登录
            </span>
          </Space>
        </Header>
        <Content style={{ margin: isMobile ? 12 : 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
