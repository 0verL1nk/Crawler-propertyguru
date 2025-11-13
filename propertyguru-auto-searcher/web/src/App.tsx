import React from 'react';
import { ConfigProvider, theme } from 'antd';
import PropertySearch from './components/PropertySearch';

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#667eea',
          borderRadius: 8,
        },
      }}
    >
      <PropertySearch />
    </ConfigProvider>
  );
};

export default App;

