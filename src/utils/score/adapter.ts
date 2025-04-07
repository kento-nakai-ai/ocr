/**
 * 合格率計算アダプター
 * 
 * @description 既存のシステムと合格率計算モジュールを連携させるためのアダプターを提供します。
 * 異なるデータ形式への変換や、他システムとの統合を容易にします。
 */

import { calculateScore, QuestionDifficulty, Question, UserAnswer, ScoreResult } from './index';
import { formatScoreDetails, isPassing, getScoreMessage } from './utils';

/**
 * 合格率計算アダプタークラス
 * 異なるシステムや形式からのデータを受け入れ、合格率計算モジュールと連携します
 */
export class ScoreCalculator {
  /**
   * データベースから取得した問題と回答データから合格率を計算します
   * 
   * @param dbQuestions データベースから取得した問題データ
   * @param dbUserAnswers データベースから取得した回答データ
   * @returns 合格率計算結果
   */
  static calculateFromDbFormat(
    dbQuestions: any[],
    dbUserAnswers: any[]
  ): ScoreResult {
    // データベース形式から内部形式に変換
    const questions: Question[] = dbQuestions.map((q) => ({
      id: q.id,
      isMandatory: q.is_mandatory === 1 || q.is_mandatory === true,
      difficulty: this.mapDifficultyFromDb(q.difficulty),
    }));

    const userAnswers: UserAnswer[] = dbUserAnswers.map((a) => ({
      questionId: a.question_id,
      isCorrect: a.is_correct === 1 || a.is_correct === true,
    }));

    // 合格率計算
    return calculateScore({ questions, userAnswers });
  }

  /**
   * 合格率と詳細情報を含む人間が読みやすい形式の文字列を生成します
   * 
   * @param result 合格率計算結果
   * @returns フォーマットされた合格率と詳細情報
   */
  static formatResult(result: ScoreResult): string {
    return formatScoreDetails(result);
  }

  /**
   * 合格率を評価し、適切なメッセージを返します
   * 
   * @param score 合格率
   * @returns 合格率に応じたメッセージ
   */
  static getEvaluationMessage(score: number): string {
    return getScoreMessage(score);
  }

  /**
   * 合格したかどうかを判定します
   * 
   * @param score 合格率
   * @param threshold 合格ライン（デフォルト: 60%）
   * @returns 合格したかどうか
   */
  static hasPassed(score: number, threshold: number = 60): boolean {
    return isPassing(score, threshold);
  }

  /**
   * APIレスポンス用の合格率情報を作成します
   * 
   * @param result 合格率計算結果
   * @returns APIレスポンス用のオブジェクト
   */
  static createApiResponse(result: ScoreResult): any {
    const { finalScore, details } = result;
    const passed = this.hasPassed(finalScore);
    
    return {
      score: finalScore,
      passed: passed,
      evaluation: this.getEvaluationMessage(finalScore),
      details: {
        base_score: details.baseScore,
        mandatory_factor: details.mandatoryFactor,
        difficulty_bonus: details.difficultyBonus,
        total_questions: details.totalQuestions,
        correct_answers: details.correctAnswers,
        mandatory_questions: details.mandatoryQuestions,
        correct_mandatory: details.correctMandatory,
        high_difficulty_correct: details.correctByDifficulty[QuestionDifficulty.HIGH],
      },
    };
  }

  /**
   * データベースの難易度値を内部形式の難易度に変換します
   * 
   * @param dbDifficulty データベースの難易度値
   * @returns 内部形式の難易度
   */
  private static mapDifficultyFromDb(dbDifficulty: string | number): QuestionDifficulty {
    // 文字列の場合
    if (typeof dbDifficulty === 'string') {
      const upperDifficulty = dbDifficulty.toUpperCase();
      if (upperDifficulty === 'HIGH' || upperDifficulty === 'H') {
        return QuestionDifficulty.HIGH;
      } else if (upperDifficulty === 'MID' || upperDifficulty === 'M' || upperDifficulty === 'MEDIUM') {
        return QuestionDifficulty.MID;
      } else {
        return QuestionDifficulty.LOW;
      }
    }
    
    // 数値の場合（例: 1=LOW, 2=MID, 3=HIGH）
    if (typeof dbDifficulty === 'number') {
      if (dbDifficulty >= 3) {
        return QuestionDifficulty.HIGH;
      } else if (dbDifficulty === 2) {
        return QuestionDifficulty.MID;
      } else {
        return QuestionDifficulty.LOW;
      }
    }
    
    // デフォルトはLOW
    return QuestionDifficulty.LOW;
  }
} 