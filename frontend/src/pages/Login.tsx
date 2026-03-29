import { Form, Input, Button, Card, message } from "antd";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function Login() {
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const onFinish = async (values: { phone: string; password: string }) => {
    try {
      await login(values.phone, values.password);
      navigate("/");
    } catch {
      message.error("手机号或密码错误");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card title="厂区车辆管理系统" style={{ width: 360 }}>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item
            name="phone"
            label="手机号"
            rules={[{ required: true }]}
          >
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
