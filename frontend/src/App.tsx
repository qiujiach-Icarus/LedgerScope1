import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Vouchers from './pages/Vouchers';
import Explainability from './pages/Explainability';
import RiskAttribution from './pages/RiskAttribution';
import Settings from './pages/Settings';

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
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
