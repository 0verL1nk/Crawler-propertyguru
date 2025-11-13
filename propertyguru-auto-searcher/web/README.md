# PropertyGuru AI Search Frontend

基于 **Ant Design X** 构建的 AI 驱动房产搜索界面。

## 🚀 特性

- ✅ **流式 AI 对话** - 实时显示 AI 思考过程和搜索结果
- ✅ **专业 UI 组件** - 使用 Ant Design X 的 Bubble、Sender 等组件
- ✅ **智能搜索** - 支持自然语言查询
- ✅ **实时更新** - SSE 流式传输，即时反馈
- ✅ **响应式设计** - 适配各种屏幕尺寸

## 📦 安装

```bash
npm install
# or
yarn install
# or
pnpm install
```

## 🛠️ 开发

```bash
npm run dev
```

访问 http://localhost:3000

后端 API 会自动代理到 http://localhost:8080

## 🏗️ 构建

```bash
npm run build
```

构建产物在 `dist/` 目录

## 📝 使用示例

```
Query: "I want a 3-bedroom condo near MRT, budget under S$1.2M"

AI 会：
1. 💭 显示思考过程（DeepSeek thinking mode）
2. ✅ 解析意图（bedrooms: 3, unit_type: "Condo", ...）
3. 🔎 搜索数据库
4. 📊 显示结果列表
```

## 🔧 技术栈

- **React 18** - UI 框架
- **Ant Design X** - AI 对话组件
- **Ant Design 5** - UI 组件库
- **TypeScript** - 类型安全
- **Vite** - 构建工具

## 📚 主要组件

### PropertySearch
主搜索界面组件，集成：
- `useXAgent` - AI 代理管理
- `useXChat` - 聊天数据流
- `Bubble.List` - 消息列表
- `Sender` - 输入框

### SSE Events
后端流式事件：
- `start` - 开始搜索
- `parsing` - 解析查询
- `thinking` - AI 思考过程
- `content` - 内容生成
- `intent` - 意图解析完成
- `searching` - 数据库查询
- `results` - 搜索结果
- `done` - 完成

## 🎨 自定义

修改 `src/App.tsx` 中的主题配置：

```tsx
<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#667eea', // 主题色
      borderRadius: 8,         // 圆角
    },
  }}
>
```

## 📄 License

MIT

