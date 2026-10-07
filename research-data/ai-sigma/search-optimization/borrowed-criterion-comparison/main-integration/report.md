# 残差入力scratchのmain統合

評価ごとの一時入力確保を、Search呼出しがsetupで一度確保するVecと借用sliceへ置き換える。固定数学・重み・特徴・FT・探索順序・TTを保持する。繰返し診断workerも自身のworkspaceを再用し、one-shot evaluateは同じ数学入口へsetup込みで入る。

独立ownership/APIレビューは重大指摘0。完全な凍結production3file（test初期化と独立oracleを含む）を採用し、測定済borrowed Criterion benchは記述labelだけを保守用へ変更した。旧比較source/raw/imageは保存し、実験用search_cost・互換feature・別searcherを現役へ追加しない。

レビューD1は運用文書へ反映した。SearchSession/TT寿命ではなく探索呼出し単位のworkspace、形状不一致errorとresizeなし、Zero4入力、非残差default委譲を明示。head timerはFT/workspace setup外、cold/warm target SearchはrootFT/workspace setup/drop込み。

既存証拠では通常head88,727回のalloc/realloc0、各root setup280B一回。独立bit/reference/full-delta/親復帰/error/cancel/reentrant証拠は停止SHA付きで再用する。Criterion固定退行条件0/5は、無退行証明や速度利益ではない。旧短測定のwhole+2.50%など負結果も保持し、profile条件は発動しなかった。

統合後ソフトウェア検証job bdca85f6は2026-10-07T03:32:10.932605Zにexit0/全6command directwait/cleanup[]で終了した（全費66.113156112秒）。CountedのNN0 mock adapter一件、現役bench no-run/model-unset early help、関連lib/runner/bench Clippyのみ。Mockは二回の計数を検査し、物理model/NN/FT/GPU forwardは0。既存モデル数値suiteの再実行、統計比較、学習再開は行わない。Counted mockはexact名の1PASS、bench no-run/model未指定helpとlib/runner/bench Clippy -D warningsはすべてPASS。記録済みscience identitiesをfresh再確認して不在、採用source/lock SHAも一致した。共有bench ELFは現main a47dbeddへ更新され、旧c6/Bf151は保存比較imageに残る。shared target成長peakはNOT_RECORDED、RSS sample176,857,088B/専有output sample163,840Bは上限内。独立モデルの実数値やdefault Float/Quantized新runtime suiteを追加資格済みとは扱わない。

実行枠はCPU0,1/RAMfamily2GiB/GPU0、科学的時間・forward上限null。専有小output/RSS/owner pause/exact childwaitを維持し、shared targetはsole writer。closed298の必要25,669,632Bを保持して将来余剰7MiBをRootへ移譲し、Root10MiB予測10,223,616Bを採用。親12GiB、探索256MiB、paused学習1048MiB、UNKNOWN128MiB、旧費・実資産は変更しない。
