#!/usr/bin/env node

/**
 * MCP ニュース・センチメント分析サーバ
 * 銘柄関連ニュースの自動収集と感情分析を提供します
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const server = new Server({
  name: 'news-analysis',
  version: '1.0.0'
}, {
  capabilities: {
    tools: {}
  }
});

// モックデータ生成関数
function generateMockNewsData(symbol: string, language: string = 'both') {
  const mockNews = [
    {
      id: 'news1',
      title: `${symbol}：第3四半期決算が市場予想を上回る好結果`,
      content: `${symbol}の最新四半期決算が発表され、売上・利益ともに市場予想を大幅に上回る結果となりました。`,
      url: 'https://example.com/news1',
      publishedAt: new Date().toISOString(),
      source: '経済新聞',
      language: 'ja',
      category: 'earnings',
      importance: 92
    },
    {
      id: 'news2',
      title: `${symbol} announces strategic partnership`,
      content: `${symbol} has announced a new strategic partnership that is expected to drive growth.`,
      url: 'https://example.com/news2',
      publishedAt: new Date().toISOString(),
      source: 'Bloomberg',
      language: 'en',
      category: 'partnership',
      importance: 78
    }
  ];

  return language === 'ja' ? mockNews.filter(n => n.language === 'ja') :
         language === 'en' ? mockNews.filter(n => n.language === 'en') :
         mockNews;
}

function generateMockSentiment(text: string) {
  return {
    score: Math.random() * 0.8 - 0.4, // -0.4 to 0.4
    magnitude: Math.random() * 0.8 + 0.2,
    confidence: Math.random() * 0.3 + 0.7,
    language: text.match(/[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]/) ? 'ja' : 'en',
    details: {}
  };
}

// ニュース収集ツール
server.tool(
  'collect_stock_news',
  z.object({
    symbol: z.string().describe('銘柄コード（例: AAPL, 7203.T）'),
    language: z.enum(['ja', 'en', 'both']).default('both').describe('ニュースの言語'),
    days: z.number().default(7).describe('過去何日分のニュースを取得するか'),
    maxResults: z.number().default(50).describe('最大取得件数')
  }),
  async ({ symbol, language = 'both', days = 7, maxResults = 50 }) => {
    const news = generateMockNewsData(symbol, language);
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          symbol,
          newsCount: news.length,
          news: news.map(item => ({
            id: item.id,
            title: item.title,
            content: item.content.substring(0, 200) + '...',
            url: item.url,
            publishedAt: item.publishedAt,
            source: item.source,
            language: item.language,
            category: item.category,
            importance: item.importance
          }))
        }, null, 2)
      }]
    };
  }
);

// 感情分析ツール
server.tool(
  'analyze_sentiment',
  z.object({
    text: z.string().describe('分析対象のテキスト'),
    language: z.enum(['ja', 'en', 'auto']).default('auto').describe('テキストの言語')
  }),
  async ({ text, language = 'auto' }) => {
    const result = generateMockSentiment(text);
    
    function interpretSentiment(sentiment: any): string {
      const { score, magnitude } = sentiment;
      
      if (Math.abs(score) < 0.1) {
        return 'ニュートラル';
      } else if (score > 0) {
        if (score > 0.7 && magnitude > 0.8) return '非常にポジティブ';
        if (score > 0.4) return 'ポジティブ';
        return '軽くポジティブ';
      } else {
        if (score < -0.7 && magnitude > 0.8) return '非常にネガティブ';
        if (score < -0.4) return 'ネガティブ';
        return '軽くネガティブ';
      }
    }
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          sentiment: {
            score: Math.round(result.score * 1000) / 1000,
            magnitude: Math.round(result.magnitude * 1000) / 1000,
            confidence: Math.round(result.confidence * 1000) / 1000,
            language: result.language
          },
          interpretation: interpretSentiment(result),
          details: result.details
        }, null, 2)
      }]
    };
  }
);

// 包括的ニュース分析ツール
server.tool(
  'comprehensive_news_analysis',
  z.object({
    symbol: z.string().describe('銘柄コード'),
    language: z.enum(['ja', 'en', 'both']).default('both').describe('ニュースの言語'),
    days: z.number().default(7).describe('分析期間（日数）'),
    maxResults: z.number().default(30).describe('最大取得件数')
  }),
  async ({ symbol, language = 'both', days = 7, maxResults = 30 }) => {
    const news = generateMockNewsData(symbol, language);
    
    if (news.length === 0) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            symbol,
            summary: '該当するニュースが見つかりませんでした',
            newsCount: 0,
            averageSentiment: 0,
            averageImportance: 0,
            topNews: []
          }, null, 2)
        }]
      };
    }

    // モック感情分析
    const sentimentResults = news.map(item => 
      generateMockSentiment(`${item.title} ${item.content}`)
    );

    const avgSentiment = sentimentResults.reduce((sum, s) => sum + s.score, 0) / sentimentResults.length;
    const avgImportance = news.reduce((sum, n) => sum + n.importance, 0) / news.length;
    
    const positiveCount = sentimentResults.filter(s => s.score > 0.1).length;
    const negativeCount = sentimentResults.filter(s => s.score < -0.1).length;
    const neutralCount = sentimentResults.length - positiveCount - negativeCount;

    const topNews = news.slice(0, 10).map((item, i) => ({
      id: item.id,
      title: item.title,
      content: item.content.substring(0, 150) + '...',
      url: item.url,
      publishedAt: item.publishedAt,
      source: item.source,
      language: item.language,
      category: item.category,
      sentiment: {
        score: Math.round(sentimentResults[i].score * 1000) / 1000,
        magnitude: Math.round(sentimentResults[i].magnitude * 1000) / 1000,
        interpretation: sentimentResults[i].score > 0.1 ? 'ポジティブ' : 
                       sentimentResults[i].score < -0.1 ? 'ネガティブ' : 'ニュートラル'
      },
      importance: {
        overallScore: Math.round(item.importance * 10) / 10,
        level: item.importance >= 90 ? '緊急' : 
               item.importance >= 80 ? '高' : 
               item.importance >= 60 ? '中' : '低'
      }
    }));

    // 投資判断への示唆
    const insights = [];
    const overallSentiment = avgSentiment > 0.1 ? 'positive' : avgSentiment < -0.1 ? 'negative' : 'neutral';
    
    if (overallSentiment === 'positive' && avgSentiment > 0.3) {
      insights.push('市場センチメントは強いポジティブを示しており、買い要因が多い');
    } else if (overallSentiment === 'negative' && avgSentiment < -0.3) {
      insights.push('市場センチメントは強いネガティブを示しており、売り要因が多い');
    }
    
    const criticalNewsCount = news.filter(n => n.importance >= 90).length;
    if (criticalNewsCount > 0) {
      insights.push(`緊急度の高いニュースが${criticalNewsCount}件あり、注意が必要`);
    }
    
    const highImportanceCount = news.filter(n => n.importance >= 80).length;
    if (highImportanceCount > 3) {
      insights.push('重要なニュースが多数あり、ボラティリティの増加が予想される');
    }

    if (insights.length === 0) {
      insights.push('特に大きな材料は見当たらず、テクニカル分析重視の局面');
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          symbol,
          analysisDate: new Date().toISOString(),
          newsCount: news.length,
          sentimentSummary: {
            averageScore: Math.round(avgSentiment * 1000) / 1000,
            overallSentiment,
            positiveCount,
            negativeCount,
            neutralCount
          },
          importanceStatistics: {
            averageImportance: Math.round(avgImportance * 10) / 10,
            highImportanceCount,
            criticalNewsCount
          },
          topNews,
          investmentInsights: insights
        }, null, 2)
      }]
    };
  }
);

// 市場センチメント要約ツール
server.tool(
  'market_sentiment_summary',
  z.object({
    symbols: z.array(z.string()).describe('銘柄コードの配列'),
    days: z.number().default(3).describe('分析期間')
  }),
  async ({ symbols, days = 3 }) => {
    const results = symbols.map((symbol: string) => {
      const news = generateMockNewsData(symbol, 'both');
      
      if (news.length > 0) {
        const sentiments = news.map(n => generateMockSentiment(`${n.title} ${n.content}`));
        const avgScore = sentiments.reduce((sum, s) => sum + s.score, 0) / sentiments.length;
        const avgConfidence = sentiments.reduce((sum, s) => sum + s.confidence, 0) / sentiments.length;
        const overallSentiment = avgScore > 0.1 ? 'positive' : avgScore < -0.1 ? 'negative' : 'neutral';
        
        return {
          symbol,
          newsCount: news.length,
          overallSentiment,
          averageScore: Math.round(avgScore * 1000) / 1000,
          confidence: Math.round(avgConfidence * 1000) / 1000
        };
      } else {
        return {
          symbol,
          newsCount: 0,
          overallSentiment: 'neutral',
          averageScore: 0,
          confidence: 0
        };
      }
    });

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          analysisDate: new Date().toISOString(),
          symbolCount: symbols.length,
          results
        }, null, 2)
      }]
    };
  }
);

// サーバー起動
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log('News Analysis MCP Server started');
}

main().catch(console.error);