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
} from "@douyinfe/semi-ui";
import { IconHome, IconMapPin } from "@douyinfe/semi-icons";
import "./PropertySearch.css";

const { Title, Text } = Typography;

interface SearchFilters {
  price_min?: number;
  price_max?: number;
  bedrooms?: number;
  bathrooms?: number;
  unit_type?: string;
  location?: string;
  mrt_distance_max?: number;
}

interface IntentSlots extends SearchFilters {}

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
  intent?: {
    slots?: IntentSlots;
    semantic_keywords?: string[];
  };
  took_ms?: number; // Backend uses took_ms not took
}

const PropertySearch: React.FC = () => {
  const [isSearching, setIsSearching] = useState(false);
  const [properties, setProperties] = useState<Property[]>([]);
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

  // Track the active fetch request so we can cancel stale streams when user asks again
  const activeFetchControllerRef = useRef<AbortController | null>(null);
  // Track the latest request ID to ignore stale responses
  const latestRequestIdRef = useRef<number>(0);

  // Handle sending messages
  const handleSendMessage = useCallback(async (props: any) => {
    // Debug log the raw props structure
    console.log("[DEBUG] Raw chat input props:", props);
    console.log(
      "[DEBUG] Raw chat input props (JSON):",
      JSON.stringify(props, null, 2)
    );
    console.log("[DEBUG] Props type:", typeof props);
    console.log(
      "[DEBUG] Props keys:",
      props ? Object.keys(props) : "null/undefined"
    );

    // Use chatInputToMessage to convert props to a standard message format
    let message: any = null;
    try {
      message = chatInputToMessage(props);
      console.log("[DEBUG] Converted message:", message);
      console.log(
        "[DEBUG] Converted message (JSON):",
        JSON.stringify(message, null, 2)
      );
    } catch (error) {
      console.error(
        "[ERROR] Failed to convert props with chatInputToMessage:",
        error
      );
    }

    // Extract content from the converted message
    let content = "";
    if (message && message.content) {
      if (typeof message.content === "string") {
        content = message.content;
        console.log(
          "[DEBUG] Extracted from converted message.content (string):",
          content
        );
      } else if (Array.isArray(message.content)) {
        // If content is an array, extract text from input_text items
        // The structure is: [{type: "message", role: "user", content: [{type: "input_text", text: "..."}]}]
        content = message.content
          .filter(
            (item: any) => item && item.type === "message" && item.content
          )
          .flatMap((item: any) => item.content)
          .filter((item: any) => item && item.type === "input_text")
          .map((item: any) => item.text)
          .join("");
        console.log(
          "[DEBUG] Extracted from converted message.content (array):",
          content
        );
      }
    }

    // If chatInputToMessage didn't work or didn't produce content, fall back to our manual extraction
    if (!content) {
      console.log("[DEBUG] Falling back to manual extraction...");

      if (typeof props === "string") {
        content = props;
        console.log("[DEBUG] Extracted from string:", content);
      } else if (props && props.inputValue) {
        // Direct input value from AIChatInput
        content = props.inputValue;
        console.log("[DEBUG] Extracted from inputValue:", content);
      } else if (
        props &&
        props.inputContents &&
        Array.isArray(props.inputContents)
      ) {
        // If it's an array of input contents, extract the text
        // The structure is: [{type: "text", text: "..."}]
        content = props.inputContents
          .filter((item: any) => item.type === "text")
          .map((item: any) => item.text)
          .join("");
        console.log("[DEBUG] Extracted from inputContents array:", content);
      } else if (props && typeof props === "object" && props.content) {
        // Handle case where props is an object with content property
        if (typeof props.content === "string") {
          content = props.content;
          console.log(
            "[DEBUG] Extracted from props.content (string):",
            content
          );
        } else if (Array.isArray(props.content)) {
          // If content is an array, extract text from input_text items
          content = props.content
            .filter((item: any) => item && item.type === "input_text")
            .map((item: any) => item.text)
            .join("");
          console.log("[DEBUG] Extracted from props.content (array):", content);
        }
      } else if (props && Array.isArray(props)) {
        // Handle case where props is directly an array
        content = props
          .filter((item: any) => item && item.type === "input_text")
          .map((item: any) => item.text)
          .join("");
        console.log("[DEBUG] Extracted from props array:", content);
      } else {
        // Fallback - try to convert to string
        content = String(props);
        console.log("[DEBUG] Extracted via String():", content);

        // Special case: if props is an object with a toString() method that returns '[object Object]'
        if (
          content === "[object Object]" &&
          props &&
          typeof props === "object"
        ) {
          console.log(
            "[DEBUG] Props is an object with no meaningful string representation"
          );
          // Try to find any text-like property
          const possibleTextProps = [
            "text",
            "value",
            "message",
            "query",
            "input",
          ];
          for (const prop of possibleTextProps) {
            if (props[prop] && typeof props[prop] === "string") {
              content = props[prop];
              console.log(`[DEBUG] Found text in props.${prop}:`, content);
              break;
            }
          }
        }
      }
    }

    // Additional debug logs for complex structures
    console.log("[DEBUG] Final extracted content:", content);
    console.log("[DEBUG] Content type:", typeof content);
    console.log("[DEBUG] Content length:", content.length);

    // Validate content before sending
    if (!content || content.length === 0) {
      console.error("[ERROR] Extracted content is empty!");
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        name: "PropertyBot",
        content:
          "❌ Error: Empty search query. Please enter a valid search query.",
        status: "failed",
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    if (content.length > 1000) {
      console.warn(
        "[WARN] Content is very long:",
        content.length,
        "characters"
      );
    }

    // Add user message to chat
    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: content,
      status: "completed",
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSearching(true);

    // Clear properties and stats for new search
    console.log("[DEBUG] Clearing properties and stats for new search");
    setProperties([]);
    setSearchStats(null);
    console.log("[DEBUG] Properties and stats cleared");

    try {
      // Abort any in-flight request before starting a new one
      if (activeFetchControllerRef.current) {
        console.log("[DEBUG] Aborting previous search request");
        activeFetchControllerRef.current.abort();
        activeFetchControllerRef.current = null;
      }

      const controller = new AbortController();
      activeFetchControllerRef.current = controller;

      // Debug log the request
      console.log("[DEBUG] Sending search request:", {
        query: content,
        options: {
          top_k: 20,
          offset: 0,
          semantic: true,
        },
      });

      const response = await fetch(`/api/v1/search/stream?t=${Date.now()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-cache, no-store, must-revalidate",
          Pragma: "no-cache",
          Expires: "0",
        },
        cache: "no-store",
        signal: controller.signal,
        body: JSON.stringify({
          query: content,
          options: {
            top_k: 20,
            offset: 0,
            semantic: true,
          },
        }),
      });

      // Check if response is OK
      if (!response.ok) {
        const errorText = await response.text();
        console.error(
          "[ERROR] Search API error:",
          response.status,
          response.statusText,
          errorText
        );
        throw new Error(
          `Search failed: ${response.status} ${response.statusText} - ${errorText}`
        );
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response body");
      }

      let buffer = "";
      let streamEnded = false;
      let aiMessageId = `ai-${Date.now()}`;
      let aiMessageContent = "";
      const requestId = ++latestRequestIdRef.current;

      console.log(`[DEBUG] Starting request ${requestId}, aiMessageId: ${aiMessageId}`);

      // Add initial AI message
      const initialAiMessage = {
        id: aiMessageId,
        role: "assistant",
        name: "PropertyBot",
        content: "🔍 Starting search...",
        status: "loading",
      };

      setMessages((prev) => [...prev, initialAiMessage]);

      while (!streamEnded) {
        const { done, value } = await reader.read();
        if (done) {
          streamEnded = true;
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        // Process lines in pairs: event + data
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (!line.trim()) continue;

          // Check if this is an event line
          if (line.startsWith("event:")) {
            const eventMatch = line.match(/event:\s*(\w+)/);
            if (!eventMatch) continue;

            const event = eventMatch[1];

            // Look for the data line (next non-empty line)
            let dataLine = "";
            for (let j = i + 1; j < lines.length; j++) {
              if (lines[j].trim()) {
                dataLine = lines[j];
                i = j; // Skip to this line in the outer loop
                break;
              }
            }

            if (!dataLine.startsWith("data:")) continue;

            const dataMatch = dataLine.match(/data:\s*(.+)/);
            if (!dataMatch) continue;

            try {
              const data = JSON.parse(dataMatch[1]);

              // 使用本地的 aiMessageId 来更新对应的消息，不依赖全局 ref
              // 这样每个流都能独立完成，互不干扰

              switch (event) {
                case "start":
                  aiMessageContent = "🔍 Starting search...";
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, content: aiMessageContent }
                        : msg
                    )
                  );
                  break;

                case "parsing":
                  aiMessageContent = "🤖 Parsing your query with AI...";
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, content: aiMessageContent }
                        : msg
                    )
                  );
                  break;

                case "thinking":
                  if (data.content) {
                    aiMessageContent += data.content;
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === aiMessageId
                          ? {
                              ...msg,
                              content: `💭 Thinking: ${aiMessageContent}`,
                            }
                          : msg
                      )
                    );
                  }
                  break;

                case "content":
                  if (data.content) {
                    aiMessageContent += data.content;
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === aiMessageId
                          ? {
                              ...msg,
                              content: `📝 Parsing: ${aiMessageContent}`,
                            }
                          : msg
                      )
                    );
                  }
                  break;

                case "intent":
                  const slots = data.slots || {};
                  const filters = Object.entries(slots)
                    .filter(([_, v]) => v !== null && v !== undefined)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(", ");
                  aiMessageContent = `✅ Understood: ${
                    filters || "General search"
                  }`;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, content: aiMessageContent }
                        : msg
                    )
                  );
                  break;

                case "searching":
                  aiMessageContent = "🔎 Searching database...";
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, content: aiMessageContent }
                        : msg
                    )
                  );
                  break;

                case "results": {
                  const searchData: SearchResponse = data;
                  console.log(`[DEBUG] Request ${requestId} received results:`, searchData);
                  
                  // 只有最新的请求才更新全局房源列表
                  if (requestId === latestRequestIdRef.current) {
                    console.log(`[DEBUG] Request ${requestId} is latest, updating properties`);
                    setProperties(searchData.results || []);
                    setSearchStats({
                      total: searchData.total || 0,
                      took: searchData.took_ms || 0,
                    });
                    setIsSearching(false);
                    activeFetchControllerRef.current = null;
                  } else {
                    console.log(`[DEBUG] Request ${requestId} is stale (latest: ${latestRequestIdRef.current}), ignoring`);
                  }
                  
                  // 更新这个流对应的消息状态（无论是否最新）
                  aiMessageContent = `Found ${searchData.total} properties in ${searchData.took_ms}ms`;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? {
                            ...msg,
                            content: aiMessageContent,
                            status: "completed",
                          }
                        : msg
                    )
                  );
                  break;
                }

                case "error":
                  aiMessageContent = `❌ Search failed: ${
                    data.error || "Unknown error"
                  }`;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? {
                            ...msg,
                            content: aiMessageContent,
                            status: "failed",
                          }
                        : msg
                    )
                  );
                  if (requestId === latestRequestIdRef.current) {
                    setIsSearching(false);
                    activeFetchControllerRef.current = null;
                  }
                  streamEnded = true;
                  break;

                case "done":
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, status: "completed" }
                        : msg
                    )
                  );
                  if (requestId === latestRequestIdRef.current) {
                    setIsSearching(false);
                    activeFetchControllerRef.current = null;
                  }
                  streamEnded = true;
                  break;
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e, dataMatch[1]);
            }
          }
        }
      }
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        console.log("[DEBUG] Search request aborted");
      } else {
        console.error("Search error:", error);
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          name: "PropertyBot",
          content: `❌ Search failed: ${
            error instanceof Error ? error.message : "Unknown error"
          }`,
          status: "failed",
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
      setIsSearching(false);
      activeFetchControllerRef.current = null;
    } finally {
      // Always close the reader when done
      // Note: In a real implementation, you would properly close the reader
    }
  }, []);

  const renderPropertyCard = (property: Property) => (
    <Card
      key={property.listing_id}
      shadows="hover"
      style={{ marginBottom: 16 }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "start",
        }}
      >
        <Title heading={5} style={{ margin: 0, flex: 1 }}>
          {property.title}
        </Title>
        <Tag color="purple">
          {((property.score || 0) * 100).toFixed(0)}% Match
        </Tag>
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
        <Col span={8}>
          <Text type="secondary">Beds</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <IconHome />
            <span>{property.bedrooms || "-"}</span>
          </div>
        </Col>
        <Col span={8}>
          <Text type="secondary">Baths</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <IconHome />
            <span>{property.bathrooms || "-"}</span>
          </div>
        </Col>
        <Col span={8}>
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

  // Role configuration for AIChatDialogue
  const roleConfig = {
    user: {
      name: "You",
      avatar:
        "https://lf3-static.bytednsdoc.com/obj/eden-cn/22606991eh7uhfups/img/user.png",
    },
    assistant: new Map([
      [
        "PropertyBot",
        {
          name: "PropertyBot",
          avatar:
            "https://lf3-static.bytednsdoc.com/obj/eden-cn/22606991eh7uhfups/img/default_icon.png",
        },
      ],
    ]),
  };

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
        {/* 主内容区域 - 左右分栏布局 (房产结果:AI对话 = 2:1) */}
        <div>
          {/* 左侧房产结果区域 - 仅在有结果时显示 */}
          {properties.length > 0 && (
            <div className="properties-results-container">
              {/* 搜索统计 */}
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

              {/* 属性结果列表 */}
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
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "16px",
                  }}
                >
                  {properties.map(renderPropertyCard)}
                </div>
              </div>
            </div>
          )}

          {/* 右侧AI对话区域 - 始终显示 */}
          <div className="ai-chat-section">
            <div className="ai-chat-container">
              <AIChatDialogue
                style={{
                  flex: 1,
                  overflow: "auto",
                  padding: "20px",
                }}
                roleConfig={roleConfig}
                chats={messages}
                align="leftRight"
                mode="bubble"
              />
            </div>

            {/* 输入区域 */}
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
