/**
 * Symbol Validator
 * 
 * 銘柄コードの正規化・検証・提案機能
 */

export interface SymbolValidation {
  isValid: boolean;
  normalizedSymbol: string;
  marketType: 'japan' | 'us' | 'unknown';
  suggestions: string[];
  errors: string[];
}

export class SymbolValidator {
  private japanStockPatterns = [
    /^\d{4}\.T$/,      // 4桁.T (例: 7203.T)
    /^\d{4}$/,         // 4桁のみ (例: 7203)
  ];

  private usStockPatterns = [
    /^[A-Z]{1,5}$/,    // 1-5文字の大文字 (例: AAPL, MSFT)
    /^[A-Z]{1,4}\.[A-Z]{1,2}$/,  // ティッカー.取引所 (例: BRK.A)
  ];

  // よく使われる日本株銘柄
  private commonJapanStocks = {
    '7203': 'トヨタ自動車',
    '6758': 'ソニーグループ',
    '9984': 'ソフトバンクグループ',
    '8306': '三菱UFJフィナンシャル・グループ',
    '6861': 'キーエンス',
    '9437': 'NTTドコモ',
    '4063': '信越化学工業',
    '6594': '日本電産',
    '8031': '三井物産',
    '9432': '日本電信電話',
  };

  // よく使われる米国株銘柄
  private commonUSStocks = {
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'TSLA': 'Tesla Inc.',
    'META': 'Meta Platforms Inc.',
    'NVDA': 'NVIDIA Corporation',
    'JPM': 'JPMorgan Chase & Co.',
    'JNJ': 'Johnson & Johnson',
    'V': 'Visa Inc.',
  };

  /**
   * 銘柄コードを正規化
   */
  normalizeSymbol(symbol: string): string {
    const cleaned = symbol.trim().toUpperCase();

    // 日本株の場合
    if (/^\d{4}$/.test(cleaned)) {
      return `${cleaned}.T`;
    }

    // 既に正規化されている場合はそのまま
    return cleaned;
  }

  /**
   * 銘柄コードを検証
   */
  validateSymbol(symbol: string): SymbolValidation {
    const errors: string[] = [];
    const suggestions: string[] = [];
    
    if (!symbol || symbol.trim().length === 0) {
      return {
        isValid: false,
        normalizedSymbol: '',
        marketType: 'unknown',
        suggestions: [],
        errors: ['Symbol cannot be empty'],
      };
    }

    const normalizedSymbol = this.normalizeSymbol(symbol);
    let marketType: 'japan' | 'us' | 'unknown' = 'unknown';
    let isValid = false;

    // 日本株パターンチェック
    if (this.japanStockPatterns.some(pattern => pattern.test(normalizedSymbol))) {
      marketType = 'japan';
      isValid = true;

      // 日本株の範囲チェック
      const stockCode = normalizedSymbol.replace('.T', '');
      const code = parseInt(stockCode);
      if (code < 1000 || code > 9999) {
        errors.push('Japanese stock code should be between 1000-9999');
        isValid = false;
      }

      // 一般的な銘柄の提案
      if (this.commonJapanStocks[stockCode]) {
        suggestions.push(`${stockCode}: ${this.commonJapanStocks[stockCode]}`);
      }
    }
    // 米国株パターンチェック
    else if (this.usStockPatterns.some(pattern => pattern.test(normalizedSymbol))) {
      marketType = 'us';
      isValid = true;

      // 一般的な銘柄の提案
      if (this.commonUSStocks[normalizedSymbol]) {
        suggestions.push(`${normalizedSymbol}: ${this.commonUSStocks[normalizedSymbol]}`);
      }
    }
    // 不明なパターン
    else {
      errors.push('Invalid symbol format');
      
      // 類似パターンの提案
      this.generateSuggestions(symbol, suggestions);
    }

    return {
      isValid,
      normalizedSymbol,
      marketType,
      suggestions,
      errors,
    };
  }

  /**
   * 類似銘柄の提案生成
   */
  private generateSuggestions(input: string, suggestions: string[]): void {
    const cleaned = input.trim().toUpperCase();

    // 数字のみの場合（日本株の可能性）
    if (/^\d+$/.test(cleaned)) {
      if (cleaned.length === 4) {
        suggestions.push(`${cleaned}.T (Japanese stock)`);
      } else if (cleaned.length < 4) {
        const padded = cleaned.padStart(4, '0');
        suggestions.push(`${padded}.T (Japanese stock with leading zeros)`);
      } else if (cleaned.length > 4) {
        const truncated = cleaned.substring(0, 4);
        suggestions.push(`${truncated}.T (Japanese stock, truncated)`);
      }
    }

    // アルファベットのみの場合（米国株の可能性）
    if (/^[A-Z]+$/i.test(cleaned)) {
      if (cleaned.length <= 5) {
        suggestions.push(`${cleaned} (US stock)`);
      }
    }

    // 部分マッチによる提案
    this.addPartialMatches(cleaned, suggestions);
  }

  /**
   * 部分マッチによる提案追加
   */
  private addPartialMatches(input: string, suggestions: string[]): void {
    const inputLower = input.toLowerCase();

    // 日本株での部分マッチ
    for (const [code, name] of Object.entries(this.commonJapanStocks)) {
      if (code.includes(inputLower) || name.toLowerCase().includes(inputLower)) {
        suggestions.push(`${code}.T: ${name}`);
      }
    }

    // 米国株での部分マッチ
    for (const [symbol, name] of Object.entries(this.commonUSStocks)) {
      if (symbol.toLowerCase().includes(inputLower) || 
          name.toLowerCase().includes(inputLower)) {
        suggestions.push(`${symbol}: ${name}`);
      }
    }

    // 提案数を制限
    if (suggestions.length > 5) {
      suggestions.splice(5);
    }
  }

  /**
   * 市場タイプを判定
   */
  getMarketType(symbol: string): 'japan' | 'us' | 'unknown' {
    const normalized = this.normalizeSymbol(symbol);
    
    if (this.japanStockPatterns.some(pattern => pattern.test(normalized))) {
      return 'japan';
    }
    
    if (this.usStockPatterns.some(pattern => pattern.test(normalized))) {
      return 'us';
    }
    
    return 'unknown';
  }

  /**
   * サンプル銘柄を取得
   */
  getSampleSymbols(marketType: 'japan' | 'us', count: number = 5): string[] {
    if (marketType === 'japan') {
      return Object.keys(this.commonJapanStocks)
        .slice(0, count)
        .map(code => `${code}.T`);
    } else {
      return Object.keys(this.commonUSStocks).slice(0, count);
    }
  }

  /**
   * 銘柄名を取得（可能な場合）
   */
  getSymbolName(symbol: string): string | null {
    const normalized = this.normalizeSymbol(symbol);
    
    // 日本株
    if (normalized.endsWith('.T')) {
      const code = normalized.replace('.T', '');
      return this.commonJapanStocks[code] || null;
    }
    
    // 米国株
    return this.commonUSStocks[normalized] || null;
  }
}