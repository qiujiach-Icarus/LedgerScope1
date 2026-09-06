import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Typography, Table, Tag, Space, Progress, Button, Select, message, Alert } from 'antd';
import { Target, Activity, AlertTriangle, TrendingUp, Fingerprint, PieChart as PieIcon, Sparkles, Download } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import type { ColumnsType } from 'antd/es/table';
import { useProjectStore } from '../store/project';

const { Title, Text } = Typography;

// iForest 特征列 → 中文标签
const FEATURE_LABELS: Record<string, string> = {
  amount: '金额',
  month: '记账月份',
  day_of_week: '星期几',
  direction_code: '借贷方向',
  amount_deviation_ratio: '金额偏离倍数',
};

const PIE_COLORS = ['#ef4444', '#f97316', '#f59e0b', '#06b6d4', '#10b981', '#8b5cf6'];

interface VoucherRow {
  voucher_id: string;
  date?: string;
  account?: string;
  amount?: number;
  风险评分?: number;
  偏离倍数?: number;
  平均切分深度?: number;
  是否异常?: boolean;
  异常原因诊断?: string;
}

const RiskAttribution: React.FC = () => {
  const [treeTrace, setTreeTrace] = useState<any>(null);
  const [vouchers, setVouchers] = useState<VoucherRow[]>([]);
  const [selectedVoucher, setSelectedVoucher] = useState<string | undefined>(undefined);
  const [report, setReport] = useState<string>('');
  const [reportMeta, setReportMeta] = useState<any>(null);
  const [steps, setSteps] = useState<any[]>([]);
  const [findingId, setFindingId] = useState<string>('');
  const [findingStatus, setFindingStatus] = useState<string>('');
  const [violations, setViolations] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const activeProjectId = useProjectStore(s => s.activeProjectId);
  const dataVersion = useProjectStore(s => s.dataVersion);

  useEffect(() => {
    setReport('');
    setReportMeta(null);
    setSelectedVoucher(undefined);
    axios.get('/api/analytics/tree-trace', { params: { project_id: activeProjectId } })
      .then(r => setTreeTrace(r.data)).catch(() => {});
    axios.get('/api/vouchers', { params: { limit: 200, risk_min: 0, project_id: activeProjectId } })
      .then(r => { if (Array.isArray(r.data) && r.data.length) setVouchers(r.data); })
      .catch(() => {});
  }, [activeProjectId, dataVersion]);

  // 异常凭证
  const anomalyRows = vouchers.length ? vouchers.filter(v => v.是否异常) : [];

  // 归因因子统计（"金额远超科目均值"等）
  const factorCount: Record<string, number> = {};
  anomalyRows.forEach(v => {
    const diag = v.异常原因诊断 || '多维特征组合离群';
    diag.split('、').forEach(f => {
      const key = f.trim();
      if (key) factorCount[key] = (factorCount[key] || 0) + 1;
    });
  });

  // 无数据时兜底 mock
  const factorEntries = Object.keys(factorCount).length
    ? Object.entries(factorCount).sort((a, b) => b[1] - a[1])
    : [['金额远超科目均值', 4], ['年末/年初突击', 3], ['非工作日记账', 3], ['多维特征组合离群', 2]];

  // 特征切分贡献（iForest 在隔离时对各特征的使用次数）
  const splitPref = treeTrace?.['特征维度切分偏好'];
  const featureData = splitPref
    ? Object.entries(splitPref)
        .map(([k, v]) => ({ name: FEATURE_LABELS[k] || k, value: v as number }))
        .sort((a, b) => b.value - a.value)
    : [
        { name: '金额偏离倍数', value: 486 },
        { name: '金额', value: 320 },
        { name: '星期几', value: 210 },
        { name: '记账月份', value: 158 },
        { name: '借贷方向', value: 76 },
      ];

  // KPI
  const anomalyTotal = anomalyRows.length || 8;
  const avgRisk = anomalyRows.length
    ? (anomalyRows.reduce((s, v) => s + (v.风险评分 || 0), 0) / anomalyRows.length).toFixed(1)
    : 78;
  const topFactor = factorEntries[0][0];
  const topFeature = featureData[0].name;

  const featureOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      name: '切分次数',
      axisLabel: { color: '#9ca3af' },
      nameTextStyle: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: '#1f2937' } },
    },
    yAxis: {
      type: 'category',
      data: featureData.map(d => d.name).reverse(),
      axisLabel: { color: '#d1d5db' },
    },
    series: [
      {
        name: '切分次数',
        type: 'bar',
        barWidth: 18,
        data: featureData.map(d => d.value).reverse(),
        itemStyle: { color: '#06b6d4', borderRadius: [0, 6, 6, 0] },
        label: { show: true, position: 'right', color: '#9ca3af' },
      },
    ],
  };

  const factorOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#9ca3af' } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '66%'],
        avoidLabelOverlap: true,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#fff' } },
        labelLine: { show: false },
        data: factorEntries.map(([name, value], i) => ({
          name,
          value,
          itemStyle: { color: PIE_COLORS[i % PIE_COLORS.length] },
        })),
      },
    ],
  };

  const riskLevel = (score: number) => {
    if (score >= 90) return { label: '极度危险', color: 'red', code: 'critical' };
    if (score >= 70) return { label: '高风险', color: 'orange', code: 'high' };
    if (score >= 30) return { label: '中风险', color: 'gold', code: 'medium' };
    return { label: '低风险', color: 'green', code: 'low' };
  };

  const columns: ColumnsType<VoucherRow> = [
    {
      title: '凭证号',
      dataIndex: 'voucher_id',
      key: 'voucher_id',
      width: 110,
      render: (t) => <span style={{ color: '#06b6d4', fontWeight: 600 }}>#{t}</span>,
    },
    {
      title: '会计科目',
      dataIndex: 'account',
      key: 'account',
      width: 130,
      ellipsis: true,
      render: (t) => <Tag color="cyan" bordered={false} style={{ margin: 0 }}>{t || '-'}</Tag>,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right',
      render: (v: number) => (
        <span style={{ color: '#fff', fontFamily: 'monospace' }}>
          ¥ {v?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      title: '风险评分',
      dataIndex: '风险评分',
      key: 'risk',
      width: 200,
      render: (score: number) => {
        const lvl = riskLevel(score);
        return (
          <Space size={10}>
            <Progress
              percent={Math.min(100, Math.round(score))}
              size="small"
              style={{ width: 110, minWidth: 110 }}
              strokeColor={lvl.code === 'low' ? '#10b981' : lvl.code === 'medium' ? '#f59e0b' : lvl.code === 'high' ? '#f97316' : '#ef4444'}
              trailColor="#1f2937"
              format={() => ''}
            />
            <Tag color={lvl.color as any} bordered={false} style={{ margin: 0 }}>{score}</Tag>
          </Space>
        );
      },
    },
    {
      title: '偏离倍数',
      dataIndex: '偏离倍数',
      key: 'ratio',
      width: 100,
      align: 'right',
      render: (v: number) => (
        <span style={{ color: v >= 2 ? '#ef4444' : '#d1d5db', fontWeight: 600 }}>{v?.toFixed?.(2) || v} 倍</span>
      ),
    },
    {
      title: '归因因子',
      dataIndex: '异常原因诊断',
      key: 'reason',
      render: (t: string) => (
        <Space size={4} wrap>
          {(t || '多维特征组合离群').split('、').map((f, i) => (
            <Tag key={i} color="error" bordered={false} style={{ margin: 0 }}>⚠ {f}</Tag>
          ))}
        </Space>
      ),
    },
  ];

  // 归因明细：优先真实异常数据，兜底 mock
  const detailRows = anomalyRows.length
    ? anomalyRows.slice(0, 10)
    : [
        { voucher_id: '1', account: '房屋租赁', amount: 10619.83, 风险评分: 100, 偏离倍数: 2.2, 异常原因诊断: '金额远超科目均值、年末突击' },
        { voucher_id: '2', account: '房屋租赁', amount: 10350.0, 风险评分: 98.1, 偏离倍数: 2.14, 异常原因诊断: '金额远超科目均值' },
        { voucher_id: '1b', account: '房屋租赁', amount: 4500.0, 风险评分: 91.73, 偏离倍数: 0.93, 异常原因诊断: '非工作日记账、年初突击' },
        { voucher_id: '4', account: '维修费', amount: 2908.0, 风险评分: 90.42, 偏离倍数: 2.69, 异常原因诊断: '金额远超科目均值、非工作日' },
        { voucher_id: '2b', account: '房屋租赁', amount: 6000.0, 风险评分: 90.4, 偏离倍数: 1.24, 异常原因诊断: '年末年初突击' },
      ];

  const kpiCards = [
    { title: '异常凭证总数', value: anomalyTotal, color: '#ef4444', icon: <AlertTriangle color="#ef4444" /> },
    { title: '平均风险评分', value: avgRisk, color: '#f97316', icon: <TrendingUp color="#f97316" /> },
    { title: '主导归因因子', value: topFactor, color: '#f59e0b', icon: <Fingerprint color="#f59e0b" />, isText: true },
    { title: '主导切分特征', value: topFeature, color: '#06b6d4', icon: <Activity color="#06b6d4" />, isText: true },
  ];

  const voucherOptions = detailRows.map(r => ({
    value: String(r.voucher_id),
    label: `#${r.voucher_id} · ${r.account || '-'} · 风险 ${r.风险评分 ?? '-'}`,
  }));

  const SPECIALIST_LABELS: Record<string, string> = {
    voucher: '凭证专家',
    invoice: '发票专家',
    bank: '银行流水专家',
    statement: '报表专家',
    vendor: '供应商/客户专家',
  };

  const generateReport = async () => {
    setLoading(true);
    setSteps([]);
    setFindingId('');
    setFindingStatus('');
    setViolations([]);
    try {
      const res = await axios.post('/api/agent/attribution', selectedVoucher ? { voucher_id: selectedVoucher, project_id: activeProjectId } : { project_id: activeProjectId });
      setReport(res.data.report);
      setReportMeta(res.data);
      setSteps(res.data.steps || []);
      setFindingId(res.data.finding_id || '');
      setFindingStatus(res.data.status || 'draft');
      setViolations(res.data.violations || []);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '归因报告生成失败');
    } finally {
      setLoading(false);
    }
  };

  const updateFindingStatus = async (status: 'confirmed' | 'rejected') => {
    if (!findingId) return;
    try {
      await axios.post(`/api/findings/${findingId}/status`, { status });
      setFindingStatus(status);
      message.success(status === 'confirmed' ? '已确认该审计发现' : '已驳回该审计发现');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '状态更新失败');
    }
  };

  const handleExportReport = () => {
    if (!report) {
      message.info('请先生成归因报告');
      return;
    }
    const title = reportMeta?.voucher_id ? `# AI 归因报告 · #${reportMeta.voucher_id}\n\n` : '';
    const blob = new Blob(['\ufeff' + title + report], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `归因报告_${reportMeta?.voucher_id || 'default'}.md`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('归因报告已导出');
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Target size={24} color="#06b6d4" />
          风险分析归因 · 全局驱动因子诊断
        </Title>
        <Text type="secondary" style={{ marginTop: 6, display: 'block' }}>
          基于 iForest 特征切分贡献与异常原因聚合，定位驱动异常的关键维度与业务因子
        </Text>
      </div>

      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <Select
          style={{ width: 300 }}
          placeholder="选择凭证（默认最高风险）"
          value={selectedVoucher}
          onChange={setSelectedVoucher}
          allowClear
          showSearch
          optionFilterProp="label"
          options={voucherOptions}
        />
        <Button
          type="primary"
          icon={<Sparkles size={16} />}
          onClick={generateReport}
          loading={loading}
          style={{ background: '#06b6d4', borderColor: '#06b6d4' }}
        >
          生成 AI 归因报告
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {kpiCards.map((card, idx) => (
          <Col xs={24} sm={12} lg={6} key={idx}>
            <Card style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }} styles={{ body: { padding: 20 } as any }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Statistic
                  title={<span style={{ color: '#9ca3af', fontSize: 13 }}>{card.title}</span>}
                  value={card.value as any}
                  valueStyle={{ color: card.color, fontSize: card.isText ? 18 : 26, fontWeight: 'bold' }}
                />
                <div style={{ padding: 10, background: '#1f2937', borderRadius: 10 }}>{card.icon}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={9}>
          <Card
            title={<span style={{ color: '#fff' }}><Activity size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} /> 特征维度切分贡献（iForest 隔离使用次数）</span>}
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, height: '100%' }}
          >
            <ReactECharts option={featureOption} style={{ height: 320 }} />
            <div style={{ marginTop: 10, padding: '10px 14px', background: '#1f2937', borderRadius: 8 }}>
              <Text style={{ color: '#d1d5db' }}>
                iForest 在隔离样本时对某特征切分越频繁，说明该特征对区分异常贡献越大。
                当前主导特征为 <span style={{ color: '#06b6d4', fontWeight: 'bold' }}>{topFeature}</span>。
              </Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={15}>
          <Card
            title={<span style={{ color: '#fff' }}><PieIcon size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} /> 异常原因归因分布（业务因子聚合）</span>}
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }}
          >
            <ReactECharts option={factorOption} style={{ height: 340 }} />
            <div style={{ marginTop: 10, padding: '10px 14px', background: '#1f2937', borderRadius: 8 }}>
              <Text style={{ color: '#d1d5db' }}>
                共聚合出 <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{factorEntries.length}</span> 类归因因子，
                其中「<span style={{ color: '#f59e0b', fontWeight: 'bold' }}>{topFactor}</span>」出现频次最高，为当前主要风险来源。
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        title={<span style={{ color: '#fff' }}><Fingerprint size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#f59e0b' }} /> 高风险凭证归因明细</span>}
        style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, marginTop: 20 }}
        styles={{ body: { padding: 0 } as any }}
      >
        <Table
          columns={columns}
          dataSource={detailRows}
          rowKey="voucher_id"
          pagination={false}
          scroll={{ x: 900 }}
          style={{ background: 'transparent' }}
          className="attribution-table"
        />
      </Card>

      {report && (
        <>
          {steps.length > 0 && (
            <Card
              title={<span style={{ color: '#fff' }}><Sparkles size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} /> Agent 审计过程（规划 → 调用 → 结论）</span>}
              style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, marginTop: 20 }}
            >
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {steps.map((step, i) => (
                  <div key={i} style={{ background: '#1f2937', borderRadius: 8, padding: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <Tag color="cyan" bordered={false}>{SPECIALIST_LABELS[step.specialist] || step.specialist}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>{step.tool_calls?.length || 0} 次工具调用</Text>
                    </div>
                    {(step.tool_calls || []).map((tc: any, j: number) => (
                      <div key={j} style={{ marginBottom: 8, padding: '8px 10px', background: '#111827', borderRadius: 6 }}>
                        <div style={{ color: '#93c5fd', fontFamily: 'monospace', fontSize: 13, marginBottom: 4 }}>
                          调用 {tc.tool}{tc.args ? `(${tc.args})` : ''}
                        </div>
                        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#9ca3af', margin: 0, fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6 }}>
                          {JSON.stringify(tc.result, null, 2)}
                        </pre>
                      </div>
                    ))}
                    <div style={{ color: '#e5e7eb', fontSize: 13, lineHeight: 1.7 }}>{step.conclusion}</div>
                  </div>
                ))}
              </Space>
            </Card>
          )}

          <Card
            title={
              <span style={{ color: '#fff' }}>
                <Sparkles size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} />
                AI 归因报告{reportMeta ? ` · #${reportMeta.voucher_id}` : ''}
              </span>
            }
            extra={
              <Space>
                <Button size="small" icon={<Download size={16} />} onClick={handleExportReport}>导出</Button>
                {findingId && (
                  <>
                    <Tag color={findingStatus === 'confirmed' ? 'green' : findingStatus === 'rejected' ? 'red' : 'gold'} bordered={false}>
                      {findingStatus === 'confirmed' ? '已确认' : findingStatus === 'rejected' ? '已驳回' : '待确认'}
                    </Tag>
                    {findingStatus !== 'confirmed' && (
                      <Button size="small" type="primary" style={{ background: '#10b981', borderColor: '#10b981' }} onClick={() => updateFindingStatus('confirmed')}>确认</Button>
                    )}
                    {findingStatus !== 'rejected' && (
                      <Button size="small" danger onClick={() => updateFindingStatus('rejected')}>驳回</Button>
                    )}
                  </>
                )}
              </Space>
            }
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, marginTop: 20 }}
          >
            {violations.length > 0 && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12, background: '#451a03', border: '1px solid #9a3412', borderRadius: 8 }}
                message={<span style={{ color: '#fdba74' }}>输出护栏触发：{violations.join('、')}</span>}
              />
            )}
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#e5e7eb', margin: 0, fontFamily: 'inherit', lineHeight: 1.8, fontSize: 14 }}>
              {report}
            </pre>
          </Card>
        </>
      )}

      <style>{`
        .attribution-table .ant-table { background: transparent !important; color: #fff !important; }
        .attribution-table .ant-table-thead > tr > th { background: #1f2937 !important; color: #9ca3af !important; border-bottom: 1px solid #374151 !important; font-weight: 600; }
        .attribution-table .ant-table-tbody > tr > td { border-bottom: 1px solid #1f2937 !important; color: #d1d5db !important; }
        .attribution-table .ant-table-tbody > tr:hover > td { background: #1f2937 !important; }
      `}</style>
    </div>
  );
};

export default RiskAttribution;
