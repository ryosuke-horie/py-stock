#!/usr/bin/env node

/**
 * MCP ニュース・センチメント分析サーバ
 * 銘柄関連ニュースの自動収集と感情分析を提供します
 */

import { Server } from '@anthropic-ai/mcp-server';
import { z } from 'zod';
import { NewsCollector, NewsItem, NewsCollectionOptions } from './services/news-collector.js';
import { SentimentAnalyzer, SentimentResult } from './services/sentiment-analyzer.js';
import { ImportanceScorer, ImportanceFactors } from './services/importance-scorer.js';

class NewsAnalysisServer {
  private server: Server;
  private newsCollector: NewsCollector;
  private sentimentAnalyzer: SentimentAnalyzer;
  private importanceScorer: ImportanceScorer;

  constructor() {
    this.server = new Server(
      {
        name: 'news-analysis',
        version: '1.0.0',
        description: 'ニュース収集と感情分析によるセンチメント分析サーバ'
      },
      {
        capabilities: {
          tools: true
        }
      }
    );

    this.newsCollector = new NewsCollector();
    this.sentimentAnalyzer = new SentimentAnalyzer();
    this.importanceScorer = new ImportanceScorer();

    this.setupTools();
  }

  private setupTools(): void {
    // ニュース収集ツール
    this.server.tool(
      'collect_stock_news',
      {
        description: '指定銘柄の関連ニュースを収集します',
        inputSchema: z.object({
          symbol: z.string().describe('銘柄コード（例: AAPL, 7203.T）'),
          language: z.enum(['ja', 'en', 'both']).optional().default('both').describe('ニュースの言語'),
          days: z.number().optional().default(7).describe('過去何日分のニュースを取得するか'),
          maxResults: z.number().optional().default(50).describe('最大取得件数')
        })
      },
      async (request) => {
        const { symbol, language, days, maxResults } = request.params;
        
        const options: NewsCollectionOptions = {
          language,
          fromDate: new Date(Date.now() - days * 24 * 60 * 60 * 1000),
          toDate: new Date(),
          maxResults
        };

        const news = await this.newsCollector.collectStockNews(symbol, options);
        
        return {
          symbol,
          newsCount: news.length,
          news: news.map(item => ({
            id: item.id,
            title: item.title,
            content: item.content.substring(0, 200) + '...',
            url: item.url,
            publishedAt: item.publishedAt.toISOString(),
            source: item.source,
            language: item.language,
            category: item.category,
            importance: item.importance
          }))
        };
      }
    );

    // 感情分析ツール
    this.server.tool(
      'analyze_sentiment',
      {
        description: 'テキストの感情分析を実行します',
        inputSchema: z.object({
          text: z.string().describe('分析対象のテキスト'),
          language: z.enum(['ja', 'en', 'auto']).optional().default('auto').describe('テキストの言語')
        })
      },
      async (request) => {
        const { text } = request.params;
        const result = await this.sentimentAnalyzer.analyzeSentiment(text);
        
        return {
          sentiment: {
            score: Math.round(result.score * 1000) / 1000,
            magnitude: Math.round(result.magnitude * 1000) / 1000,
            confidence: Math.round(result.confidence * 1000) / 1000,
            language: result.language
          },
          interpretation: this.interpretSentiment(result),
          details: result.details
        };
      }
    );

    // 包括的ニュース分析ツール
    this.server.tool(
      'comprehensive_news_analysis',
      {
        description: '銘柄のニュース収集・感情分析・重要度評価を包括的に実行します',
        inputSchema: z.object({
          symbol: z.string().describe('銘柄コード'),
          language: z.enum(['ja', 'en', 'both']).optional().default('both'),
          days: z.number().optional().default(7).describe('分析期間（日数）'),
          maxResults: z.number().optional().default(30)
        })
      },
      async (request) => {
        const { symbol, language, days, maxResults } = request.params;
        
        // ニュース収集
        const options: NewsCollectionOptions = {
          language,
          fromDate: new Date(Date.now() - days * 24 * 60 * 60 * 1000),
          toDate: new Date(),
          maxResults
        };

        const news = await this.newsCollector.collectStockNews(symbol, options);
        
        if (news.length === 0) {
          return {
            symbol,
            summary: '該当するニュースが見つかりませんでした',
            newsCount: 0,
            averageSentiment: 0,
            averageImportance: 0,
            topNews: []
          };
        }

        // 感情分析実行
        const sentimentResults: SentimentResult[] = [];
        for (const item of news) {
          const sentiment = await this.sentimentAnalyzer.analyzeSentiment(
            `${item.title} ${item.content}`
          );
          sentimentResults.push(sentiment);
        }

        // 重要度評価とランキング
        const rankedNews = this.importanceScorer.rankNewsByImportance(news, sentimentResults);
        
        // 統計情報計算
        const sentimentSummary = this.sentimentAnalyzer.calculateSentimentSummary(sentimentResults);
        const importanceStats = this.importanceScorer.calculateImportanceStatistics(
          rankedNews.map(r => r.importance)
        );

        return {
          symbol,
          analysisDate: new Date().toISOString(),
          newsCount: news.length,
          
          // センチメント統計
          sentimentSummary: {
            averageScore: Math.round(sentimentSummary.averageScore * 1000) / 1000,
            overallSentiment: sentimentSummary.overallSentiment,
            positiveCount: sentimentSummary.positiveCount,
            negativeCount: sentimentSummary.negativeCount,
            neutralCount: sentimentSummary.neutralCount
          },
          
          // 重要度統計
          importanceStatistics: {
            averageImportance: Math.round(importanceStats.averageScore * 10) / 10,
            highImportanceCount: importanceStats.highImportanceCount,
            criticalNewsCount: rankedNews.filter(r => r.importance.overallScore >= 90).length
          },
          
          // 上位ニュース（最大10件）
          topNews: rankedNews.slice(0, 10).map(r => ({
            id: r.newsItem.id,
            title: r.newsItem.title,
            content: r.newsItem.content.substring(0, 150) + '...',
            url: r.newsItem.url,
            publishedAt: r.newsItem.publishedAt.toISOString(),
            source: r.newsItem.source,
            language: r.newsItem.language,
            category: r.newsItem.category,
            sentiment: {
              score: Math.round(r.sentiment.score * 1000) / 1000,
              magnitude: Math.round(r.sentiment.magnitude * 1000) / 1000,
              interpretation: this.interpretSentiment(r.sentiment)
            },
            importance: {
              overallScore: Math.round(r.importance.overallScore * 10) / 10,
              level: this.getImportanceLevel(r.importance.overallScore)
            }
          })),
          
          // 投資判断への示唆
          investmentInsights: this.generateInvestmentInsights(
            sentimentSummary,
            importanceStats,
            rankedNews.slice(0, 5)
          )
        };
      }
    );

    // 市場センチメント要約ツール
    this.server.tool(
      'market_sentiment_summary',
      {
        description: '複数銘柄の市場センチメントを要約します',
        inputSchema: z.object({
          symbols: z.array(z.string()).describe('銘柄コードの配列'),
          days: z.number().optional().default(3).describe('分析期間')
        })
      },
      async (request) => {
        const { symbols, days } = request.params;
        const results: any[] = [];

        for (const symbol of symbols) {
          try {
            const options: NewsCollectionOptions = {
              language: 'both',
              fromDate: new Date(Date.now() - days * 24 * 60 * 60 * 1000),
              toDate: new Date(),
              maxResults: 20
            };

            const news = await this.newsCollector.collectStockNews(symbol, options);
            
            if (news.length > 0) {
              const sentiments = await this.sentimentAnalyzer.analyzeMultipleTexts(
                news.map(n => `${n.title} ${n.content}`)
              );
              
              const summary = this.sentimentAnalyzer.calculateSentimentSummary(sentiments);
              
              results.push({
                symbol,
                newsCount: news.length,
                overallSentiment: summary.overallSentiment,
                averageScore: Math.round(summary.averageScore * 1000) / 1000,
                confidence: Math.round(summary.averageConfidence * 1000) / 1000
              });
            } else {
              results.push({
                symbol,
                newsCount: 0,
                overallSentiment: 'neutral',
                averageScore: 0,
                confidence: 0
              });
            }
          } catch (error) {
            console.error(`Error analyzing ${symbol}:`, error);
            results.push({
              symbol,
              error: 'Analysis failed',
              newsCount: 0,
              overallSentiment: 'neutral',
              averageScore: 0,
              confidence: 0
            });
          }
        }

        return {
          analysisDate: new Date().toISOString(),
          symbolCount: symbols.length,
          results
        };
      }
    );
  }

  /**
   * 感情分析結果の解釈
   */
  private interpretSentiment(sentiment: SentimentResult): string {
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

  /**
   * 重要度レベルの判定
   */
  private getImportanceLevel(score: number): string {
    if (score >= 90) return '緊急';
    if (score >= 80) return '高';
    if (score >= 60) return '中';
    if (score >= 40) return '低';
    return '軽微';
  }

  /**
   * 投資判断への示唆を生成
   */
  private generateInvestmentInsights(
    sentimentSummary: any,
    importanceStats: any,
    topNews: any[]
  ): string[] {
    const insights: string[] = [];
    
    // センチメント関連の示唆
    if (sentimentSummary.overallSentiment === 'positive' && sentimentSummary.averageScore > 0.5) {
      insights.push('市場センチメントは強いポジティブを示しており、買い要因が多い');
    } else if (sentimentSummary.overallSentiment === 'negative' && sentimentSummary.averageScore < -0.5) {
      insights.push('市場センチメントは強いネガティブを示しており、売り要因が多い');
    }
    
    // 重要度関連の示唆
    if (importanceStats.criticalNewsCount > 0) {
      insights.push(`緊急度の高いニュースが${importanceStats.criticalNewsCount}件あり、注意が必要`);
    }
    
    if (importanceStats.highImportanceCount > 3) {
      insights.push('重要なニュースが多数あり、ボラティリティの増加が予想される');
    }
    
    // カテゴリ別分析
    const categories = topNews.map(n => n.category);
    if (categories.filter(c => c === 'earnings').length >= 2) {
      insights.push('決算関連のニュースが多く、業績動向に注目');
    }
    
    if (categories.filter(c => c === 'ma').length >= 1) {
      insights.push('M&A関連のニュースあり、株価への大きな影響が予想される');
    }
    
    if (insights.length === 0) {
      insights.push('特に大きな材料は見当たらず、テクニカル分析重視の局面');
    }
    
    return insights;
  }

  async start(): Promise<void> {
    await this.server.connect();
    console.log('News Analysis MCP Server started');
  }
}

// サーバー起動
const server = new NewsAnalysisServer();
server.start().catch(console.error);