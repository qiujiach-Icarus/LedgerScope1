import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Vouchers from './pages/Vouchers';
import Explainability from './pages/Explainability';
import RiskAttribution from './pages/RiskAttribution';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="vouchers" element={<Vouchers />} />
          <Route path="explain" element={<Explainability />} />
          <Route path="attribution" element={<RiskAttribution />} />
          <Route path="settings" element={
            <div style={{ 
              padding: '60px 20px', 
              textAlign: 'center', 
              background: '#111827', 
              border: '1px solid #1f2937', 
              borderRadius: 12,
              color: '#d1d5db'
            }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>⚙️</div>
              <h2 style={{ color: '#fff', margin: '0 0 10px' }}>系统设置</h2>
              <p style={{ color: '#9ca3af', margin: 0 }}>正在建设中，敬请期待...</p>
            </div>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
