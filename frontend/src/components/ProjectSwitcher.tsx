import React, { useEffect, useState } from 'react';
import { Select, Button, Space, Tooltip } from 'antd';
import { Folder, Plus } from 'lucide-react';
import { useProjectStore } from '../store/project';

const ProjectSwitcher: React.FC = () => {
  const { projects, activeProjectId, loading, loadProjects, setActiveProject, createProject } = useProjectStore();
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async () => {
    const name = window.prompt('请输入项目名称：');
    if (!name) return;
    setCreating(true);
    try {
      await createProject(name.trim());
    } finally {
      setCreating(false);
    }
  };

  const options = projects.map(p => ({
    value: p.id,
    label: `${p.name}（${p.dataset_count ?? 0} 数据）`,
  }));

  return (
    <Space size={6}>
      <Folder size={16} color="#9ca3af" />
      <Select
        style={{ width: 200 }}
        size="small"
        loading={loading}
        value={activeProjectId || undefined}
        placeholder="选择项目"
        options={options}
        onChange={(id) => setActiveProject(id)}
        notFoundContent="暂无项目"
      />
      <Tooltip title="新建项目">
        <Button
          size="small"
          type="text"
          icon={<Plus size={16} color="#06b6d4" />}
          loading={creating}
          onClick={handleCreate}
        />
      </Tooltip>
    </Space>
  );
};

export default ProjectSwitcher;
