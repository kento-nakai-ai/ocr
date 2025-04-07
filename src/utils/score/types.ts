/**
 * 合格率計算に関する型定義ファイル
 * 
 * @description 合格率計算に必要な入力データや出力データの型を定義します。
 * これにより、型安全な実装と将来的な拡張を容易にします。
 */

/**
 * 問題の難易度を表す列挙型
 */
export enum QuestionDifficulty {
  LOW = 'LOW',
  MID = 'MID',
  HIGH = 'HIGH',
}

/**
 * 問題データの型定義
 */
export interface Question {
  /** 問題ID */
  id: string | number;
  /** 問題が必須かどうか */
  isMandatory: boolean;
  /** 問題の難易度 */
  difficulty: QuestionDifficulty;
}

/**
 * ユーザーの回答データの型定義
 */
export interface UserAnswer {
  /** 問題ID */
  questionId: string | number;
  /** 正解かどうか */
  isCorrect: boolean;
}

/**
 * 合格率計算の入力データ型
 */
export interface ScoreCalculationInput {
  /** 解答した問題のリスト */
  questions: Question[];
  /** ユーザーの回答リスト */
  userAnswers: UserAnswer[];
}

/**
 * 合格率計算の結果データ型
 */
export interface ScoreResult {
  /** 最終的な合格率 */
  finalScore: number;
  /** 内訳情報 */
  details: {
    /** 基本スコア (正解数/全問題数) */
    baseScore: number;
    /** 必須問題係数 */
    mandatoryFactor: number;
    /** 難易度ボーナス */
    difficultyBonus: number;
    /** 総問題数 */
    totalQuestions: number;
    /** 正解数 */
    correctAnswers: number;
    /** 必須問題数 */
    mandatoryQuestions: number;
    /** 必須問題の正解数 */
    correctMandatory: number;
    /** 難易度別の正解数 */
    correctByDifficulty: {
      [QuestionDifficulty.LOW]: number;
      [QuestionDifficulty.MID]: number;
      [QuestionDifficulty.HIGH]: number;
    };
  };
} 