import React, { useEffect, useState } from 'react';
import { Card, Typography, Form, Input, Button, Space, Tag, message, Alert } from 'antd';
import { KeyRound, Save, ShieldCheck } from 'lucide-react';
import axios from 'axios';

const { Title, Text } = Typography;

const Settings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyConfigured, setKeyConfigured] = useState(false);
  const [form] = Form.useForm();

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/settings/llm');
      setKeyConfigured(res.data.api_key_set);
      form.setFieldsValue({
        api_key: '',
        base_url: res.data.base_url,
        model: res.data.model,
      });
    } catch {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const onSave = async (values: any) => {
    setSaving(true);
    try {
      await axios.post('/api/settings/llm', values);
      message.success('DeepSeek 配置已保存并生效');
      await loadSettings();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldCheck size={24} color="#06b6d4" />
          系统设置 · DeepSeek 大模型
        </Title>
        <Text type="secondary" style={{ marginTop: 6, display: 'block' }}>
          在这里填写你自己的 DeepSeek API Key，配置保存后立即生效，无需重启后端。
        </Text>
      </div>

      <Card
        style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, maxWidth: 640 }}
        title={
          <span style={{ color: '#fff' }}>
            <KeyRound size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} />
            DeepSeek API 配置
          </span>
        }
      >
        {keyConfigured && (
          <Alert
            type="success"
            showIcon
            style={{ marginBottom: 16, background: '#052e16', border: '1px solid #166534', borderRadius: 8 }}
            message={<span style={{ color: '#bbf7d0' }}>已配置 API Key</span>}
          />
        )}

        <Form form={form} layout="vertical" onFinish={onSave}>
          <Form.Item
            name="api_key"
            label={<span style={{ color: '#d1d5db' }}>API Key</span>}
            extra={<span style={{ color: '#6b7280' }}>已配置时留空表示保持不变</span>}
          >
            <Input.Password
              placeholder={keyConfigured ? '••••••••（留空保持不变）' : 'sk-...'}
              style={{ background: '#1f2937', border: '1px solid #374151', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item
            name="base_url"
            label={<span style={{ color: '#d1d5db' }}>Base URL</span>}
            initialValue="https://api.deepseek.com"
          >
            <Input
              placeholder="https://api.deepseek.com"
              style={{ background: '#1f2937', border: '1px solid #374151', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item
            name="model"
            label={<span style={{ color: '#d1d5db' }}>Model</span>}
            initialValue="deepseek-chat"
          >
            <Input
              placeholder="deepseek-chat"
              style={{ background: '#1f2937', border: '1px solid #374151', color: '#fff' }}
            />
          </Form.Item>

          <Space>
            <Button
              type="primary"
              icon={<Save size={16} />}
              loading={saving}
              onClick={() => form.submit()}
              style={{ background: '#06b6d4', borderColor: '#06b6d4' }}
            >
              保存配置
            </Button>
            {keyConfigured && <Tag color="green" bordered={false}>当前已配置</Tag>}
          </Space>
        </Form>
      </Card>
    </div>
  );
};

export default Settings;
