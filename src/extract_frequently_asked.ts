/**
 * 頻出問題300抽出CLI
 * 
 * @description 過去の出題頻度、正答率、有識者評価を組み合わせて上位300問を抽出します。
 * 毎年出題される問題には特別なボーナスを付与します。
 * 
 * 使用方法:
 *   npm run extract-frequently-asked -- --output=./output/top300.json
 */

import * as fs from 'fs';
import * as path from 'path';
import { FrequentlyAskedService } from './frequently_asked_service';
import { FrequentlyAskedScoreConfig } from './utils/score';

// ロギング設定
import * as log4js from 'log4js';
const logger = log4js.getLogger('extract_frequently_asked');
logger.level = process.env.LOG_LEVEL || 'info';

// DB設定を読み込み
import * as dotenv from 'dotenv';
dotenv.config();

const dbConfig = {
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432', 10),
  database: process.env.DB_NAME || 'exam_db',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '',
};

/**
 * コマンドライン引数を解析
 * 
 * @returns パース済みの引数オブジェクト
 */
function parseArgs(): Record<string, string> {
  const args: Record<string, string> = {};
  
  for (let i = 2; i < process.argv.length; i++) {
    const arg = process.argv[i];
    if (arg.startsWith('--')) {
      const [key, value] = arg.slice(2).split('=');
      args[key] = value || 'true';
    }
  }
  
  return args;
}

/**
 * メイン処理
 */
async function main() {
  try {
    // 引数解析
    const args = parseArgs();
    const outputPath = args.output || path.join(__dirname, '../output/frequently_asked_top300.json');
    
    // 設定情報をログ出力
    logger.info('頻出問題300抽出ツール開始');
    logger.info(`ボーナス設定: 毎年出題=${FrequentlyAskedScoreConfig.EVERY_YEAR_BONUS}, 7/8年=${FrequentlyAskedScoreConfig.ALMOST_EVERY_YEAR_BONUS[7]}, 6/8年=${FrequentlyAskedScoreConfig.ALMOST_EVERY_YEAR_BONUS[6]}`);
    logger.info(`出力先: ${outputPath}`);
    
    // 出力先ディレクトリ確認
    const outputDir = path.dirname(outputPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
      logger.info(`出力ディレクトリを作成しました: ${outputDir}`);
    }
    
    // サービスインスタンス生成と初期化
    const service = new FrequentlyAskedService(dbConfig);
    await service.initialize();
    
    // 頻出問題抽出を実行
    const result = await service.extractTop300FrequentlyAskedQuestions(outputPath);
    
    // クリーンアップ
    await service.cleanup();
    
    // 結果の表示
    if (result.success) {
      logger.info('頻出問題300抽出が完了しました');
      logger.info(`抽出問題数: ${result.count}問`);
      logger.info(`毎年出題問題数: ${result.results.filter(q => q.isEveryYear).length}問`);
      logger.info(`出力ファイル: ${outputPath}`);
    } else {
      logger.error('頻出問題300抽出に失敗しました');
      process.exit(1);
    }
    
    process.exit(0);
  } catch (error) {
    logger.error('処理中にエラーが発生しました', error);
    process.exit(1);
  }
}

// スクリプト実行
main(); 