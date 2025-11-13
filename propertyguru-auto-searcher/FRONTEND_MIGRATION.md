# 🎨 Frontend Migration to Ant Design X

## Overview

前端已从纯 HTML/JS 升级到基于 **React + Ant Design X** 的现代化 AI 对话界面。

## 🌟 Why Ant Design X?

Ant Design X 是蚂蚁集团专门为 **AI 驱动的应用界面**开发的组件库，完美契合本项目的需求：

### 核心优势

1. **🤖 AI-First Design**
   - 专为 AI 对话和交互设计
   - 内置流式响应处理
   - 优雅的思考过程展示

2. **💬 专业对话组件**
   - `Bubble` - 气泡消息
   - `Sender` - 智能输入框
   - `useXAgent` - AI 代理管理
   - `useXChat` - 对话流管理

3. **🎯 开箱即用**
   - 完整的 TypeScript 支持
   - 响应式设计
   - 主题定制
   - 无缝集成 Ant Design

## 📂 New Project Structure

```
web/
├── package.json              # 依赖配置
├── vite.config.ts            # Vite 构建配置
├── tsconfig.json             # TypeScript 配置
├── index-new.html            # 新版 HTML 入口
├── src/
│   ├── main.tsx              # React 入口
│   ├── App.tsx               # 主应用组件
│   ├── index.css             # 全局样式
│   └── components/
│       ├── PropertySearch.tsx   # 搜索组件
│       └── PropertySearch.css   # 组件样式
├── static/                   # 旧版静态资源 (保留)
│   ├── js/app.js
│   └── css/style.css
└── index.html                # 旧版 HTML (保留)
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd /home/ling/Crawler/propertyguru-auto-searcher/web
npm install
```

### 2. Start Development Server

```bash
npm run dev
# or
./start-dev.sh
```

访问 http://localhost:3000

### 3. Build for Production

```bash
npm run build
```

## 🔧 Key Features

### 1. Streaming AI Responses

使用 `useXAgent` 处理后端 SSE 流式事件：

```typescript
const [agent] = useXAgent({
  request: async (info, callbacks) => {
    const { onUpdate, onSuccess, onError } = callbacks;
    
    // 处理 SSE 流
    const response = await fetch('/api/v1/search/stream', {
      method: 'POST',
      body: JSON.stringify({ query: message }),
    });
    
    // 实时更新 UI
    onUpdate('🤖 Parsing your query...');
    onUpdate('💭 AI is thinking...');
    onSuccess(results);
  },
});
```

### 2. Real-time Thinking Display

DeepSeek 的思考过程实时展示：

```typescript
case 'thinking':
  setCurrentThinking((prev) => prev + data.content);
  onUpdate(`💭 AI is thinking: ${currentThinking}`);
  break;
```

### 3. Property Results Display

使用 Ant Design 的高级组件展示房源：

```typescript
<Card hoverable className="property-card">
  <Statistic title="Price" value={property.price} prefix="S$" />
  <Tag color="purple">{score}% Match</Tag>
  <Button type="primary" onClick={viewDetails}>
    View Details
  </Button>
</Card>
```

## 📊 SSE Event Handling

| Event | Description | UI Update |
|-------|-------------|-----------|
| `start` | 搜索开始 | 🔍 Starting search... |
| `parsing` | 解析查询 | 🤖 Parsing your query... |
| `thinking` | AI 思考 | 💭 AI is thinking: ... |
| `content` | 内容分析 | 📝 Analyzing requirements... |
| `intent` | 意图解析 | ✅ Understood: bedrooms: 3, ... |
| `searching` | 数据库查询 | 🔎 Searching database... |
| `results` | 返回结果 | Found 42 properties in 123ms |
| `done` | 完成 | - |
| `error` | 错误 | ❌ Error message |

## 🎨 Customization

### Theme

修改 `src/App.tsx`:

```typescript
<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#667eea',  // 主色调
      borderRadius: 8,           // 圆角
    },
  }}
>
```

### Components

- `PropertySearch.tsx` - 主搜索界面
- `PropertySearch.css` - 自定义样式

## 🔄 Migration Path

### Old Frontend (保留)
- `index.html` - 原版 HTML
- `static/js/app.js` - 原版 JavaScript

### New Frontend (推荐)
- `index-new.html` - React 版入口
- `src/` - React + TypeScript 源码

**两个版本可以并存！** 方便对比和渐进式迁移。

## 📦 Dependencies

### Core
- **React 18** - UI 框架
- **@ant-design/x** - AI 对话组件
- **antd** - UI 组件库

### Build Tools
- **Vite** - 快速构建工具
- **TypeScript** - 类型安全
- **@vitejs/plugin-react** - React 支持

## 🚦 Backend Integration

Vite 配置自动代理 API 请求：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

## 🎯 Next Steps

1. ✅ 基础框架搭建完成
2. ✅ SSE 流式传输支持
3. ✅ AI 思考过程展示
4. ✅ 房源卡片展示
5. 🔲 添加更多过滤器 UI
6. 🔲 添加地图视图
7. 🔲 添加收藏功能
8. 🔲 添加比较功能

## 📝 Notes

- 后端必须运行在 `http://localhost:8080`
- 开发模式下 Vite 会自动代理 API 请求
- 生产环境需要配置 Nginx 或其他反向代理
- 确保后端支持 CORS（开发环境）

## 🐛 Troubleshooting

### Frontend 无法连接后端
```bash
# 检查后端是否运行
curl http://localhost:8080/api/v1/health

# 检查 Vite 配置
cat vite.config.ts
```

### 依赖安装失败
```bash
# 清理缓存重试
rm -rf node_modules package-lock.json
npm install
```

### TypeScript 错误
```bash
# 检查类型定义
npm list @types/react
npm list @ant-design/x
```

## 📚 Resources

- [Ant Design X GitHub](https://github.com/ant-design/x)
- [Ant Design X Docs](https://x.ant.design/)
- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)

## 🎉 Result

现在你拥有了一个**专业级的 AI 房产搜索界面**！

- ✅ 流式 AI 对话
- ✅ 实时思考过程
- ✅ 精美房源卡片
- ✅ 现代化设计
- ✅ TypeScript 类型安全
- ✅ 响应式布局

