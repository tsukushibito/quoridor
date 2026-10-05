# ユーザー指示: 主要ディレクトリのREADMEとファイル案内を整備

ユーザーはroot提案に「その方針で。チームに伝えて。」と明示承認。現在frame21の研究と並行して、統括から既stewardへ実作業を配分する。新枠/自動延長/研究停止ではない。主研究の特徴・学習原因分析と探索高速化の優先度は維持する。

## 採用方針

AIエージェントが検索対象を絞ってからrgを使えるよう、責務・検索範囲が切り替わる主要ディレクトリに短いREADMEを配置する。全階層へ機械的に配置しない。

現物確認済み: root README/AGENTS、docs/development/ai-research-code.md、crates/quoridor-{nnue,inference,runner}/README.md、python/quoridor_training/README.md、tools/model-export/README.md は存在。これらを再用し重複案内を作らない。

整備候補: crates/README.mdでcrate責務・依存・個別入口、主要crateのREADMEで公開入口/主要module/対応test、tools/README.mdとscripts/README.mdで用途別実行入口、docs/README.mdで設計/実行手順/現在計画/過去報告、research-data/README.mdでデータ形式/manifest/保存結果への辿り方。既存構成/必要性を見て配置を調整してよい。

READMEの内容は『何を扱うか』『どのファイルから読むか』『関連する正本文書』『検証入口』。全file一覧/実装詳細/設計/契約/タスク状態を複製せず正本へリンクする。学習/対局/取得が起きるcommandと軽量checkを区別。現役Rust/Pythonと管理/製品Nodeの境界、凍結モデル/データとコード正本の区別が分かること。

AGENTS.mdは行動規約と案内へのリンク、READMEは構成説明。新しい必読/全資料読取/定期全体監査を増やさない。配置や入口変更時に対応READMEも更新する。構成案内・見直しはStewardの責務とし、必要な既文書に簡潔に反映する。全role定義/registry更新を一律に発生させず、既責務で実行できる部分は進める。

## 配分・検証・終了

統括が既stewardの現在owned運用責任/編集pathを確認しBeadsで問い・owner・main専用path・軽量予算・検証・終了へ具体化し全文配送する。同steward activeなら正確turnへ追補、idleなら既savedで開始、重複writer/新役0。現在main正本、旧WTへ恒常mirror0、他者source/index保持。Git/indexは現在統合ownerと調整する。

検証は現物入口/相対linkの存在と責務の対応に必要な範囲。文書整備を理由にモデルforward/train/game/build/取得やCPU測定競合を起こさない。整理削除/コードリファクタリング/新生成をこの依頼へ追加しない。枠終了10:37:54UTCと92の停止責任を維持し、枠内に入り切らない分は具体担当/次機会を保存、自動延長0。

root宛報告には実配分/本人開始、整備した入口と不足を示す。全稿/rootACKを研究gateにしない。今回指示の配送/結果は継続goal quoridor-4lcへ記録する。
