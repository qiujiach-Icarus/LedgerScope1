import React, { useState } from 'react';
import { Card, Row, Col, Upload, Typography, Table, Tag, Space, Alert, Statistic, Progress, message, Radio } from 'antd';
import { UploadCloud, FileSpreadsheet, CheckCircle2, XCircle, Clock, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';
import axios from 'axios';
import { useProjectStore } from '../store/project';

const { Dragger } = Upload;
const { Title, Text } = Typography;

const UploadPage: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [appendMode, setAppendMode] = useState<'append' | 'replace'>('append');
  const { activeProjectId, projects, loadProjects } = useProjectStore();
  const activeProject = projects.find(p => p.id === activeProjectId);

  const historyData = [
    { key: '1', name: 'test_data.xlsx（示例）', time: '2026-09-05 16:00', status: 'success', anomalies: 8, total: 242 },
  ];

  const columns = [
    { 
      title: '文件名', 
      dataIndex: 'name', 
      key: 'name', 
      render: (text: string) => (
        <Space size={8}>
          <FileSpreadsheet size={16} color="#06b6d4" />
          <Text style={{ color: '#e5e7eb' }}>{text}</Text>
        </Space>
      )
    },
    { title: '上传时间', dataIndex: 'time', key: 'time', render: (t: string) => <Text type="secondary">{t}</Text> },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const map: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
          success: { color: 'success', label: '分析完成', icon: <CheckCircle2 size={12} /> },
          failed:  { color: 'error',   label: '分析失败', icon: <XCircle size={12} /> },
          pending: { color: 'processing', label: '分析中...', icon: <Clock size={12} /> },
        };
        const s = map[status] || map.pending;
        return <Tag color={s.color} icon={s.icon}>{s.label}</Tag>;
      }
    },
    { 
      title: '单据数/异常数', 
      key: 'info', 
      render: (_: any, r: any) => (
        <Space>
          <Text type="secondary">共 {r.total || '-'} 条</Text>
          <Text style={{ color: r.anomalies > 0 ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>
            异常 {r.anomalies} 条
          </Text>
        </Space>
      )
    },
  ];

  const uploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: true,
    accept: '.xlsx,.xls,.csv',
    beforeUpload: (file: any) => {
      const isExcel = /\.(xlsx|xls|csv)$/i.test(file.name);
      if (!isExcel) {
        message.error('仅支持 Excel 文件（.xlsx / .xls / .csv）');
        return Upload.LIST_IGNORE;
      }
      const isLt100M = file.size / 1024 / 1024 < 100;
      if (!isLt100M) {
        message.error('文件大小不能超过 100MB');
        return Upload.LIST_IGNORE;
      }
      return true;
    },
    customRequest: async ({ file, onSuccess, onError }: any) => {
      setUploading(true);
      setResult(null);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', activeProjectId || '');
      formData.append('append', String(appendMode === 'append'));
      try {
        const res = await axios.post('/api/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 300000,
        });
        setResult(res.data);
        await loadProjects();
        message.success(`文件 "${file.name}" 分析完成！`);
        onSuccess?.(res.data);
      } catch (e: any) {
        const msg = e?.response?.data?.detail || e?.message || '上传失败';
        message.error(`分析失败：${msg}`);
        onError?.(e);
      } finally {
        setUploading(false);
      }
    },
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldCheck size={24} color="#06b6d4" />
          财务账本上传与智能审计
        </Title>
        <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
          支持 Excel 格式财务凭证账本。上传后将自动完成：<span style={{ color: '#06b6d4' }}>数据清洗 → 统计模式分析 → 孤立森林异常检测 → 风险评分</span> 四阶段白盒检测
        </Text>
      </div>

      {result && (
        <Alert
          type="success"
          showIcon
          style={{ marginBottom: 20, background: '#052e16', border: '1px solid #166534', borderRadius: 8 }}
          icon={<CheckCircle2 color="#10b981" />}
          message={<span style={{ color: '#bbf7d0' }}>分析完成</span>}
          description={
            <Space wrap style={{ marginTop: 4 }}>
              <Text style={{ color: '#86efac' }}>总单据数：{result.summary?.total_count ?? '-'}</Text>
              <Text style={{ color: '#fca5a5' }}>异常单据数：{result.summary?.anomaly_count ?? '-'}</Text>
              <Text style={{ color: '#93c5fd' }}>平均风险评分：{result.summary?.avg_risk_score ?? '-'}</Text>
            </Space>
          }
        />
      )}

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={12}>
          <Card 
            style={{ 
              background: '#111827', 
              border: '1px solid #1f2937', 
              height: 'auto',
              minHeight: 420,
              borderRadius: 12
            }}
            title={
              <span style={{ color: '#fff' }}>
                <UploadCloud size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} />
                上传账本
              </span>
            }
            extra={<Tag color="blue" icon={<ShieldCheck size={12} />}>离线安全处理</Tag>}
          >
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
              <Text style={{ color: '#9ca3af' }}>
                存入项目：<Tag color="cyan" bordered={false} style={{ margin: 0 }}>{activeProject?.name || '默认项目'}</Tag>
              </Text>
              <Radio.Group value={appendMode} onChange={e => setAppendMode(e.target.value)} size="small">
                <Radio.Button value="append">追加为多数据集（合并分析）</Radio.Button>
                <Radio.Button value="replace">替换项目数据（单数据集）</Radio.Button>
              </Radio.Group>
            </div>
            <Dragger {...uploadProps} style={{ 
              background: 'transparent', 
              border: '2px dashed #374151', 
              borderRadius: 12,
              padding: '30px 20px'
            }}>
              <p className="ant-upload-drag-icon">
                <UploadCloud size={56} color="#06b6d4" style={{ margin: '10px auto' }} />
              </p>
              <p className="ant-upload-text" style={{ color: '#fff', fontSize: 18, fontWeight: 500 }}>
                点击或拖拽文件到此区域上传
              </p>
              <p className="ant-upload-hint" style={{ color: '#9ca3af', marginTop: 10, lineHeight: 1.8 }}>
                <Space wrap size={[16, 8]} style={{ justifyContent: 'center' }}>
                  <span><Tag color="cyan" bordered={false}>.xlsx</Tag></span>
                  <span><Tag color="blue" bordered={false}>.xls</Tag></span>
                  <span><Tag color="geekblue" bordered={false}>.csv</Tag></span>
                </Space>
                <div style={{ marginTop: 12, fontSize: 13 }}>
                  <AlertTriangle size={14} color="#f59e0b" style={{ verticalAlign: 'middle', marginRight: 6 }} />
                  单文件大小不超过 100MB，建议使用包含凭证号、日期、科目、借贷方向、金额等列的标准财务账本
                </div>
              </p>
              {uploading && (
                <div style={{ marginTop: 20, padding: '0 40px' }}>
                  <Progress percent={60} status="active" showInfo={false} strokeColor="#06b6d4" trailColor="#1f2937" />
                  <Text type="secondary" style={{ display: 'block', marginTop: 10, fontSize: 12 }}>
                    正在进行多维拓扑切分与 iForest 孤立森林计算，请稍候...
                  </Text>
                </div>
              )}
            </Dragger>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card 
            style={{ 
              background: '#111827', 
              border: '1px solid #1f2937', 
              minHeight: 420,
              borderRadius: 12
            }}
            title={
              <span style={{ color: '#fff' }}>
                <Clock size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} />
                近期上传与分析结果
              </span>
            }
          >
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Card size="small" style={{ background: '#1f2937', border: 'none', borderRadius: 8 }}>
                  <Statistic 
                    title={<span style={{ color: '#9ca3af', fontSize: 12 }}>累计检测单据</span>} 
                    value={result ? result.summary?.total_count ?? 0 : 242}
                    valueStyle={{ color: '#06b6d4', fontSize: 22 }}
                    prefix={<Activity size={16} />}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" style={{ background: '#1f2937', border: 'none', borderRadius: 8 }}>
                  <Statistic 
                    title={<span style={{ color: '#9ca3af', fontSize: 12 }}>识别高危异常</span>} 
                    value={result ? result.summary?.anomaly_count ?? 0 : 8}
                    valueStyle={{ color: '#ef4444', fontSize: 22 }}
                    prefix={<AlertTriangle size={16} />}
                  />
                </Card>
              </Col>
            </Row>

            <Table 
              columns={columns} 
              dataSource={historyData} 
              pagination={false}
              size="middle"
              style={{ background: 'transparent' }}
              className="custom-table"
              rowKey="key"
            />
          </Card>
        </Col>
      </Row>

      <style>{`
        .custom-table .ant-table { background: transparent !important; color: #fff !important; }
        .custom-table .ant-table-thead > tr > th { background: #1f2937 !important; color: #9ca3af !important; border-bottom: 1px solid #374151 !important; }
        .custom-table .ant-table-tbody > tr > td { border-bottom: 1px solid #1f2937 !important; color: #d1d5db !important; }
        .custom-table .ant-table-tbody > tr:hover > td { background: #1f2937 !important; }
      `}</style>
    </div>
  );
};

export default UploadPage;
