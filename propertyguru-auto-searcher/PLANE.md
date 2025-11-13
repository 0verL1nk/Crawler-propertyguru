
## 一、项目背景

当前房产搜索平台普遍采用基于关键词和结构化过滤的检索方式（例如价格区间、房型、地铁距离等）。
然而，用户在实际使用过程中越来越倾向于**自然语言表达需求**，例如：

> “我想找靠近地铁的三房新公寓，预算 120 万以内，最好采光好一点。”

传统 SQL 或关键词匹配方案在此类模糊表达下会出现以下问题：

1. **语义理解缺失**
   系统无法理解“采光好”“靠近地铁”等语义型描述，只能依赖字段匹配，导致召回率低。

2. **检索粒度粗**
   数据库字段往往是结构化的（price、bedrooms、distance），但很多重要的房源特征存在于非结构化文本中（description、title、amenities），传统查询无法利用。

3. **用户体验割裂**
   用户需要在多层筛选条件间反复切换，缺乏自然对话式或一体化搜索体验。

4. **难以智能推荐与解释**
   搜索结果缺乏语义相关度和解释依据，难以自动生成“推荐理由”或“对比说明”。

---

## 二、项目目标

本项目旨在基于 **Golang + 语义检索（Embedding + 向量数据库）** 构建一个面向房产场景的智能搜索系统，实现从自然语言到结构化查询的自动映射和融合排序，提升搜索体验与转化率。

具体目标如下：

1. **语义理解能力**
   支持从自然语言中自动提取房型、预算、地理偏好等结构化条件，并理解模糊描述（如“采光好”“适合家庭”）。

2. **混合检索机制**
   结合属性过滤（SQL）与语义检索（向量搜索），在精确约束下实现语义召回。

3. **智能排序与解释**
   通过加权或学习排序模型输出最符合意图的房源，并能生成自然语言解释（如“推荐因为靠近地铁且采光良好”）。

4. **可扩展与可维护性**
   架构层次清晰，易于后续接入 RAG、个性化推荐、对话式搜索等功能。

---

## 三、建设意义

* **对用户：**
  提供更自然、智能的找房体验，减少反复筛选的成本，提升满意度与成交转化率。

* **对业务：**
  通过智能排序和推荐，提高优质房源曝光率；通过日志与反馈数据闭环，不断优化搜索质量。

* **对系统演进：**
  为后续引入多模态检索（图像、视频）、推荐系统与知识问答打下基础。

---

## 四、项目范围（MVP 阶段）

* 支持自然语言搜索与结构化筛选共存。
* 支持房源属性过滤（价格、卧室数、完成状态、地铁距离）。
* 支持语义相似度检索与属性融合排序。
* 提供 RESTful API 接口（/search、/intent、/feedback）。
* 实现基础日志采集与性能监控。


# 一、总体架构（高层概念）

1. 前端（Vue3）：用户用自然语言或表单提交查询 → 调用后端 REST API。
2. 后端（Go 服务群组）：

   * 意图解析服务（NLU）
   * 属性过滤服务（SQL 层，PostgreSQL）
   * 语义检索服务（向量检索，pgvector/Pinecone/Milvus）
   * 排序与融合服务（Hybrid Ranker）
   * （可选）RAG/解释服务（调用 LLM 生成自然语言解释）
   * 日志/反馈采集（search_logs）
3. 存储：

   * 关系 DB（listing_info / listing_media）
   * 向量 DB（embedding 存储与检索）
   * 缓存（Redis）
4. 观测：Prometheus/Grafana、日志（ELK）、Tracing（Jaeger）

---

# 二、核心数据流（逐步描述）

1. **用户输入**：前端发送 `{ query: string, filters?: {...}, options?: {...} }` 到 `/search`。
2. **Intent Parser（可选）**：

   * 目标：把自然语言拆成 `intent` + `slots`（price_min/max, bedrooms, mrt_distance, unit_type 等）。
   * 实现思路：优先用轻量规则+正则快速抽取数值/单位，再用 LLM 校正或处理复杂语句。输出 JSON slots。
3. **属性过滤（SQL）**：

   * 根据 slots 组装安全的参数化 SQL（或使用 ORM/sqlx）。
   * 先做结构化过滤（价格、卧室、是否完成、地理范围），把候选集缩到可控规模（例如 ≤ 5k）。
   * 这一步保证硬约束（必须满足的条件）不会被语义检索破坏。
4. **语义搜索（向量检索）**：

   * 生成 query embedding（若 query 含有模糊需求或 user 指定 semantic）。
   * 在向量 DB 中以 `top_k` 搜索，但用 filter 限制 listing_id 在上一步得到的候选集内（metadata filter）。
   * 向量库返回每条的相似度分值和对应 text chunk（若需要 RAG）。
5. **融合与排序（Hybrid Ranker）**：

   * 计算并归一化多个分数：语义相似度、属性匹配度（精确/部分/不匹配）、价格接近度、recency、业务加权（例如 is_completed 优先）。
   * 合成最终得分并排序。
   * 可以在此插入业务规则（黑名单、推广位）或学习排序模型（后期）。
6. **可选 RAG/解释**：

   * 若用户请求解释/对比，从向量检索取 top-N 文本片段作为 context，调用 LLM 生成自然语言推荐/对比，**并在回答中列明来源 listing_id** 以避免幻觉。
7. **返回给前端**：

   * 列表结果（每条包含基本字段、score、matched_reasons snippets、source link）。
   * 同时记录 `search_logs`（query、slots、returned ids、clicked id 等）供训练/优化。

---

# 三、关键模块职责与实现要点（思路，不写代码）

## 1) 意图解析（NLU）

* 主要职责：把自由文本转为结构化查询条件（slots），并输出信心水平。
* 思路：

  * 首先用轻量正则提取数值（价格、卧室、距离、年份）。
  * 对语义模糊或复杂需求（“适合家庭、采光好”）标注为需要语义检索的标签。
  * 用 LLM 执行补充/纠错（可做为 fallback 或增强），并将最终 slots 返回。
* 输出：`{intent:"search", slots:{...}, semantic_needed: bool}`

## 2) SQL 过滤层（属性筛选）

* 目的：执行硬约束，高效缩小候选集。
* 要点：

  * 使用参数化查询防注入。
  * 建索引（price, bedrooms, mrt_distance_m, is_completed, unit_type）。
  * 对地理查询用 radius/bounding-box（若有 lat/lon）。
  * 限制返回 id 数量（例如 LIMIT 5000）以便后面向量操作。

## 3) Embedding & 向量检索

* Embedding 策略：

  * 合并字段：`title + description + amenities + property_details` 为检索文本。
  * Chunking：对过长文本切分成段落并为每段生成 embedding，保存 chunk metadata（listing_id, chunk_index）。
  * 模型：可以用 OpenAI embeddings 或自托管模型，维度与性能由成本决定。
* 向量库：

  * 推荐 HNSW index（在线低延迟、召回率好）。
  * 在检索时使用 metadata filter（限制 listing_id 在 SQL 候选集）。
* 实际检索流程：用 query embedding 搜索 top_k（比如 200），返回 id+score+chunk。

## 4) 融合排序（Hybrid）

* 核心：把“精确匹配”与“语义相似”合成一个最终分数。
* 常见做法：

  * 先归一化每类分数（0-1）。
  * 给定初始权重（例如 semantic 0.65，attribute 0.30，recency 0.05），线性加权。
  * 若有业务或推广候选，按规则插入或增权。
* 迭代优化：用 search_logs 训练 LambdaMART/LightGBM 等 Learning-to-Rank 模型。

## 5) RAG / 解释生成（可选）

* 只在用户需要自然语言解释或对比时触发，避免每次调用 LLM 增加成本。
* 步骤：

  * 从向量检索获取支持片段（带 listing_id）。
  * 构造 prompt（system: 不允许捏造；user: 给出 query 与 context）。
  * LLM 输出解释，并附上 sources（listing_id）。
* 必要性：增强可信度与用户体验，但成本较高。

---

# 四、工程与部署要点（生产化考虑）

## 性能与可扩展性

* **分层限流**：前端/网关限流 + 后端熔断（避免 LLM/向量库被突发流量压垮）。
* **缓存**：Redis 缓存热门 query 的结果（短时有效），或缓存向量检索 top-N id 列表。
* **异步 ETL**：Embedding 更新放入后台任务队列（Celery/Go worker），做增量更新。
* **并发**：Go 的 goroutine + 连接池（DB/向量库）保证并发。

## 可观测性

* 基本指标：/search 延迟 P50/P95、向量库查询时延、LLM 调用时延、错误率、CTR、contact rate。
* 日志：记录 query、slots、candidate_ids、returned_ids、clicked_id（隐私合规下）。
* A/B：跑不同权重组合或新 ranker 的 A/B 测试。

## 安全&合规

* 对敏感字段（用户 ID、IP）做脱敏/加密存储。
* LLM 输出加上来源引用，避免幻觉造成法律/信任问题。
* 根据地区法规（如新加坡 PDPA）保护个人数据。

---

# 五、工程优先级（MVP 到进阶路线）

## MVP（最小可行）

1. 前端最简单搜索框 + 结构化筛选 UI。
2. 后端：

   * 基于规则的意图/slot 提取（正则/简单 NLP）。
   * SQL 属性过滤（完成、价格、卧室、地铁距离）。
   * 基本文本全文检索（PostgreSQL fulltext）或初期不做向量，仅用 fulltext。
   * 返回排序（价格/上架时间）。
3. 保存 search_logs。

**目标**：快速上线、验证用户需求与查询分布。

## Phase 2（语义增强）

1. 引入 Embedding（对 listing 文本做离线 embedding）。
2. 集成向量库（pgvector/Pinecone），实现 semantic search。
3. 实现融合排序（属性+语义）。
4. 在前端展示 matched_reasons。

**目标**：提升对模糊需求（采光、装修风格等）的召回与匹配质量。

## Phase 3（智能化）

1. RAG（按需启用）用于生成推荐理由/对比报告。
2. 用 search_logs 训练 Learning-to-Rank。
3. 个性化推荐（基于用户历史行为）。

---

# 六、接口契约（简要，便于前端/后端对接）

* `POST /api/v1/search`

  * Input:

    ```json
    { "query": "我想找三房靠近地铁", "filters": { "price_max": 1200000, "bedrooms": 3 }, "semantic": true, "top_k": 20 }
    ```
  * Output:

    ```json
    { "results": [
        { "listing_id": 60157325, "title": "...", "price": 1150000, "score": 0.92, "matched_reasons":["靠近地铁","三房","描述含“采光”"] },
        ...
      ],
      "intent": { "slots": {...} }
    }
    ```

* `POST /api/v1/intent`（可选）

  * Return: `{ "slots": {...}, "semantic_needed": true }`

* `POST /api/v1/feedback`

  * 用于接收点击/联系等行为，写入 search_logs。

---

# 七、指标与优化闭环

* 初期用 CTR、contact_rate、top-K 点击率、搜索延迟评估效果。
* 收集失败案例（用户反馈“不相关”），用作微调意图提取或优化 embedding 文本拼接策略。
* 定期（例如每月）评估 embedding 模型效果（召回@K），必要时更换 embedding 模型或调整 chunk 大小。

---

# 八、总结（一句话）

用 Go 的实现思路就是：**先用结构化过滤保证精确性 → 在可控候选集里做语义检索提高召回 → 用可解释的混合排序输出结果 → 按需用 RAG 生成解释**。按 MVP→语义增强→智能化的路线迭代，优先解决硬约束（价格、卧室、地理）再逐步投入 LLM 成本以提高用户体验。

