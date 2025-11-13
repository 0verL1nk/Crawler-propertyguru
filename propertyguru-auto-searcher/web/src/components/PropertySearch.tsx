import React, { useState, useRef } from 'react';
import { Bubble, Sender, useXChat, useXAgent } from '@ant-design/x';
import type { SenderRef } from '@ant-design/x';
import { Card, Typography, Space, Tag, Divider, Button, Statistic, Row, Col } from 'antd';
import {
  HomeOutlined,
  EnvironmentOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import './PropertySearch.css';

const { Title, Text, Paragraph } = Typography;

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
  took_ms?: number;  // Backend uses took_ms not took
}

const PropertySearch: React.FC = () => {
  const [isSearching, setIsSearching] = useState(false);
  const [currentThinking, setCurrentThinking] = useState('');
  const [currentContent, setCurrentContent] = useState('');
  const [properties, setProperties] = useState<Property[]>([]);
  const [searchStats, setSearchStats] = useState<{ total: number; took: number } | null>(null);
  const [searchKey, setSearchKey] = useState(0); // Force re-render
  const senderRef = useRef<SenderRef>(null);
  const [inputValue, setInputValue] = useState('');

  const [agent] = useXAgent({
    request: async (info, callbacks) => {
      const { message } = info;
      const { onUpdate, onSuccess, onError } = callbacks;

      console.log('[DEBUG] 🆕 New search started, clearing all states');

      // Clear all states immediately and increment search key
      setSearchKey(prev => prev + 1);
      setIsSearching(true);
      setCurrentThinking('');
      setCurrentContent('');
      setProperties([]);
      setSearchStats(null);

      console.log('[DEBUG] ✅ All states cleared, searchKey incremented');

      let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

      try {
        const response = await fetch(`/api/v1/search/stream?t=${Date.now()}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
          },
          cache: 'no-store',
          body: JSON.stringify({
            query: message,
            options: {
              top_k: 20,
              offset: 0,
              semantic: true,
            },
          }),
        });

        reader = response.body?.getReader() || null;
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let buffer = '';
        let streamEnded = false;

        while (!streamEnded) {
          const { done, value } = await reader.read();
          if (done) {
            streamEnded = true;
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          // Process lines in pairs: event + data
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (!line.trim()) continue;

            // Check if this is an event line
            if (line.startsWith('event:')) {
              const eventMatch = line.match(/event:\s*(\w+)/);
              if (!eventMatch) continue;

              const event = eventMatch[1];

              // Look for the data line (next non-empty line)
              let dataLine = '';
              for (let j = i + 1; j < lines.length; j++) {
                if (lines[j].trim()) {
                  dataLine = lines[j];
                  i = j; // Skip to this line in the outer loop
                  break;
                }
              }

              if (!dataLine.startsWith('data:')) continue;

              const dataMatch = dataLine.match(/data:\s*(.+)/);
              if (!dataMatch) continue;

              try {
                const data = JSON.parse(dataMatch[1]);

                switch (event) {
                  case 'start':
                    onUpdate('🔍 Starting search...');
                    break;

                  case 'parsing':
                    onUpdate('🤖 Parsing your query with AI...');
                    break;

                  case 'thinking':
                    if (data.content) {
                      setCurrentThinking((prev) => {
                        const newThinking = prev + data.content;
                        console.log('[DEBUG] Thinking accumulated:', newThinking);
                        onUpdate(`💭 Thinking: ${newThinking}`);
                        return newThinking;
                      });
                    }
                    break;

                  case 'content':
                    if (data.content) {
                      setCurrentContent((prev) => {
                        const newContent = prev + data.content;
                        console.log('[DEBUG] Content accumulated:', newContent);
                        onUpdate(`📝 Parsing: ${newContent}`);
                        return newContent;
                      });
                    }
                    break;

                  case 'intent':
                    const slots = data.slots || {};
                    const filters = Object.entries(slots)
                      .filter(([_, v]) => v !== null && v !== undefined)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(', ');
                    onUpdate(`✅ Understood: ${filters || 'General search'}`);
                    break;

                  case 'searching':
                    onUpdate('🔎 Searching database...');
                    break;

                  case 'results':
                    const searchData: SearchResponse = data;
                    setProperties(searchData.results || []);
                    setSearchStats({
                      total: searchData.total || 0,
                      took: searchData.took_ms || 0,
                    });

                    const resultText = `Found ${searchData.total} properties in ${searchData.took_ms}ms`;
                    onUpdate(resultText);
                    onSuccess(resultText);
                    break;

                  case 'error':
                    onError(new Error(data.error || 'Search failed'));
                    setIsSearching(false);
                    streamEnded = true;
                    break;

                  case 'done':
                    console.log('[DEBUG] Stream done event received');
                    setIsSearching(false);
                    streamEnded = true;
                    break;
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e, dataMatch[1]);
              }
            }
          }
        }
      } catch (error) {
        console.error('Search error:', error);
        onError(error as Error);
        setIsSearching(false);
      } finally {
        // Always close the reader when done
        if (reader) {
          try {
            await reader.cancel();
            console.log('[DEBUG] Stream reader closed');
          } catch (e) {
            console.error('Failed to close reader:', e);
          }
        }
      }
    },
  });

  const { messages, onRequest } = useXChat({ agent });

  const formatProperties = (props: Property[]): string => {
    if (props.length === 0) return 'No properties found.';
    return props
      .slice(0, 3)
      .map(
        (p, i) =>
          `${i + 1}. ${p.title}\n   📍 ${p.location}\n   💰 S$${p.price?.toLocaleString() || 'N/A'}\n   🛏️ ${
            p.bedrooms || '-'
          } beds, ${p.bathrooms || '-'} baths\n   📊 ${((p.score || 0) * 100).toFixed(0)}% match`
      )
      .join('\n\n');
  };

  const renderPropertyCard = (property: Property) => (
    <Card
      key={property.listing_id}
      hoverable
      className="property-card"
      style={{ marginBottom: 16 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
          <Title level={5} style={{ margin: 0, flex: 1 }}>
            {property.title}
          </Title>
          <Tag color="purple">
            {((property.score || 0) * 100).toFixed(0)}% Match
          </Tag>
        </div>

        <Row gutter={16}>
          <Col span={12}>
            <Statistic
              title="Price"
              value={property.price || 0}
              prefix="S$"
              formatter={(value) => `${Number(value).toLocaleString()}`}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="Per sqft"
              value={property.price_per_sqft || 0}
              prefix="S$"
              suffix="/sqft"
            />
          </Col>
        </Row>

        <Divider style={{ margin: '8px 0' }} />

        <Row gutter={[16, 8]}>
          <Col span={8}>
            <Text type="secondary">Beds</Text>
            <div>🛏️ {property.bedrooms || '-'}</div>
          </Col>
          <Col span={8}>
            <Text type="secondary">Baths</Text>
            <div>🚿 {property.bathrooms || '-'}</div>
          </Col>
          <Col span={8}>
            <Text type="secondary">Area</Text>
            <div>📐 {property.area_sqft?.toFixed(0) || '-'} sqft</div>
          </Col>
        </Row>

        <Space size="small" style={{ marginTop: 8 }}>
          <HomeOutlined />
          <Text>{property.unit_type || 'N/A'}</Text>
        </Space>

        <Space size="small">
          <EnvironmentOutlined />
          <Text>{property.location || 'N/A'}</Text>
        </Space>

        {property.mrt_station && (
          <Space size="small">
            <Text type="secondary">
              🚇 {property.mrt_station} ({property.mrt_distance_m}m)
            </Text>
          </Space>
        )}

        {property.matched_reasons && property.matched_reasons.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <Text type="success">✓ {property.matched_reasons.join(' · ')}</Text>
          </div>
        )}

        {property.listed_age && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            📅 {property.listed_age}
          </Text>
        )}

        <Button
          type="primary"
          block
          onClick={() =>
            window.open(`https://www.propertyguru.com.sg/listing/${property.listing_id}`, '_blank')
          }
        >
          View Details
        </Button>
      </Space>
    </Card>
  );

  const items = messages.map(({ message, id, role }) => {
    // In Ant Design X with useXAgent, we need to detect message source differently
    // User input messages vs AI response messages
    const isUserMessage = role === 'user';
    
    return {
      key: id,
      content: message,
      placement: isUserMessage ? ('end' as const) : ('start' as const), // User on right, AI on left (traditional)
      avatar: isUserMessage ? '👤' : '🤖',
      variant: isUserMessage ? ('filled' as const) : ('outlined' as const),
    };
  });

  return (
    <div className="property-search-container">
      <div className="header">
        <Title level={2} style={{ margin: 0, color: 'white' }}>
          🏠 AI Property Search Demo
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.9)' }}>
          Find your dream home using natural language
        </Text>
      </div>

      <div className="content-wrapper">
        <div className="chat-container">
          <Bubble.List
            items={items}
            style={{
              flex: 1,
              overflow: 'auto',
              padding: '20px',
              background: '#f5f5f5',
              fontSize: '16px',
            }}
            styles={{
              content: {
                fontSize: '16px',
                lineHeight: '1.6',
              },
            }}
          />
        </div>

        {searchStats && (
          <div style={{ padding: '16px', background: '#fff', borderTop: '1px solid #f0f0f0' }}>
            <Space>
              <Text strong style={{ fontSize: '16px' }}>Found {searchStats.total} properties</Text>
              <Text type="secondary" style={{ fontSize: '14px' }}>in {searchStats.took}ms</Text>
            </Space>
          </div>
        )}

        {properties.length > 0 && (
          <div className="properties-container">
            <Title level={4}>Search Results</Title>
            {properties.map(renderPropertyCard)}
          </div>
        )}
      </div>

      <div className="sender-container">
        <Sender
          ref={senderRef}
          value={inputValue}
          onChange={(value) => setInputValue(value)}
          onSubmit={(message) => {
            onRequest({ message }).then(() => {
              // Clear the input after successful submission
              setInputValue('');
            });
          }}
          loading={isSearching}
          placeholder="e.g., I want a 3-bedroom condo near MRT, budget under S$1.2M..."
          style={{ maxWidth: 1200, margin: '0 auto' }}
        />
      </div>
    </div>
  );
};

export default PropertySearch;

