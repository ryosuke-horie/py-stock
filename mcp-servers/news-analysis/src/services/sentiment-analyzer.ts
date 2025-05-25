/**
 * 感情分析サービス
 * 日本語・英語のニュースに対してポジティブ/ネガティブ判定を行います
 */

import Sentiment from 'sentiment';
import franc from 'franc';

export interface SentimentResult {
  score: number; // -1.0 (very negative) to 1.0 (very positive)
  magnitude: number; // 0.0 (neutral) to 1.0 (strong emotion)
  confidence: number; // 0.0 to 1.0
  language: 'ja' | 'en' | 'unknown';
  details: {
    positive: string[];
    negative: string[];
    neutral: string[];
  };
}

export class SentimentAnalyzer {
  private englishSentiment: Sentiment;
  private japanesePositiveWords: Set<string>;
  private japaneseNegativeWords: Set<string>;

  constructor() {
    this.englishSentiment = new Sentiment();
    this.initializeJapaneseDictionary();
  }

  /**
   * テキストの感情分析を実行
   */
  async analyzeSentiment(text: string): Promise<SentimentResult> {
    const language = this.detectLanguage(text);
    
    if (language === 'ja') {
      return this.analyzeJapaneseSentiment(text);
    } else if (language === 'en') {
      return this.analyzeEnglishSentiment(text);
    } else {
      // 不明な言語の場合は英語として処理
      return this.analyzeEnglishSentiment(text);
    }
  }

  /**
   * 日本語感情分析
   */
  private analyzeJapaneseSentiment(text: string): SentimentResult {
    const words = this.segmentJapaneseText(text);
    let positiveScore = 0;
    let negativeScore = 0;
    let totalWords = 0;

    const positive: string[] = [];
    const negative: string[] = [];
    const neutral: string[] = [];

    for (const word of words) {
      totalWords++;
      
      if (this.japanesePositiveWords.has(word)) {
        positiveScore += this.getJapaneseWordWeight(word, 'positive');
        positive.push(word);
      } else if (this.japaneseNegativeWords.has(word)) {
        negativeScore += this.getJapaneseWordWeight(word, 'negative');
        negative.push(word);
      } else {
        neutral.push(word);
      }
    }

    // スコア正規化
    const rawScore = positiveScore - negativeScore;
    const normalizedScore = Math.tanh(rawScore / Math.max(totalWords, 1));
    const magnitude = Math.min(1.0, (Math.abs(rawScore) / Math.max(totalWords, 1)) * 2);
    
    // 信頼度計算（感情語の割合に基づく）
    const emotionWords = positive.length + negative.length;
    const confidence = Math.min(1.0, emotionWords / Math.max(totalWords * 0.1, 1));

    return {
      score: normalizedScore,
      magnitude,
      confidence,
      language: 'ja',
      details: { positive, negative, neutral }
    };
  }

  /**
   * 英語感情分析
   */
  private analyzeEnglishSentiment(text: string): SentimentResult {
    const result = this.englishSentiment.analyze(text);
    
    // Sentimentライブラリの結果を正規化
    const normalizedScore = Math.tanh(result.score / Math.max(result.tokens.length, 1));
    const magnitude = Math.min(1.0, Math.abs(result.score) / Math.max(result.tokens.length, 1));
    const confidence = Math.min(1.0, result.calculation.length / Math.max(result.tokens.length * 0.1, 1));

    return {
      score: normalizedScore,
      magnitude,
      confidence,
      language: 'en',
      details: {
        positive: result.positive,
        negative: result.negative,
        neutral: result.tokens.filter(token => 
          !result.positive.includes(token) && !result.negative.includes(token)
        )
      }
    };
  }

  /**
   * 言語検出
   */
  private detectLanguage(text: string): 'ja' | 'en' | 'unknown' {
    const detected = franc(text);
    
    if (detected === 'jpn') return 'ja';
    if (detected === 'eng') return 'en';
    
    // fallback: ひらがな・カタカナ・漢字の存在で日本語判定
    if (/[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]/.test(text)) {
      return 'ja';
    }
    
    return 'en'; // デフォルトは英語
  }

  /**
   * 日本語テキストの簡易分かち書き
   * TinySegmenterの代替として基本的な分割を実装
   */
  private segmentJapaneseText(text: string): string[] {
    // 簡易的な分かち書き（実際のプロダクションではTinySegmenterを使用）
    const words: string[] = [];
    const cleanText = text.replace(/[！？。、・「」『』（）\s]+/g, ' ');
    
    // ひらがな・カタカナ・漢字・アルファベット・数字で分割
    const segments = cleanText.match(/[\u3040-\u309F]+|[\u30A0-\u30FF]+|[\u4E00-\u9FAF]+|[a-zA-Z]+|[0-9]+/g) || [];
    
    for (const segment of segments) {
      if (segment.length >= 2) {
        words.push(segment);
      }
    }
    
    return words;
  }

  /**
   * 日本語感情辞書の初期化
   */
  private initializeJapaneseDictionary(): void {
    // ポジティブワード
    this.japanesePositiveWords = new Set([
      // 基本的なポジティブ語
      '良い', 'よい', 'いい', '素晴らしい', '優秀', '成功', '利益', '収益', '好調', '上昇',
      '増加', '成長', '拡大', '向上', '改善', '最高', '最良', '優れる', '勝利', '達成',
      
      // ビジネス・投資関連ポジティブ語
      '黒字', '増収', '増益', '上方修正', '好業績', '躍進', '飛躍', '革新', '画期的',
      'breakthrough', '好材料', '追い風', '強い', '堅調', '安定', '確実', '有望',
      
      // 感情表現
      '嬉しい', '楽しい', '満足', '安心', '期待', '希望', '喜び', '幸せ', '快適',
      '魅力的', '素敵', '美しい', '感動', '驚き', '興味深い', '面白い'
    ]);

    // ネガティブワード
    this.japaneseNegativeWords = new Set([
      // 基本的なネガティブ語
      '悪い', 'わるい', 'だめ', 'ダメ', '失敗', '損失', '赤字', '下落', '減少',
      '悪化', '低下', '縮小', '最悪', '困難', '問題', '課題', '危険', '危機',
      
      // ビジネス・投資関連ネガティブ語
      '赤字', '減収', '減益', '下方修正', '不振', '低迷', '苦戦', '悪材料',
      '逆風', '弱い', '不安定', '不確実', 'リスク', '懸念', '警戒', '売り',
      
      // 感情表現
      '悲しい', '辛い', '苦しい', '不安', '心配', '恐怖', '怒り', '失望',
      'がっかり', '残念', '困る', '疲れる', 'ストレス', '不満', '嫌'
    ]);
  }

  /**
   * 日本語感情語の重みを取得
   */
  private getJapaneseWordWeight(word: string, type: 'positive' | 'negative'): number {
    // 強い感情語には高い重みを設定
    const strongWords = {
      positive: ['素晴らしい', '最高', '最良', '画期的', '躍進', '飛躍'],
      negative: ['最悪', '危機', '失敗', '赤字', '暴落', '崩壊']
    };

    if (strongWords[type].includes(word)) {
      return 2.0;
    }

    // ビジネス関連語には中程度の重み
    const businessWords = {
      positive: ['増収', '増益', '上方修正', '好業績', '黒字'],
      negative: ['減収', '減益', '下方修正', '不振', '赤字']
    };

    if (businessWords[type].includes(word)) {
      return 1.5;
    }

    return 1.0; // デフォルト重み
  }

  /**
   * 複数のニュース記事の感情分析
   */
  async analyzeMultipleTexts(texts: string[]): Promise<SentimentResult[]> {
    const results: SentimentResult[] = [];
    
    for (const text of texts) {
      const result = await this.analyzeSentiment(text);
      results.push(result);
    }
    
    return results;
  }

  /**
   * 感情分析結果の要約統計
   */
  calculateSentimentSummary(results: SentimentResult[]): {
    averageScore: number;
    averageMagnitude: number;
    averageConfidence: number;
    positiveCount: number;
    negativeCount: number;
    neutralCount: number;
    overallSentiment: 'positive' | 'negative' | 'neutral';
  } {
    if (results.length === 0) {
      return {
        averageScore: 0,
        averageMagnitude: 0,
        averageConfidence: 0,
        positiveCount: 0,
        negativeCount: 0,
        neutralCount: 0,
        overallSentiment: 'neutral'
      };
    }

    const totalScore = results.reduce((sum, r) => sum + r.score, 0);
    const totalMagnitude = results.reduce((sum, r) => sum + r.magnitude, 0);
    const totalConfidence = results.reduce((sum, r) => sum + r.confidence, 0);

    const averageScore = totalScore / results.length;
    const averageMagnitude = totalMagnitude / results.length;
    const averageConfidence = totalConfidence / results.length;

    const positiveCount = results.filter(r => r.score > 0.1).length;
    const negativeCount = results.filter(r => r.score < -0.1).length;
    const neutralCount = results.length - positiveCount - negativeCount;

    let overallSentiment: 'positive' | 'negative' | 'neutral';
    if (averageScore > 0.1) {
      overallSentiment = 'positive';
    } else if (averageScore < -0.1) {
      overallSentiment = 'negative';
    } else {
      overallSentiment = 'neutral';
    }

    return {
      averageScore,
      averageMagnitude,
      averageConfidence,
      positiveCount,
      negativeCount,
      neutralCount,
      overallSentiment
    };
  }
}