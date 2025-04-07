/**
 * 頻出問題抽出サービス
 * 
 * @description 過去問から頻出問題300を抽出するためのサービスクラス。
 * 毎年出題される問題には特別なボーナスを付与し、スコアリングを行います。
 */

import { promises as fs } from 'fs';
import * as path from 'path';
import * as db from './db_utils';
import { 
  FrequentlyAskedQuestionData,
  FrequentlyAskedScoreResult,
  calculateFrequentlyAskedScore,
  selectTop300FrequentlyAskedQuestions,
  selectUniqueTop300FrequentlyAskedQuestions,
  FrequentlyAskedScoreConfig
} from './utils/score';
import { TagManager } from './tag_manager';

// ロギング設定
import * as log4js from 'log4js';
const logger = log4js.getLogger('FrequentlyAskedService');
logger.level = process.env.LOG_LEVEL || 'info';

interface QuestionMetadata {
  id: string;
  content: string;
  yearList: string[];
  accuracy: number;
  expertScore: number;
}

/**
 * 頻出問題サービスクラス
 */
export class FrequentlyAskedService {
  private tagManager: TagManager;
  private dbConnection: any;

  /**
   * コンストラクタ
   * 
   * @param dbConfig データベース接続設定
   */
  constructor(dbConfig: any) {
    this.tagManager = new TagManager(dbConfig);
    this.dbConnection = null;
  }

  /**
   * データベース接続を初期化
   */
  public async initialize(): Promise<void> {
    try {
      this.dbConnection = await db.getConnection();
      logger.info('データベース接続を初期化しました');
    } catch (error) {
      logger.error('データベース接続の初期化に失敗しました', error);
      throw error;
    }
  }

  /**
   * 頻出問題300を抽出して保存する
   * 
   * @param outputPath 出力先ファイルパス
   * @returns 処理結果と抽出された問題数
   */
  public async extractTop300FrequentlyAskedQuestions(
    outputPath: string
  ): Promise<{ success: boolean; count: number; results: FrequentlyAskedScoreResult[] }> {
    try {
      // 1. すべての問題とその出題年度を取得
      const questions = await this.fetchAllQuestionsWithYearList();
      logger.info(`総問題数: ${questions.length}件`);

      // 2. 問題ごとに正答率と有識者評価を取得
      const questionsWithMetadata = await this.appendQuestionMetadata(questions);

      // 3. 頻出問題スコアを計算して上位300問を抽出
      const top300Questions = selectTop300FrequentlyAskedQuestions(questionsWithMetadata);
      
      // 4. 結果をJSONファイルとして保存
      await this.saveResultsToFile(top300Questions, outputPath);
      
      // 5. 頻出問題のタグ付け（DBに記録）
      await this.tagTop300Questions(top300Questions);

      return {
        success: true,
        count: top300Questions.length,
        results: top300Questions
      };

    } catch (error) {
      logger.error('頻出問題300抽出処理に失敗しました', error);
      return {
        success: false,
        count: 0,
        results: []
      };
    }
  }

  /**
   * すべての問題とその出題年度を取得
   * 
   * @returns 問題データのリスト
   */
  private async fetchAllQuestionsWithYearList(): Promise<QuestionMetadata[]> {
    try {
      // TagManagerを使って全問題と出題年度を取得
      const rawQuestions = await this.tagManager.get_frequently_asked_questions(1);
      
      return rawQuestions.map(q => {
        // year_listフィールドがJSON文字列なのでパース
        let yearList: string[] = [];
        try {
          if (q.year_list) {
            yearList = JSON.parse(q.year_list);
          }
        } catch (e) {
          logger.warn(`問題ID ${q.question_id} の出題年度リストのパースに失敗: ${e}`);
        }

        return {
          id: q.question_id,
          content: q.content,
          yearList: yearList,
          accuracy: 0, // 後で設定
          expertScore: 0 // 後で設定
        };
      });
    } catch (error) {
      logger.error('問題データの取得に失敗しました', error);
      throw error;
    }
  }

  /**
   * 問題に正答率と有識者評価の情報を追加
   * 
   * @param questions 問題データのリスト
   * @returns 正答率と有識者評価を含む問題データのリスト
   */
  private async appendQuestionMetadata(
    questions: QuestionMetadata[]
  ): Promise<FrequentlyAskedQuestionData[]> {
    try {
      // IDのリストを作成
      const questionIds = questions.map(q => q.id);
      
      // 正答率情報を取得（DBから）
      const accuracyData = await this.fetchAccuracyData(questionIds);
      
      // 有識者評価を取得（DBから）
      const expertScoreData = await this.fetchExpertScoreData(questionIds);
      
      // 情報を統合
      return questions.map(question => {
        const accuracy = accuracyData[question.id] || 0.5; // デフォルト値：50%
        const expertScore = expertScoreData[question.id] || 0.5; // デフォルト値：0.5（中間）
        
        return {
          ...question,
          accuracy,
          expertScore
        };
      });
    } catch (error) {
      logger.error('問題メタデータの取得に失敗しました', error);
      throw error;
    }
  }

  /**
   * 問題の正答率データを取得
   * 
   * @param questionIds 問題IDのリスト
   * @returns 問題IDをキー、正答率を値とするオブジェクト
   */
  private async fetchAccuracyData(questionIds: string[]): Promise<Record<string, number>> {
    try {
      // 実際のDBクエリは実装に応じて変更
      const query = `
        SELECT question_id, accuracy 
        FROM question_stats
        WHERE question_id IN (?)
      `;
      
      // 仮実装：実際のDBデータ取得に置き換える
      // この例では模擬データを返す
      const mockData: Record<string, number> = {};
      for (const id of questionIds) {
        // ランダムな正答率（50%〜90%）を生成
        mockData[id] = 0.5 + (Math.random() * 0.4);
      }
      
      return mockData;
    } catch (error) {
      logger.error('正答率データの取得に失敗しました', error);
      return {};
    }
  }

  /**
   * 問題の有識者評価データを取得
   * 
   * @param questionIds 問題IDのリスト
   * @returns 問題IDをキー、有識者評価を値とするオブジェクト
   */
  private async fetchExpertScoreData(questionIds: string[]): Promise<Record<string, number>> {
    try {
      // 実際のDBクエリは実装に応じて変更
      const query = `
        SELECT question_id, expert_score 
        FROM question_evaluations
        WHERE question_id IN (?)
      `;
      
      // 仮実装：実際のDBデータ取得に置き換える
      // この例では模擬データを返す
      const mockData: Record<string, number> = {};
      for (const id of questionIds) {
        // ランダムな評価（0.3〜1.0）を生成
        mockData[id] = 0.3 + (Math.random() * 0.7);
      }
      
      return mockData;
    } catch (error) {
      logger.error('有識者評価データの取得に失敗しました', error);
      return {};
    }
  }

  /**
   * 結果をJSONファイルとして保存
   * 
   * @param results 頻出問題スコア計算結果
   * @param outputPath 出力先ファイルパス
   */
  private async saveResultsToFile(
    results: FrequentlyAskedScoreResult[],
    outputPath: string
  ): Promise<void> {
    try {
      // 出力ディレクトリが存在しない場合は作成
      const dir = path.dirname(outputPath);
      await fs.mkdir(dir, { recursive: true });
      
      // 結果を保存
      const output = {
        generatedAt: new Date().toISOString(),
        config: FrequentlyAskedScoreConfig,
        totalQuestions: results.length,
        everyYearQuestions: results.filter(r => r.isEveryYear).length,
        questions: results
      };
      
      await fs.writeFile(
        outputPath,
        JSON.stringify(output, null, 2),
        'utf-8'
      );
      
      logger.info(`頻出問題300リストを ${outputPath} に保存しました`);
    } catch (error) {
      logger.error(`結果の保存に失敗しました: ${error}`);
      throw error;
    }
  }

  /**
   * 頻出問題300にタグ付け
   * 
   * @param top300Questions 頻出問題スコア計算結果
   */
  private async tagTop300Questions(
    top300Questions: FrequentlyAskedScoreResult[]
  ): Promise<void> {
    try {
      // タグKeyを定義
      const TOP_300_TAG = 'top_300_frequently_asked';
      const EVERY_YEAR_TAG = 'every_year_question';
      
      // タグ定義が存在しない場合は作成
      try {
        await this.tagManager.add_tag_definition(
          TOP_300_TAG,
          'Boolean',
          '頻出度上位300問を示すフラグ',
          ['true', 'false'],
          '頻出問題300自動抽出プロセスで付与'
        );
      } catch (e) {
        // 既に存在する場合はエラーを無視
      }
      
      try {
        await this.tagManager.add_tag_definition(
          EVERY_YEAR_TAG,
          'Boolean',
          '毎年出題される問題を示すフラグ',
          ['true', 'false'],
          '過去8年間すべてで出題された問題'
        );
      } catch (e) {
        // 既に存在する場合はエラーを無視
      }
      
      // 各問題にタグ付け
      for (const question of top300Questions) {
        // top_300_frequently_askedタグを付与
        await this.tagManager.add_tag_to_question(
          question.questionId,
          TOP_300_TAG,
          'true',
          `Score: ${question.finalScore.toFixed(2)}`,
          `自動計算: ${new Date().toISOString()}`
        );
        
        // 毎年出題問題にはevery_year_questionタグも付与
        if (question.isEveryYear) {
          await this.tagManager.add_tag_to_question(
            question.questionId,
            EVERY_YEAR_TAG,
            'true',
            `YearList: ${JSON.stringify(question.yearList)}`,
            `自動計算: ${new Date().toISOString()}`
          );
        }
      }
      
      logger.info(`${top300Questions.length}問にタグ付けを行いました`);
    } catch (error) {
      logger.error(`頻出問題へのタグ付けに失敗しました: ${error}`);
      throw error;
    }
  }

  /**
   * クリーンアップ処理
   */
  public async cleanup(): Promise<void> {
    try {
      if (this.dbConnection) {
        await db.releaseConnection(this.dbConnection);
        logger.info('データベース接続を解放しました');
      }
    } catch (error) {
      logger.error('クリーンアップ処理に失敗しました', error);
    }
  }
} 