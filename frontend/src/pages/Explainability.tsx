import React from 'react';
import { Row, Col, Card, Typography, Space, Tag, Button, Select, Descriptions, Divider, message } from 'antd';
import { SearchCode, Download, Zap, Lightbulb, FileCheck, Activity } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const Explainability: React.FC = () => {
  const navigate = useNavigate();

  const handleExport = () => {
    const content = `# 异常可解释性分析报告\n\n## 凭证 #V-2023-001 · 风险评分 86 · 极度危险\n\n- 记账日期：2023-12-05（周二）\n- 涉及金额：¥125,000.00\n- 会计科目：差旅费 / 管理费用\n- 偏离倍数：4.20 倍\n\n## 模型诊断说明\n1. 金额严重偏离：差旅费科目 ¥125,000 达到科目均值 4.2 倍。\n2. 时间异常：入账时间为周日 23:45。\n3. 窗口期敏感：12 月年末属于费用突击高发期。\n4. 缓解因素：借贷对应关系正常。\n`;
    const blob = new Blob(['\ufeff' + content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '可解释性分析报告.md';
    a.click();
    URL.revokeObjectURL(url);
    message.success('已导出解释报告');
  };

  const waterfallOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', axisLabel: { color: '#9ca3af' }, splitLine: { lineStyle: { color: '#1f2937' } } },
    yAxis: {
      type: 'category',
      data: ['基础分', '金额偏离倍数', '非工作日记账', '科目组合异常', '月初/年末突击', '风险评分'],
      axisLabel: { color: '#d1d5db' }
    },
    series: [
      {
        name: '特征贡献',
        type: 'bar',
        stack: 'total',
        label: { show: true, position: 'right', color: '#fff', formatter: (p: any) => p.value > 0 ? '+' + p.value : p.value },
        data: [
          { value: 45, itemStyle: { color: '#3b82f6' } },
          { value: 22, itemStyle: { color: '#ef4444' } },
          { value: 10, itemStyle: { color: '#f59e0b' } },
          { value: -5, itemStyle: { color: '#10b981' } },
          { value: 14, itemStyle: { color: '#ef4444' } },
          { value: 86, itemStyle: { color: '#f97316' } }
        ]
      }
    ]
  };

  const traceOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['切分 1 (金额)', '切分 2 (日期)', '切分 3 (星期)', '切分 4 (偏离度)', '切分 5 (流向)', '孤立完成'],
      axisLabel: { color: '#9ca3af', rotate: 20 }
    },
    yAxis: { type: 'value', name: '平均隔离深度', axisLabel: { color: '#9ca3af' }, splitLine: { lineStyle: { color: '#1f2937' } }, nameTextStyle: { color: '#9ca3af' } },
    series: [
      {
        name: '该单据深度',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 10,
        lineStyle: { color: '#ef4444', width: 3 },
        itemStyle: { color: '#ef4444' },
        data: [2, 3, 4, 5, 5.4, 5.43],
        markLine: {
          data: [{ yAxis: 7.7, name: '基准深度', lineStyle: { color: '#06b6d4', type: 'dashed' }, label: { color: '#06b6d4', formatter: '正常基准 7.7 刀' } }]
        }
      },
      {
        name: '正常样本深度',
        type: 'line',
        smooth: true,
        symbol: 'diamond',
        symbolSize: 8,
        lineStyle: { color: '#06b6d4' },
        itemStyle: { color: '#06b6d4' },
        data: [3, 5, 6, 7, 7.5, 7.7]
      }
    ],
    legend: { textStyle: { color: '#9ca3af' }, top: 0 }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Title level={4} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
            <SearchCode size={24} color="#06b6d4" />
            异常可解释性分析 · 证据链穿透
          </Title>
          <Text type="secondary" style={{ marginTop: 6, display: 'block' }}>
            白盒 SHAP 特征贡献分析 + iForest 孤立森林拓扑追踪
          </Text>
        </div>
        <Space wrap>
          <Select defaultValue="V-2023-001" style={{ width: 220 }} placeholder="选择凭证号">
            <Option value="V-2023-001">凭证 #V-2023-001 【极度危险】</Option>
            <Option value="V-2023-002">凭证 #V-2023-002 【高风险】</Option>
            <Option value="V-2023-003">凭证 #V-2023-003 【中风险】</Option>
          </Select>
          <Button icon={<Download size={16} />} onClick={handleExport}>导出解释报告</Button>
          <Button type="primary" icon={<Zap size={16} />} style={{ background: '#06b6d4' }} onClick={() => navigate('/attribution')}>重新深度分析</Button>
        </Space>
      </div>

      <Row gutter={[20, 20]}>
        <Col xs={24} lg={8}>
          <Card style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }}>
            <div style={{ textAlign: 'center', padding: '10px 0' }}>
              <div style={{ fontSize: 72, fontWeight: 'bold', color: '#ef4444', lineHeight: 1 }}>86</div>
              <div style={{ color: '#ef4444', fontWeight: 'bold', fontSize: 20, letterSpacing: 4, marginTop: 6 }}>极度危险</div>
              <div style={{ width: 140, height: 140, margin: '16px auto', borderRadius: '50%', border: '6px solid #ef4444', borderTopColor: 'transparent', transform: 'rotate(-45deg)' }} />
            </div>
            <Divider style={{ borderColor: '#1f2937', margin: '10px 0 16px' }} />
            <Descriptions column={1} size="small" labelStyle={{ color: '#9ca3af', background: '#1f2937' }} contentStyle={{ color: '#fff', background: '#0f172a' }} bordered>
              <Descriptions.Item label="凭证号">#V-2023-001</Descriptions.Item>
              <Descriptions.Item label="记账日期">2023-12-05 (周二)</Descriptions.Item>
              <Descriptions.Item label="涉及金额">¥ 125,000.00</Descriptions.Item>
              <Descriptions.Item label="会计科目">差旅费 / 管理费用</Descriptions.Item>
              <Descriptions.Item label="科目历史均值">¥ 29,800.00</Descriptions.Item>
              <Descriptions.Item label="偏离倍数">
                <Tag color="red" style={{ margin: 0 }}>4.20 倍</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="制单人">张 某</Descriptions.Item>
              <Descriptions.Item label="审计状态"><Tag color="error">待人工复核</Tag></Descriptions.Item>
            </Descriptions>
          </Card>

          <Card 
            title={<span style={{ color: '#fff' }}><Lightbulb size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#f59e0b' }} /> 模型诊断说明</span>}
            style={{ background: '#111827', border: '1px solid #1f2937', marginTop: 20, borderRadius: 12 }}
          >
            <Paragraph style={{ color: '#d1d5db', margin: 0, lineHeight: 1.9 }}>
              该凭证被孤立森林算法判定为高危，主要原因为：
            </Paragraph>
            <ol style={{ color: '#e5e7eb', paddingLeft: 22, marginTop: 10, marginBottom: 0, lineHeight: 2 }}>
              <li><span style={{ color: '#ef4444' }}>金额严重偏离</span>：差旅费科目下 ¥125,000 达到科目均值 <b>4.2 倍</b>，为历史 Top 1%</li>
              <li><span style={{ color: '#f59e0b' }}>时间异常</span>：入账时间为 <b>周日 23:45</b>，属于非标准工作时间</li>
              <li><span style={{ color: '#f59e0b' }}>窗口期敏感</span>：<b>12 月年末</b>属于费用突击高发期</li>
              <li><span style={{ color: '#10b981' }}>缓解因素</span>：借贷对应关系符合正常差旅费组合，未见科目串户</li>
            </ol>
            <Divider style={{ borderColor: '#1f2937', margin: '14px 0' }} />
            <Space>
              <Tag icon={<FileCheck size={12} />} color="processing">建议：调取发票/行程单核验</Tag>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card 
            title={<span style={{ color: '#fff' }}><SearchCode size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} /> SHAP 特征贡献瀑布图（各维度对最终评分的贡献度）</span>}
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, marginBottom: 20 }}
          >
            <ReactECharts option={waterfallOption} style={{ height: 340 }} />
          </Card>

          <Card 
            title={<span style={{ color: '#fff' }}><Activity size={16} style={{ marginRight: 8, verticalAlign: 'middle', color: '#06b6d4' }} /> iForest 孤立森林拓扑穿透（iTree 平均切分深度曲线）</span>}
            style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12 }}
          >
            <ReactECharts option={traceOption} style={{ height: 320 }} />
            <div style={{ marginTop: 10, padding: '10px 14px', background: '#1f2937', borderRadius: 8 }}>
              <Text style={{ color: '#d1d5db' }}>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>● 该单据</span> 仅需 <b>5.43 刀</b> 切分即可被孤立；
                <span style={{ color: '#06b6d4', fontWeight: 'bold', marginLeft: 12 }}>● 正常样本</span> 平均需 <b>7.7 刀</b>。
                切分深度越少代表在特征空间越「离群」，异常概率越高。
              </Text>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Explainability;
