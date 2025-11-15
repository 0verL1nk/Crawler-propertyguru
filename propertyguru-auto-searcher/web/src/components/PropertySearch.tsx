import React, { useState, useRef, useCallback } from "react";
import {
  AIChatDialogue,
  AIChatInput,
  chatInputToMessage,
} from "@douyinfe/semi-ui";
import {
  Card,
  Typography,
  Space,
  Tag,
  Divider,
  Button,
  Descriptions,
  Row,
  Col,
  Spin,
} from "@douyinfe/semi-ui";
import { IconHome, IconMapPin } from "@douyinfe/semi-icons";
import "./PropertySearch.css";

const { Title, Text } = Typography;

interface Property {
  listing_id: number;
  title: string;
  price?: number;
  price_per_sqft?: number;
  bedrooms?: number;
  bathrooms?: number;
  area_sqft?: number;
  unit_type?: string;
  location?: string;
  mrt_station?: string;
  mrt_distance_m?: number;
  score?: number;
  matched_reasons?: string[];
  listed_age?: string;
}

interface SearchResponse {
  results?: Property[];
  total?: number;
  intent?: any;
  took_ms?: number;
}

const PropertySearch: React.FC = () => {
  const [isSearching, setIsSearching] = useState(false);
  const [properties, setProperties] = useState<Property[] | null>(null); // null: 未搜索过，[]: 无结果
  const [searchStats, setSearchStats] = useState<{
    total: number;
    took: number;
  } | null>(null);
  const [messages, setMessages] = useState<any[]>([
    {
      id: "welcome",
      role: "assistant",
      name: "PropertyBot",
      content:
        '🏠 Welcome to AI Property Search! Describe your dream home and I\'ll find the perfect matches for you. Try something like "3-bedroom condo near MRT, budget under S$1.5M"...',
      status: "completed",
    },
  ]);

  // 只需要一个标志防止并发
  const isProcessingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = useCallback(async (props: any) => {
    // 如果正在处理请求，直接返回
    if (isProcessingRef.current) {
      console.log("[BLOCKED] Previous request still processing");
      return;
    }

    // 提取用户输入
    const message = chatInputToMessage(props);
    let content = "";
    
    if (typeof message.content === "string") {
      content = message.content;
    } else if (Array.isArray(message.content)) {
      content = message.content
        .filter((item: any) => item?.type === "message")
        .flatMap((item: any) => item.content || [])
        .filter((item: any) => item?.type === "input_text")
        .map((item: any) => item.text)
        .join("");
    }

    if (!content?.trim()) {
      console.error("[ERROR] Empty query");
      return;
    }

    console.log(`[SEARCH] Starting: "${content}"`);

    // 标记正在处理
    isProcessingRef.current = true;

    // 添加用户消息
    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      status: "completed",
    };

    const aiMessageId = `ai-${Date.now()}`;
    const aiMessage = {
      id: aiMessageId,
      role: "assistant",
      name: "PropertyBot",
      content: "🔍 Starting search...",
      status: "loading",
    };

    setMessages((prev) => [...prev, userMessage, aiMessage]);
    setIsSearching(true);
  // 不清空，等新结果返回后再替换

    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(`/api/v1/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          query: content,
          options: { top_k: 20, offset: 0, semantic: true },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const searchData: SearchResponse = await response.json();
      setProperties(searchData.results || []);
      setSearchStats({
        total: searchData.total || 0,
        took: searchData.took_ms || 0,
      });
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? {
                ...msg,
                content: `Found ${searchData.total} properties in ${searchData.took_ms}ms`,
                status: "completed",
              }
            : msg
        )
      );
      setIsSearching(false);
    } catch (error: any) {
      if (error.name === "AbortError") {
        console.log("[SEARCH] Aborted");
      } else {
        console.error("[SEARCH] Error:", error);
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            name: "PropertyBot",
            content: `❌ ${error.message}`,
            status: "failed",
          },
        ]);
        // 失败时不清空原有结果
        setIsSearching(false);
      }
    } finally {
      isProcessingRef.current = false;
      console.log("[SEARCH] Completed, ready for next request");
    }
  }, []);

  const renderPropertyCard = (property: Property) => (
    <Card key={property.listing_id} shadows="hover" style={{ marginBottom: 16 }} className="property-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", flexWrap: "wrap", gap: 8 }}>
        <Title heading={5} style={{ margin: 0, flex: "1 1 auto", minWidth: "60%" }}>
          {property.title}
        </Title>
        <Tag color="purple" style={{ flexShrink: 0 }}>{((property.score || 0) * 100).toFixed(0)}% Match</Tag>
      </div>

      <div style={{ margin: "12px 0" }}>
        <Descriptions row>
          <Descriptions.Item itemKey="Price">
            S${property.price?.toLocaleString() || "N/A"}
          </Descriptions.Item>
          <Descriptions.Item itemKey="Per sqft">
            S${property.price_per_sqft?.toLocaleString() || "N/A"}/sqft
          </Descriptions.Item>
        </Descriptions>
      </div>

      <Divider margin="12px" />

      <Row gutter={[16, 8]}>
        <Col xs={24} sm={8}>
          <Text type="secondary">Beds</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <IconHome />
            <span>{property.bedrooms || "-"}</span>
          </div>
        </Col>
        <Col xs={24} sm={8}>
          <Text type="secondary">Baths</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <IconHome />
            <span>{property.bathrooms || "-"}</span>
          </div>
        </Col>
        <Col xs={24} sm={8}>
          <Text type="secondary">Area</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <IconHome />
            <span>{property.area_sqft?.toFixed(0) || "-"} sqft</span>
          </div>
        </Col>
      </Row>

      <Space vertical align="start" style={{ marginTop: 8 }}>
        <Space>
          <IconHome />
          <Text>{property.unit_type || "N/A"}</Text>
        </Space>
        <Space>
          <IconMapPin />
          <Text>{property.location || "N/A"}</Text>
        </Space>
        {property.mrt_station && (
          <Space>
            <Text type="tertiary">
              🚇 {property.mrt_station} ({property.mrt_distance_m}m)
            </Text>
          </Space>
        )}
        {property.matched_reasons && property.matched_reasons.length > 0 && (
          <div>
            <Text type="success">✓ {property.matched_reasons.join(" · ")}</Text>
          </div>
        )}
        {property.listed_age && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            📅 {property.listed_age}
          </Text>
        )}
      </Space>

      <div style={{ marginTop: 16 }}>
        <Button
          theme="solid"
          block
          onClick={() =>
            window.open(
              `https://www.propertyguru.com.sg/listing/${property.listing_id}`,
              "_blank"
            )
          }
        >
          View Details
        </Button>
      </div>
    </Card>
  );

  const roleConfig = {
    user: {
      name: "You",
      avatar: "https://lf3-static.bytednsdoc.com/obj/eden-cn/22606991eh7uhfups/img/user.png",
    },
    assistant: new Map([
      [
        "PropertyBot",
        {
          name: "PropertyBot",
          avatar:
            "https://lf3-static.bytednsdoc.com/obj/eden-cn/22606991eh7uhfups/img/robot.png",
        },
      ],
    ]),
  };

  // 自定义渲染Bot消息，显示加载环
  const renderMessage = useCallback((message: any) => {
    const msg = message.message || message;
    if (msg.role === "assistant" && msg.status === "loading") {
      return (
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Spin size="small" />
          <Text>{msg.content}</Text>
        </div>
      );
    }
    return msg.content;
  }, []);

  return (
    <div className="property-search-container">
      <div className="header">
        <Title heading={2} style={{ margin: 0, color: "white" }}>
          🏠 AI Property Search
        </Title>
        <Text style={{ color: "rgba(255,255,255,0.9)" }}>
          Find your dream home using natural language
        </Text>
      </div>

      <div className="content-wrapper">
        <div>
          {properties !== null && (
            <div className="properties-results-container">
              {isSearching ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minHeight: 320,
                    background: "var(--semi-color-bg-1)",
                    borderRadius: "8px",
                    marginBottom: "16px",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                  }}
                >
                  <Spin size="large" tip="Searching properties..." />
                </div>
              ) : (
                properties.length > 0 && (
                  <>
                    <div
                      style={{
                        flex: "0 0 auto",
                        padding: "16px",
                        background: "var(--semi-color-bg-1)",
                        borderRadius: "8px",
                        marginBottom: "16px",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                      }}
                    >
                      <Space>
                        <Text strong style={{ fontSize: "16px" }}>
                          Found {searchStats?.total} properties
                        </Text>
                        <Text type="tertiary" style={{ fontSize: "14px" }}>
                          in {searchStats?.took}ms
                        </Text>
                      </Space>
                    </div>
                    <div
                      style={{
                        flex: 1,
                        overflow: "auto",
                        background: "var(--semi-color-bg-1)",
                        borderRadius: "8px",
                        padding: "16px",
                      }}
                    >
                      <Title heading={4} style={{ margin: "0 0 16px 0" }}>
                        Search Results
                      </Title>
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                        {properties.map(renderPropertyCard)}
                      </div>
                    </div>
                  </>
                )
              )}
            </div>
          )}

          <div className="ai-chat-section">
            <div className="ai-chat-container">
              <AIChatDialogue
                style={{ flex: 1, overflow: "auto", padding: "20px" }}
                roleConfig={roleConfig}
                chats={messages}
                align="leftRight"
                mode="bubble"
                renderMessage={renderMessage}
              />
            </div>

            <div
              style={{
                flex: "0 0 auto",
                padding: "16px",
                backgroundColor: "var(--semi-color-bg-0)",
                borderTop: "1px solid var(--semi-color-border)",
                marginTop: "16px",
                borderRadius: "8px",
              }}
            >
              <AIChatInput
                placeholder="e.g., I want a 3-bedroom condo near MRT, budget under S$1.5M..."
                generating={isSearching}
                onMessageSend={handleSendMessage}
                onStopGenerate={() => setIsSearching(false)}
                style={{ maxWidth: "100%", margin: "0 auto" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PropertySearch;
