/**
 * Rate Limiter
 * 
 * API呼び出し制限とレート制御
 */

export class RateLimiter {
  private requests: number[] = [];
  private readonly maxRequests: number;
  private readonly windowMs: number;
  private readonly minInterval: number;
  private lastRequestTime: number = 0;

  constructor(maxRequests: number = 60, windowMs: number = 60000, minInterval: number = 1000) {
    this.maxRequests = maxRequests;  // 1分間に最大60リクエスト
    this.windowMs = windowMs;        // 1分間のウィンドウ
    this.minInterval = minInterval;  // リクエスト間の最小間隔（1秒）
  }

  /**
   * レート制限をチェックし、必要に応じて待機
   */
  async checkLimit(): Promise<void> {
    const now = Date.now();

    // 最小間隔チェック
    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < this.minInterval) {
      const waitTime = this.minInterval - timeSinceLastRequest;
      await this.sleep(waitTime);
    }

    // ウィンドウ内の古いリクエストを削除
    this.cleanOldRequests(now);

    // リクエスト数制限チェック
    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      const waitTime = this.windowMs - (now - oldestRequest);
      if (waitTime > 0) {
        console.log(`Rate limit reached. Waiting ${waitTime}ms...`);
        await this.sleep(waitTime);
        this.cleanOldRequests(Date.now());
      }
    }

    // 現在のリクエストを記録
    this.requests.push(now);
    this.lastRequestTime = now;
  }

  /**
   * 古いリクエストをクリーンアップ
   */
  private cleanOldRequests(now: number): void {
    const cutoff = now - this.windowMs;
    this.requests = this.requests.filter(timestamp => timestamp > cutoff);
  }

  /**
   * 指定時間待機
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 現在のレート制限状況を取得
   */
  getStatus(): {
    requestsInWindow: number;
    maxRequests: number;
    remainingRequests: number;
    windowMs: number;
    nextAvailableTime: number | null;
  } {
    const now = Date.now();
    this.cleanOldRequests(now);

    let nextAvailableTime: number | null = null;
    
    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      nextAvailableTime = oldestRequest + this.windowMs;
    }

    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < this.minInterval) {
      const minIntervalNext = this.lastRequestTime + this.minInterval;
      nextAvailableTime = nextAvailableTime ? 
        Math.max(nextAvailableTime, minIntervalNext) : 
        minIntervalNext;
    }

    return {
      requestsInWindow: this.requests.length,
      maxRequests: this.maxRequests,
      remainingRequests: Math.max(0, this.maxRequests - this.requests.length),
      windowMs: this.windowMs,
      nextAvailableTime,
    };
  }

  /**
   * レート制限をリセット
   */
  reset(): void {
    this.requests = [];
    this.lastRequestTime = 0;
  }

  /**
   * 設定を動的に変更
   */
  updateConfig(maxRequests?: number, windowMs?: number, minInterval?: number): void {
    if (maxRequests !== undefined) {
      this.maxRequests = maxRequests;
    }
    if (windowMs !== undefined) {
      this.windowMs = windowMs;
    }
    if (minInterval !== undefined) {
      this.minInterval = minInterval;
    }

    // 設定変更後、古いリクエストをクリーンアップ
    this.cleanOldRequests(Date.now());
  }
}