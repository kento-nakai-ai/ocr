/**
 * 合格率計算に関連するユーティリティ関数
 * 
 * @description 合格率計算の補助や、データ変換、フォーマット関数などを提供します。
 */

import { ScoreResult } from './types';
import { ScoreConfig } from './config';

/**
 * 合格率の詳細情報を人間が読みやすい形式にフォーマットする関数
 * 
 * @param result 合格率計算結果
 * @returns フォーマットされた詳細情報
 */
export const formatScoreDetails = (result: ScoreResult): string => {
  const { finalScore, details } = result;
  const {
    baseScore,
    mandatoryFactor,
    difficultyBonus,
    totalQuestions,
    correctAnswers,
    mandatoryQuestions,
    correctMandatory,
    correctByDifficulty
  } = details;

  return `
合格率: ${finalScore}%

＜詳細情報＞
総問題数: ${totalQuestions}問（正解: ${correctAnswers}問）
基本スコア: ${baseScore.toFixed(1)}%
必須問題: ${correctMandatory}/${mandatoryQuestions}問正解（係数: ${mandatoryFactor.toFixed(3)}）
難易度ボーナス: +${difficultyBonus.toFixed(1)}%（HIGH問題${correctByDifficulty.HIGH}問正解）

計算式: ${baseScore.toFixed(1)}% × ${mandatoryFactor.toFixed(3)} + ${difficultyBonus.toFixed(1)}% = ${finalScore}%
  `.trim();
};

/**
 * 合格判定を行う関数
 * 
 * @param score 合格率
 * @param passingThreshold 合格ライン（デフォルト60%）
 * @returns 合格したかどうか
 */
export const isPassing = (score: number, passingThreshold: number = 60): boolean => {
  return score >= passingThreshold;
};

/**
 * 合格率に応じたメッセージを生成する関数
 * 
 * @param score 合格率
 * @returns 合格率に応じたメッセージ
 */
export const getScoreMessage = (score: number): string => {
  if (score >= 90) {
    return '素晴らしい成績です！本番でも合格の可能性が非常に高いでしょう。';
  } else if (score >= 80) {
    return '良い成績です。本番に向けてこの調子で続けましょう。';
  } else if (score >= 70) {
    return 'まずまずの成績です。さらに得点を伸ばす余地があります。';
  } else if (score >= 60) {
    return '合格ラインですが、余裕を持って本番に臨むためにもう少し学習を続けましょう。';
  } else if (score >= 50) {
    return '合格ラインに近づいています。もう少し頑張りましょう。';
  } else {
    return '合格ラインには届いていません。苦手分野を重点的に学習しましょう。';
  }
}; 