import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Typography } from 'antd';
import { TrendingUp, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useProjectStore } from '../store/project';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const activeProjectId = useProjectStore(s => s.activeProjectId);
  const dataVersion = useProjectStore(s => s.dataVersion);

  useEffect(() => {
    axios.get('/api/stats/dashboard', { params: { project_id: activeProjectId } })
      .then(r => setStats(r.data))
      .catch(() => {});
  }, [activeProjectId, dataVersion]);

  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#9ca3af' }, data: ['正常单据', '异常单据'] },
    xAxis: {
      type: 'category',
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
      axisLabel: { color: '#9ca3af' }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: '#1f2937' } }
    },
    series: [
      {
        name: '正常单据',
        type: 'bar',
        stack: 'total',
        data: [42, 55, 38, 60, 48, 52, 45, 58, 40, 50, 44, 30],
        itemStyle: { color: '#06b6d4' }
      },
      {
        name: '异常单据',
        type: 'bar',
        stack: 'total',
        data: [3, 2, 5, 4, 6, 3, 7, 2, 4, 1, 5, 3],
        itemStyle: { color: '#ef4444' }
      }
    ]
  };

  const total = stats?.total_vouchers || 242;
  const anomalies = stats?.anomaly_vouchers || 8;
  const avg = stats?.avg_risk_score || 42;
  const critical = stats?.critical_vouchers || 1;
  const dist = stats?.risk_distribution || { Low: 180, Medium: 40, High: 14, Critical: 1 };

  const distOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
    legend: {
      bottom: 0,
      textStyle: { color: '#9ca3af' },
      data: ['低风险', '中风险', '高风险', '极度危险']
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '68%'],
        avoidLabelOverlap: true,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#fff' } },
        labelLine: { show: false },
        data: [
          { value: dist.Low,      name: '低风险',    itemStyle: { color: '#10b981' } },
          { value: dist.Medium,   name: '中风险',    itemStyle: { color: '#f59e0b' } },
          { value: dist.High,     name: '高风险',    itemStyle: { color: '#f97316' } },
          { value: dist.Critical, name: '极度危险',  itemStyle: { color: '#ef4444' } }
        ]
      }
    ]
  };

  const kpiCards = [
    { title: '检测凭证总数', value: total,  trend: '',        color: '#06b6d4', icon: <Activity color="#06b6d4" /> },
    { title: '识别异常单据', value: anomalies,trend: '',        color: '#ef4444', icon: <AlertTriangle color="#ef4444" /> },
    { title: '平均风险评分', value: avg.toFixed?.(1) || avg, trend: '',    color: '#10b981', icon: <ShieldCheck color="#10b981" /> },
    { title: '极度危险凭证', value: critical, trend: '',        color: '#f59e0b', icon: <TrendingUp color="#f59e0b" /> },
  ];

  const level = avg >= 70 ? '高' : avg >= 30 ? '中' : '低';
  const levelColor = avg >= 70 ? '#ef4444' : avg >= 30 ? '#f59e0b' : '#10b981';

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldCheck size={24} color="#06b6d4" />
          财务异常审计总览仪表盘
        </Title>
        <Text type="secondary" style={{ marginTop: 6, display: 'block' }}>
          白盒孤立森林检测 · 多维特征拓扑分析 · 实时风险监控
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        {kpiCards.map((card, idx) => (
          <Col xs={24} sm={12} lg={6} key={idx}>
            <Card style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }} bodyStyle={{ padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Statistic
                  title={<span style={{ color: '#9ca3af', fontSize: 13 }}>{card.title}</span>}
                  value={card.value}
                  valueStyle={{ color: card.color, fontSize: 26, fontWeight: 'bold' }}
                />
                <div style={{ padding: 10, background: '#1f2937', borderRadius: 10 }}>{card.icon}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={15}>
          <Card 
            title={<span style={{ color: '#fff' }}><Activity size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} /> 月度单据与异常分布趋势</span>} 
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }}
          >
            <ReactECharts option={trendOption} style={{ height: 340 }} />
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card 
            title={<span style={{ color: '#fff' }}><AlertTriangle size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#f59e0b' }} /> 风险等级分布</span>} 
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, height: '100%' }}
          >
            <div style={{ textAlign: 'center', marginBottom: 10 }}>
              <div style={{ fontSize: 52, fontWeight: 'bold', color: levelColor }}>{avg}</div>
              <div style={{ color: levelColor, fontWeight: 'bold', fontSize: 16, letterSpacing: 2 }}>
                综合风险等级 · {level}
              </div>
            </div>
            <ReactECharts option={distOption} style={{ height: 240 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
