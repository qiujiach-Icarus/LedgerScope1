import React, { useState } from 'react';
import { Layout, Menu, Badge, Avatar, Space, Input, Tooltip } from 'antd';
import { 
  LayoutDashboard, 
  UploadCloud, 
  FileText, 
  SearchCode,
  Settings,
  Bell,
  Search,
  User,
  ShieldCheck,
  Target
} from 'lucide-react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { key: '/',        icon: <LayoutDashboard size={18} />, label: '总览仪表盘' },
    { key: '/upload',  icon: <UploadCloud size={18} />,    label: '账本上传' },
    { key: '/vouchers',icon: <FileText size={18} />,       label: '凭证清单' },
    { key: '/explain', icon: <SearchCode size={18} />,     label: '可解释分析' },
    { key: '/attribution', icon: <Target size={18} />,    label: '风险分析归因' },
    { key: '/settings',icon: <Settings size={18} />,       label: '系统设置' },
  ];

  return (
    <Layout style={{ minHeight: '100vh', background: '#0a0e17' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={(value) => setCollapsed(value)}
        theme="dark"
        style={{ 
          background: '#111827', 
          borderRight: '1px solid #1f2937',
          position: 'fixed',
          height: '100vh',
          left: 0,
          zIndex: 100
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          padding: '0 20px', 
          color: '#06b6d4', 
          fontWeight: 'bold', 
          fontSize: 16,
          gap: 10
        }}>
          <ShieldCheck size={22} color="#06b6d4" />
          {!collapsed && '智能财务审计平台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent', border: 'none' }}
        />
        <div style={{ position: 'absolute', bottom: 20, width: '100%', padding: '0 16px', fontSize: 12, color: '#9ca3af' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} />
            {!collapsed && '后端服务 · 运行中'}
          </div>
        </div>
      </Sider>
      
      <Layout style={{ marginLeft: collapsed ? 80 : 200, background: 'transparent' }}>
        <Header style={{ 
          background: '#111827', 
          padding: '0 24px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderBottom: '1px solid #1f2937',
          position: 'sticky',
          top: 0,
          zIndex: 99
        }}>
          <Input 
            prefix={<Search size={16} color="#9ca3af" />}
            placeholder="搜索凭证号、科目、摘要..."
            style={{ width: 320, background: '#1f2937', border: 'none', color: '#fff' }}
          />
          <Space size={24}>
            <Tooltip title="系统通知">
              <Badge count={3} size="small">
                <Bell size={20} color="#9ca3af" style={{ cursor: 'pointer' }} />
              </Badge>
            </Tooltip>
            <Space size={8} style={{ cursor: 'pointer' }}>
              <Avatar icon={<User size={16} />} size="small" style={{ background: '#06b6d4' }} />
              <span style={{ color: '#fff' }}>审计管理员</span>
            </Space>
          </Space>
        </Header>
        
        <Content style={{ padding: '24px', color: '#fff', minHeight: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
