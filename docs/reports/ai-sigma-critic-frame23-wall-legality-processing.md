# 壁合法性・到達性処理の同情報比較 / quoridor-4lc.288

caller-local DSU と共通 WallEdges を使う合法壁生成を、現在 main の exact 経路と同一仕事で比較した。固定4prefix、depth2、nodecap1200、D(0,8)と保存NNUEモデルの全56組で Action・value bits・PV・depth・nodes・評価数・TT・履歴復帰が一致した。2科学jobでnativeNN36,732、課金processed114,658。main採用は統括の別ownerレビューに渡す。

Position のフィールドと Copy 構成を維持した。単独 legal_wall/play は exact を維持し、legal_action_ids 内だけに10×10 wall-post DSU と blocked-edge mask を構築する。全borderを接続し、候補の両端と中点の3postに同componentがあればexact到達性へ戻る。基準pawnが到達不能なら元の壁全不許可を維持する。NNUE数学・IDs・STM・距離・履歴鍵・TT・orderingを変えない。

独立scalar edge/queue oracleの4test、counter unit、midpoint H27反例、到達不能基準、rotation/P2、stock0、terminal/jump、決定的prefixの候補可否・Action集合がPASSした。4prefixのgeometry件数128/125/108/128、exact fallback0/1/5/0、skip128/124/103/128。両binaryの合法子1006件でScalar/SIMD/full-deltaと親復帰を有限確認した。skip率を探索・教師生成倍率へ換算しない。

## 性能の範囲

profiling featureを付けないLinux release、CPU3 single、同入力/model/binary条件を登録した。候補/基準の計時合計比は次の通り。各明細と初期warm試行を保存し、有利な試行のみを採らない。

| 系列                    |       D |    NNUE |
| ----------------------- | ------: | ------: |
| 初回forward steady4root | .454566 | .740728 |
| 初回reverse4root        | .428181 | .557049 |
| 確認forward8試行        | .386875 | .660692 |
| 確認reverse8試行        | .334795 | .521271 |

局所合法callerのsteady median比は .06020/.06853/.08728/.09363。DSU・mask・基準到達・candidate fallbackの費を含み、standalone play再検査は別に測った。NNUEの個別試行は初回initial1.06280、確認initial1.18293/jump1.33495の悪化もある。短いms単位の計時、cache/coldwarm/順序/host変動を含む少数root観測であり、production全体・同wall棋力・MCTS生成Rjointの利益は未測。

## 費用・失敗・停止

最初のsubmit Errno17、build中の285実CPU検出による自己SIGTERMと元zombie点を保持した。背景cleanup/currentexactabsenceは後続点証拠と区別する。元compile背景33.320393秒＋resume64.802067秒＝98.122460秒、最終core clippy child .354958秒。format/check等を含む保守compile117/120秒、source60/60・管理30/30を保持し、未測read/LLM/制御費を0にしない。科学child guardian合計1.054482秒、MAX2/3、事前hard bound135/240秒。parent admission/保存走査のUNKNOWNをchild時間へ混ぜず、重複加算しない。

確認前の相対cwd path失敗でformat preludeがNOT_RUNとなった。実科学は絶対argv、登録config SHA、専用task/schemaを検査して成功した。凍結データやconfigを後から整形しない。変更Rust3path rustfmt check、core libraryとwall_legality test clippy -D warnings、自己Python Ruffを確認した。runner example全target clippyは未実施、release compileは成功した。

## 統合境界

source-alignment-v1.jsonに旧279 archive保護と必要3pathのmain alignmentを記録した。比較binaryの元core・candidate、必要source/testsと実結果をlossless packへ保存する。mainへ渡す候補はproduction coreと独立correctness testsだけで、test-only caller counter、wall_work、旧AI/NNUE比較scaffoldは比較証拠として残し恒久APIへ入れない。本人Git/index/main source変更はない。

次の最小案は、実callerでまだ繰り返すstandalone play exact検査のboolean共通経路を、今回の採用後の費と保守費から選ぶこと。context rollbackや局所distance更新は別の高費候補として保留する。今枠に追加科学は行わず、287封印評価と291公開zレビューを維持する。
