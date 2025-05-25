/**
 * ニュース収集サービス
 * 指定された銘柄に関連するニュースを自動収集します
 */

import fetch from 'node-fetch';
import { format, subDays } from 'date-fns';

export interface NewsItem {
  id: string;
  title: string;
  content: string;
  url: string;
  publishedAt: Date;
  source: string;
  symbol?: string;
  language: 'ja' | 'en';
  category: string;
  importance: number; // 0-100
}

export interface NewsCollectionOptions {
  symbols?: string[];
  language?: 'ja' | 'en' | 'both';
  category?: string[];
  fromDate?: Date;
  toDate?: Date;
  maxResults?: number;
}

export class NewsCollector {
  private apiKey: string;
  private baseUrl: string = 'https://newsapi.org/v2';
  
  constructor(apiKey?: string) {
    this.apiKey = apiKey || process.env.NEWS_API_KEY || '';
  }

  /**
   * 銘柄関連ニュースを収集
   */
  async collectStockNews(symbol: string, options: NewsCollectionOptions = {}): Promise<NewsItem[]> {
    const {
      language = 'both',
      fromDate = subDays(new Date(), 7),
      toDate = new Date(),
      maxResults = 50
    } = options;

    const news: NewsItem[] = [];

    // 日本語ニュース収集
    if (language === 'ja' || language === 'both') {
      const jaNews = await this.collectJapaneseNews(symbol, fromDate, toDate, maxResults);
      news.push(...jaNews);
    }

    // 英語ニュース収集
    if (language === 'en' || language === 'both') {
      const enNews = await this.collectEnglishNews(symbol, fromDate, toDate, maxResults);
      news.push(...enNews);
    }

    // 重複除去と重要度順ソート
    const uniqueNews = this.removeDuplicates(news);
    return uniqueNews.sort((a, b) => b.importance - a.importance);
  }

  /**
   * 日本語ニュース収集
   */
  private async collectJapaneseNews(symbol: string, fromDate: Date, toDate: Date, maxResults: number): Promise<NewsItem[]> {
    if (!this.apiKey) {
      console.warn('News API key not configured. Using mock data.');
      return this.getMockJapaneseNews(symbol);
    }

    try {
      // 日本の主要経済メディアから検索
      const sources = 'nikkei.com,bloomberg.co.jp,reuters.com,sankei.com';
      const query = this.buildJapaneseQuery(symbol);
      
      const url = `${this.baseUrl}/everything?` +
        `q=${encodeURIComponent(query)}&` +
        `sources=${sources}&` +
        `language=ja&` +
        `from=${format(fromDate, 'yyyy-MM-dd')}&` +
        `to=${format(toDate, 'yyyy-MM-dd')}&` +
        `pageSize=${Math.min(maxResults, 100)}&` +
        `sortBy=relevancy&` +
        `apiKey=${this.apiKey}`;

      const response = await fetch(url);
      const data = await response.json() as any;

      if (data.status !== 'ok') {
        throw new Error(`News API error: ${data.message}`);
      }

      return data.articles.map((article: any) => this.convertToNewsItem(article, symbol, 'ja'));
    } catch (error) {
      console.error('Error collecting Japanese news:', error);
      return this.getMockJapaneseNews(symbol);
    }
  }

  /**
   * 英語ニュース収集
   */
  private async collectEnglishNews(symbol: string, fromDate: Date, toDate: Date, maxResults: number): Promise<NewsItem[]> {
    if (!this.apiKey) {
      console.warn('News API key not configured. Using mock data.');
      return this.getMockEnglishNews(symbol);
    }

    try {
      // 主要な経済メディアから検索
      const sources = 'bloomberg.com,reuters.com,cnbc.com,marketwatch.com,yahoo.com';
      const query = this.buildEnglishQuery(symbol);
      
      const url = `${this.baseUrl}/everything?` +
        `q=${encodeURIComponent(query)}&` +
        `sources=${sources}&` +
        `language=en&` +
        `from=${format(fromDate, 'yyyy-MM-dd')}&` +
        `to=${format(toDate, 'yyyy-MM-dd')}&` +
        `pageSize=${Math.min(maxResults, 100)}&` +
        `sortBy=relevancy&` +
        `apiKey=${this.apiKey}`;

      const response = await fetch(url);
      const data = await response.json() as any;

      if (data.status !== 'ok') {
        throw new Error(`News API error: ${data.message}`);
      }

      return data.articles.map((article: any) => this.convertToNewsItem(article, symbol, 'en'));
    } catch (error) {
      console.error('Error collecting English news:', error);
      return this.getMockEnglishNews(symbol);
    }
  }

  /**
   * 日本語検索クエリを構築
   */
  private buildJapaneseQuery(symbol: string): string {
    const cleanSymbol = symbol.replace(/\.[A-Z]+$/, ''); // .T, .TO等を除去
    
    if (this.isJapaneseStock(symbol)) {
      // 日本株の場合、銘柄コードと企業名で検索
      const queries = [
        cleanSymbol,
        `銘柄コード${cleanSymbol}`,
        `証券コード${cleanSymbol}`
      ];
      
      // 主要企業の場合、社名も追加
      const companyName = this.getJapaneseCompanyName(cleanSymbol);
      if (companyName) {
        queries.push(companyName);
      }
      
      return queries.join(' OR ');
    } else {
      // 米国株の場合
      return `${symbol} 株価 OR ${symbol} 決算`;
    }
  }

  /**
   * 英語検索クエリを構築
   */
  private buildEnglishQuery(symbol: string): string {
    const cleanSymbol = symbol.replace(/\.[A-Z]+$/, '');
    return `${cleanSymbol} stock OR ${cleanSymbol} earnings OR ${cleanSymbol} financial`;
  }

  /**
   * 記事をNewsItemに変換
   */
  private convertToNewsItem(article: any, symbol: string, language: 'ja' | 'en'): NewsItem {
    const id = Buffer.from(`${article.url}_${symbol}`).toString('base64');
    
    return {
      id,
      title: article.title || '',
      content: article.description || article.content || '',
      url: article.url || '',
      publishedAt: new Date(article.publishedAt),
      source: article.source?.name || 'Unknown',
      symbol,
      language,
      category: this.categorizeNews(article.title || '', article.description || ''),
      importance: this.calculateImportance(article.title || '', article.description || '')
    };
  }

  /**
   * ニュースのカテゴリ分類
   */
  private categorizeNews(title: string, content: string): string {
    const text = (title + ' ' + content).toLowerCase();
    
    if (text.includes('earnings') || text.includes('決算') || text.includes('業績')) {
      return 'earnings';
    } else if (text.includes('merger') || text.includes('acquisition') || text.includes('M&A') || text.includes('買収')) {
      return 'ma';
    } else if (text.includes('dividend') || text.includes('配当')) {
      return 'dividend';
    } else if (text.includes('forecast') || text.includes('guidance') || text.includes('見通し') || text.includes('予想')) {
      return 'forecast';
    } else if (text.includes('partnership') || text.includes('collaboration') || text.includes('提携')) {
      return 'partnership';
    } else {
      return 'general';
    }
  }

  /**
   * ニュースの重要度を計算（0-100）
   */
  private calculateImportance(title: string, content: string): number {
    const text = (title + ' ' + content).toLowerCase();
    let score = 50; // ベーススコア

    // 重要キーワードによる加点
    const importantKeywords = {
      'earnings': 20,
      '決算': 20,
      'merger': 25,
      'acquisition': 25,
      'M&A': 25,
      '買収': 25,
      'bankruptcy': 30,
      '破綻': 30,
      'dividend': 15,
      '配当': 15,
      'forecast': 10,
      '見通し': 10,
      'guidance': 15,
      'beat': 15,
      'miss': 15,
      '上方修正': 20,
      '下方修正': 20
    };

    for (const [keyword, points] of Object.entries(importantKeywords)) {
      if (text.includes(keyword)) {
        score += points;
      }
    }

    return Math.min(100, Math.max(0, score));
  }

  /**
   * 重複記事を除去
   */
  private removeDuplicates(news: NewsItem[]): NewsItem[] {
    const seen = new Set<string>();
    return news.filter(item => {
      const key = `${item.title}_${item.source}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  /**
   * 日本株かどうかを判定
   */
  private isJapaneseStock(symbol: string): boolean {
    return /^\d{4}(\.T|\.TO)?$/.test(symbol);
  }

  /**
   * 日本企業名を取得（主要企業のみ）
   */
  private getJapaneseCompanyName(symbol: string): string | null {
    const companyMap: Record<string, string> = {
      '7203': 'トヨタ自動車',
      '6758': 'ソニー',
      '9984': 'ソフトバンク',
      '6861': 'キーエンス',
      '7974': '任天堂',
      '4519': '中外製薬',
      '8411': 'みずほフィナンシャル',
      '6954': 'ファナック',
      '7751': 'キヤノン',
      '4689': 'ヤフー'
    };
    
    return companyMap[symbol] || null;
  }

  /**
   * モック日本語ニュース（API未設定時用）
   */
  private getMockJapaneseNews(symbol: string): NewsItem[] {
    return [
      {
        id: `mock_ja_1_${symbol}`,
        title: `${symbol}：四半期決算が市場予想を上回る`,
        content: `${symbol}の第3四半期決算が発表され、売上高・利益ともに市場予想を上回る好結果となりました。`,
        url: 'https://example.com/mock-news-1',
        publishedAt: new Date(),
        source: 'Mock経済新聞',
        symbol,
        language: 'ja',
        category: 'earnings',
        importance: 85
      },
      {
        id: `mock_ja_2_${symbol}`,
        title: `${symbol}：新製品発表で株価上昇`,
        content: `${symbol}が新製品を発表し、投資家の注目を集めています。`,
        url: 'https://example.com/mock-news-2',
        publishedAt: subDays(new Date(), 1),
        source: 'Mock投資ニュース',
        symbol,
        language: 'ja',
        category: 'general',
        importance: 65
      }
    ];
  }

  /**
   * モック英語ニュース（API未設定時用）
   */
  private getMockEnglishNews(symbol: string): NewsItem[] {
    return [
      {
        id: `mock_en_1_${symbol}`,
        title: `${symbol} Reports Strong Q3 Earnings Beat`,
        content: `${symbol} has reported quarterly earnings that exceeded analyst expectations.`,
        url: 'https://example.com/mock-news-en-1',
        publishedAt: new Date(),
        source: 'Mock Financial Times',
        symbol,
        language: 'en',
        category: 'earnings',
        importance: 90
      },
      {
        id: `mock_en_2_${symbol}`,
        title: `${symbol} Announces Strategic Partnership`,
        content: `${symbol} has announced a new strategic partnership that could boost future growth.`,
        url: 'https://example.com/mock-news-en-2',
        publishedAt: subDays(new Date(), 2),
        source: 'Mock Bloomberg',
        symbol,
        language: 'en',
        category: 'partnership',
        importance: 70
      }
    ];
  }
}