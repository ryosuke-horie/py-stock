/**
 * 重要度スコアリングサービス
 * ニュースの投資判断への影響度を算出します
 */

import { NewsItem } from './news-collector.js';
import { SentimentResult } from './sentiment-analyzer.js';

export interface ImportanceFactors {
  sentimentImpact: number; // 感情分析による影響度
  keywordRelevance: number; // キーワード関連度
  sourceCredibility: number; // 情報源の信頼性
  recency: number; // 時間的新しさ
  marketImpact: number; // 市場影響度
  overallScore: number; // 総合スコア (0-100)
}

export class ImportanceScorer {
  private credibleSources: Map<string, number>;
  private criticalKeywords: Map<string, number>;
  private marketImpactKeywords: Map<string, number>;

  constructor() {
    this.initializeSourceCredibility();
    this.initializeCriticalKeywords();
    this.initializeMarketImpactKeywords();
  }

  /**
   * ニュースの重要度を総合的に評価
   */
  calculateImportance(
    newsItem: NewsItem,
    sentimentResult: SentimentResult
  ): ImportanceFactors {
    const sentimentImpact = this.calculateSentimentImpact(sentimentResult);
    const keywordRelevance = this.calculateKeywordRelevance(newsItem);
    const sourceCredibility = this.calculateSourceCredibility(newsItem.source);
    const recency = this.calculateRecency(newsItem.publishedAt);
    const marketImpact = this.calculateMarketImpact(newsItem);

    // 重み付き総合スコア計算
    const weights = {
      sentiment: 0.25,
      keyword: 0.30,
      source: 0.20,
      recency: 0.10,
      market: 0.15
    };

    const overallScore = Math.min(100, Math.max(0,
      sentimentImpact * weights.sentiment +
      keywordRelevance * weights.keyword +
      sourceCredibility * weights.source +
      recency * weights.recency +
      marketImpact * weights.market
    ));

    return {
      sentimentImpact,
      keywordRelevance,
      sourceCredibility,
      recency,
      marketImpact,
      overallScore
    };
  }

  /**
   * 感情分析による影響度計算
   */
  private calculateSentimentImpact(sentimentResult: SentimentResult): number {
    const { score, magnitude, confidence } = sentimentResult;
    
    // 感情の強さと信頼度を考慮
    const emotionStrength = Math.abs(score) * magnitude;
    const weightedImpact = emotionStrength * confidence;
    
    // 極端な感情ほど高スコア（投資判断により大きく影響）
    let impactScore = weightedImpact * 100;
    
    // 非常に強いネガティブ感情は特に高くスコア
    if (score < -0.7 && magnitude > 0.8) {
      impactScore *= 1.5;
    }
    
    return Math.min(100, impactScore);
  }

  /**
   * キーワード関連度計算
   */
  private calculateKeywordRelevance(newsItem: NewsItem): number {
    const text = `${newsItem.title} ${newsItem.content}`.toLowerCase();
    let score = 0;
    let matchCount = 0;

    // 重要キーワードの出現をチェック
    for (const [keyword, weight] of this.criticalKeywords) {
      if (text.includes(keyword)) {
        score += weight;
        matchCount++;
      }
    }

    // キーワード密度も考慮
    const density = matchCount / Math.max(text.split(' ').length, 1);
    score += density * 50;

    return Math.min(100, score);
  }

  /**
   * 情報源の信頼性計算
   */
  private calculateSourceCredibility(source: string): number {
    const normalizedSource = source.toLowerCase();
    
    for (const [credibleSource, score] of this.credibleSources) {
      if (normalizedSource.includes(credibleSource)) {
        return score;
      }
    }
    
    return 50; // デフォルトスコア
  }

  /**
   * 時間的新しさ計算
   */
  private calculateRecency(publishedAt: Date): number {
    const now = new Date();
    const hoursDiff = (now.getTime() - publishedAt.getTime()) / (1000 * 60 * 60);
    
    if (hoursDiff <= 1) return 100;
    if (hoursDiff <= 6) return 90;
    if (hoursDiff <= 24) return 80;
    if (hoursDiff <= 72) return 60;
    if (hoursDiff <= 168) return 40; // 1週間
    
    return 20; // 1週間以上古い
  }

  /**
   * 市場影響度計算
   */
  private calculateMarketImpact(newsItem: NewsItem): number {
    const text = `${newsItem.title} ${newsItem.content}`.toLowerCase();
    let score = 0;

    // 市場影響キーワードをチェック
    for (const [keyword, impact] of this.marketImpactKeywords) {
      if (text.includes(keyword)) {
        score += impact;
      }
    }

    // カテゴリ別基本スコア
    const categoryScores: Record<string, number> = {
      'earnings': 30,
      'ma': 40,
      'dividend': 20,
      'forecast': 25,
      'partnership': 15,
      'general': 10
    };

    score += categoryScores[newsItem.category] || 10;

    return Math.min(100, score);
  }

  /**
   * 情報源の信頼性マップを初期化
   */
  private initializeSourceCredibility(): void {
    this.credibleSources = new Map([
      // 日本の主要メディア
      ['日本経済新聞', 95],
      ['nikkei', 95],
      ['日経', 95],
      ['朝日新聞', 90],
      ['読売新聞', 90],
      ['毎日新聞', 90],
      ['reuters', 95],
      ['ロイター', 95],
      ['bloomberg', 95],
      ['ブルームバーグ', 95],
      
      // 海外主要メディア
      ['wall street journal', 95],
      ['financial times', 95],
      ['cnbc', 85],
      ['marketwatch', 80],
      ['yahoo finance', 75],
      
      // 証券会社・金融機関
      ['野村證券', 85],
      ['大和証券', 85],
      ['みずほ証券', 85],
      ['三菱ufj', 85],
      
      // 一般メディア
      ['nhk', 80],
      ['tbs', 70],
      ['フジテレビ', 70],
      ['テレビ朝日', 70],
      
      // 不明・その他
      ['unknown', 50],
      ['mock', 30] // テスト用
    ]);
  }

  /**
   * 重要キーワードマップを初期化
   */
  private initializeCriticalKeywords(): void {
    this.criticalKeywords = new Map([
      // 決算関連
      ['earnings', 30],
      ['決算', 30],
      ['業績', 25],
      ['売上', 20],
      ['利益', 25],
      ['revenue', 20],
      ['profit', 25],
      
      // 予想・見通し
      ['forecast', 20],
      ['guidance', 25],
      ['見通し', 20],
      ['予想', 20],
      ['上方修正', 35],
      ['下方修正', 35],
      ['beat', 30],
      ['miss', 30],
      
      // M&A・提携
      ['merger', 40],
      ['acquisition', 40],
      ['買収', 40],
      ['合併', 35],
      ['提携', 25],
      ['partnership', 25],
      
      // 重大ニュース
      ['bankruptcy', 50],
      ['破綻', 50],
      ['倒産', 50],
      ['不正', 45],
      ['scandal', 45],
      ['リコール', 40],
      ['recall', 40],
      
      // 配当・株主還元
      ['dividend', 20],
      ['配当', 20],
      ['株主還元', 25],
      ['自社株買い', 25],
      ['buyback', 25]
    ]);
  }

  /**
   * 市場影響キーワードマップを初期化
   */
  private initializeMarketImpactKeywords(): void {
    this.marketImpactKeywords = new Map([
      // 高影響度
      ['ceo', 25],
      ['社長', 25],
      ['役員', 20],
      ['executive', 20],
      ['leadership', 20],
      
      // 製品・サービス
      ['新製品', 15],
      ['new product', 15],
      ['innovation', 20],
      ['革新', 20],
      ['breakthrough', 25],
      
      // 規制・法的
      ['regulation', 30],
      ['規制', 30],
      ['lawsuit', 35],
      ['訴訟', 35],
      ['fine', 30],
      ['罰金', 30],
      
      // 市場環境
      ['market', 15],
      ['競合', 20],
      ['competitor', 20],
      ['industry', 15],
      ['業界', 15],
      
      // 財務指標
      ['debt', 25],
      ['負債', 25],
      ['cash', 20],
      ['現金', 20],
      ['credit', 25],
      ['信用', 25]
    ]);
  }

  /**
   * 複数ニュースの重要度ランキング
   */
  rankNewsByImportance(
    newsItems: NewsItem[],
    sentimentResults: SentimentResult[]
  ): Array<{
    newsItem: NewsItem;
    importance: ImportanceFactors;
    sentiment: SentimentResult;
  }> {
    if (newsItems.length !== sentimentResults.length) {
      throw new Error('News items and sentiment results must have the same length');
    }

    const rankedNews = newsItems.map((news, index) => ({
      newsItem: news,
      importance: this.calculateImportance(news, sentimentResults[index]),
      sentiment: sentimentResults[index]
    }));

    return rankedNews.sort((a, b) => b.importance.overallScore - a.importance.overallScore);
  }

  /**
   * 重要度分布の統計情報
   */
  calculateImportanceStatistics(importanceScores: ImportanceFactors[]): {
    averageScore: number;
    maxScore: number;
    minScore: number;
    highImportanceCount: number; // 80点以上
    mediumImportanceCount: number; // 50-79点
    lowImportanceCount: number; // 50点未満
  } {
    if (importanceScores.length === 0) {
      return {
        averageScore: 0,
        maxScore: 0,
        minScore: 0,
        highImportanceCount: 0,
        mediumImportanceCount: 0,
        lowImportanceCount: 0
      };
    }

    const scores = importanceScores.map(i => i.overallScore);
    const averageScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    const maxScore = Math.max(...scores);
    const minScore = Math.min(...scores);

    const highImportanceCount = scores.filter(score => score >= 80).length;
    const mediumImportanceCount = scores.filter(score => score >= 50 && score < 80).length;
    const lowImportanceCount = scores.filter(score => score < 50).length;

    return {
      averageScore,
      maxScore,
      minScore,
      highImportanceCount,
      mediumImportanceCount,
      lowImportanceCount
    };
  }
}