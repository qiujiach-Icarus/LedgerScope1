import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Input, Button, Card, Progress, message, Select } from 'antd';
import { Search, Filter, RefreshCw, Info, FileText, Download } from 'lucide-react';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '../store/project';

const { Option } = Select;

interface VoucherRecord {
  voucher_id: string;
  date: string;
  account: string;
  amount: number;
  风险评分: number;
  偏离倍数: number;
  平均切分深度: number;
  摘要: string;
  是否异常: boolean;
  异常原因诊断?: string;
  direction?: string;
}

const Vouchers: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<VoucherRecord[]>([]);
  const [keyword, setKeyword] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const activeProjectId = useProjectStore(s => s.activeProjectId);
  const dataVersion = useProjectStore(s => s.dataVersion);
  const navigate = useNavigate();

  useEffect(() => {
    loadList();
  }, [activeProjectId, dataVersion]);

  const loadList = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/vouchers', { params: { limit: 100, risk_min: 0, project_id: activeProjectId } });
      if (Array.isArray(res.data) && res.data.length > 0) {
        setData(res.data);
      } else {
        // 模拟数据展示
        setData([
          { voucher_id: '1', date: '2021-12-22', account: '房屋租赁', amount: 10619.83, 风险评分: 100, 偏离倍数: 2.20, 平均切分深度: 5.43, 摘要: '年末房租支付', 是否异常: true, 异常原因诊断: '金额远超科目均值、年末突击', direction: '借' },
          { voucher_id: '2', date: '2022-03-09', account: '房屋租赁', amount: 10350.00, 风险评分: 98.1, 偏离倍数: 2.14, 平均切分深度: 5.51, 摘要: '一季度房租', 是否异常: true, 异常原因诊断: '金额远超科目均值', direction: '借' },
          { voucher_id: '1b', date: '2021-01-31', account: '房屋租赁', amount: 4500.00, 风险评分: 91.73, 偏离倍数: 0.93, 平均切分深度: 5.78, 摘要: '年初房租调整', 是否异常: true, 异常原因诊断: '非工作日记账、年初突击', direction: '借' },
          { voucher_id: '4', date: '2023-04-23', account: '维修费', amount: 2908.00, 风险评分: 90.42, 偏离倍数: 2.69, 平均切分深度: 5.88, 摘要: '维修卫生间等', 是否异常: true, 异常原因诊断: '金额远超科目均值、非工作日', direction: '借' },
          { voucher_id: '2b', date: '2024-01-08', account: '房屋租赁', amount: 6000.00, 风险评分: 90.4, 偏离倍数: 1.24, 平均切分深度: 5.86, 摘要: '年初房租', 是否异常: true, 异常原因诊断: '年末年初突击', direction: '借' },
          { voucher_id: '7', date: '2023-06-15', account: '办公用品', amount: 240.00, 风险评分: 22, 偏离倍数: 0.8, 平均切分深度: 8.1, 摘要: '打印纸采购', 是否异常: false, direction: '借' },
          { voucher_id: '8', date: '2023-06-16', account: '差旅费', amount: 3200.00, 风险评分: 35, 偏离倍数: 1.1, 平均切分深度: 7.8, 摘要: '出差高铁住宿', 是否异常: false, direction: '借' },
        ]);
      }
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const riskLevel = (score: number) => {
    if (score >= 90) return { label: '极度危险', color: 'red',    code: 'critical' };
    if (score >= 70) return { label: '高风险',   color: 'orange', code: 'high' };
    if (score >= 30) return { label: '中风险',   color: 'gold',   code: 'medium' };
    return            { label: '低风险',   color: 'green',  code: 'low' };
  };

  const filtered = data.filter(r => {
    const matchKey = keyword ? [r.voucher_id, r.account, r.摘要, r.date].some(v => String(v ?? '').includes(keyword)) : true;
    const matchRisk = riskFilter === 'all' ? true : riskLevel(r.风险评分).code === riskFilter;
    return matchKey && matchRisk;
  });

  const handleExport = () => {
    if (!filtered.length) {
      message.info('当前无可导出数据');
      return;
    }
    const headers = ['凭证号', '记账日期', '会计科目', '借贷', '金额', '偏离倍数', '风险评分', 'iForest隔离深度', '业务摘要', '异常原因诊断'];
    const lines = filtered.map(r => [
      r.voucher_id,
      String(r.date || '').slice(0, 10),
      r.account,
      r.direction || '',
      r.amount,
      r.偏离倍数,
      r.风险评分,
      r.平均切分深度,
      r.摘要 || '',
      r.异常原因诊断 || '',
    ].map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','));
    const csv = '\ufeff' + [headers.join(','), ...lines].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '凭证风险清单.csv';
    a.click();
    URL.revokeObjectURL(url);
    message.success('已导出 CSV');
  };

  const columns: ColumnsType<VoucherRecord> = [
    {
      title: '凭证号',
      dataIndex: 'voucher_id',
      key: 'voucher_id',
      width: 100,
      render: (text) => <span style={{ color: '#06b6d4', fontWeight: 600 }}>#{text}</span>,
      sorter: (a, b) => Number(a.voucher_id) - Number(b.voucher_id),
    },
    {
      title: '记账日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      render: (t) => <span style={{ color: '#9ca3af' }}>{String(t || '').slice(0, 10)}</span>
    },
    {
      title: '会计科目',
      dataIndex: 'account',
      key: 'account',
      width: 120,
      ellipsis: true,
      render: (t) => <Tag color="cyan" bordered={false} style={{ margin: 0 }}>{t}</Tag>
    },
    {
      title: '借贷',
      dataIndex: 'direction',
      key: 'direction',
      width: 70,
      render: (d) => d ? <Tag color={d === '借' ? 'blue' : 'green'} bordered={false}>{d}</Tag> : '-'
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 140,
      align: 'right',
      render: (amount: number) => <span style={{ color: '#fff', fontFamily: 'monospace' }}>¥ {amount?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>,
      sorter: (a, b) => a.amount - b.amount,
    },
    {
      title: '偏离倍数',
      dataIndex: '偏离倍数',
      key: 'ratio',
      width: 100,
      align: 'right',
      render: (v: number) => <span style={{ color: v >= 2 ? '#ef4444' : '#d1d5db', fontWeight: 600 }}>{v?.toFixed?.(2) || v} 倍</span>,
      sorter: (a, b) => a.偏离倍数 - b.偏离倍数,
    },
    {
      title: '风险评分',
      dataIndex: '风险评分',
      key: 'risk',
      width: 200,
      render: (score: number, r) => {
        const lvl = riskLevel(score);
        return (
          <Space size={10}>
            <Progress 
              percent={Math.min(100, Math.round(score))} 
              size="small" 
              style={{ width: 120, minWidth: 120 }}
              strokeColor={lvl.code === 'low' ? '#10b981' : lvl.code === 'medium' ? '#f59e0b' : lvl.code === 'high' ? '#f97316' : '#ef4444'}
              trailColor="#1f2937"
              format={() => ''}
            />
            <Tag color={lvl.color as any} bordered={false} style={{ margin: 0 }}>{score} · {lvl.label}</Tag>
          </Space>
        );
      },
      sorter: (a, b) => a.风险评分 - b.风险评分,
      defaultSortOrder: 'descend' as any,
    },
    {
      title: 'iForest 隔离深度',
      dataIndex: '平均切分深度',
      key: 'depth',
      width: 120,
      align: 'right',
      render: (v: number) => <span style={{ color: v <= 6 ? '#ef4444' : '#d1d5db' }}>{v?.toFixed?.(2) || v} 刀</span>,
      sorter: (a, b) => a.平均切分深度 - b.平均切分深度,
    },
    {
      title: '业务摘要',
      dataIndex: '摘要',
      key: 'desc',
      ellipsis: true,
      render: (t, r) => (
        <Space direction="vertical" size={2} style={{ margin: 0 }}>
          <span style={{ color: '#e5e7eb' }}>{t || '-'}</span>
          {r.异常原因诊断 && <span style={{ color: '#fca5a5', fontSize: 12 }}>⚠ {r.异常原因诊断}</span>}
        </Space>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      fixed: 'right' as any,
      render: (_, r) => (
        <Space size="small">
          <Button type="text" size="small" icon={<Info size={16} color="#06b6d4" />} onClick={() => navigate(`/explain?voucher_id=${r.voucher_id}`)}>
            穿透分析
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Card.Meta 
            title={<span style={{ color: '#fff', fontSize: 20, display: 'flex', alignItems: 'center', gap: 10 }}><FileText size={24} color="#06b6d4" /> 凭证风险清单</span>} 
            description={<span style={{ color: '#9ca3af' }}>按风险评分降序 · Top 高危单据优先展示</span>}
          />
        </div>
        <Space wrap>
          <Input 
            prefix={<Search size={16} />} 
            placeholder="搜索凭证号 / 科目 / 摘要..." 
            allowClear
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            style={{ width: 260, background: '#111827', border: '1px solid #1f2937', color: '#fff' }}
          />
          <Select 
            value={riskFilter} 
            onChange={setRiskFilter}
            style={{ width: 150 }} 
            placeholder="风险等级"
          >
            <Option value="all">全部等级</Option>
            <Option value="critical">极度危险</Option>
            <Option value="high">高风险</Option>
            <Option value="medium">中风险</Option>
            <Option value="low">低风险</Option>
          </Select>
          <Button icon={<Filter size={16} />} style={{ background: '#111827', border: '1px solid #1f2937', color: '#fff' }} onClick={() => message.info('高级筛选：请组合上方搜索框与风险等级筛选')}>高级筛选</Button>
          <Button icon={<RefreshCw size={16} />} onClick={loadList} loading={loading}>刷新</Button>
          <Button icon={<Download size={16} />} type="primary" style={{ background: '#06b6d4' }} onClick={handleExport}>导出Excel</Button>
        </Space>
      </div>

      <Card style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }} styles={{ body: { padding: 0 } as any }}>
        <Table 
          columns={columns} 
          dataSource={filtered} 
          loading={loading}
          pagination={{ 
            pageSize: 10, 
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条凭证 · 其中异常 ${filtered.filter(r=>r.是否异常).length} 条`,
            style: { padding: '10px 16px', color: '#9ca3af' }
          }}
          scroll={{ x: 1300 }}
          style={{ background: 'transparent' }}
          className="custom-table"
          rowKey="voucher_id"
          rowClassName={(r) => r.是否异常 ? 'anomaly-row' : ''}
        />
      </Card>
      
      <style>{`
        .custom-table .ant-table { background: transparent !important; color: #fff !important; }
        .custom-table .ant-table-thead > tr > th { background: #1f2937 !important; color: #9ca3af !important; border-bottom: 1px solid #374151 !important; font-weight: 600; }
        .custom-table .ant-table-tbody > tr > td { border-bottom: 1px solid #1f2937 !important; color: #d1d5db !important; }
        .custom-table .ant-table-tbody > tr.anomaly-row > td { background: rgba(239, 68, 68, 0.05) !important; }
        .custom-table .ant-table-tbody > tr:hover > td { background: #1f2937 !important; }
        .custom-table .ant-table-tbody > tr.anomaly-row:hover > td { background: rgba(239, 68, 68, 0.12) !important; }
        .custom-table .ant-pagination-item a { color: #9ca3af !important; }
        .custom-table .ant-pagination-item-active a { color: #fff !important; background: #06b6d4 !important; border-color: #06b6d4 !important; }
      `}</style>
    </div>
  );
};

export default Vouchers;
