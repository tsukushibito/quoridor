# 同算術NNUE入力バッファ候補の結果

固定学習済みH32モデルの入力バッファをinline70f32へ変更し、より広い構成はheap fallbackとした。限定正しさ検証は通ったが、plain探索全体の速度利益を支持できないためRootは不採用とする。main評価器は変更しない。

4組のAB/BA・8runの合計candidate/baseline時間比は外部プロセス全体1.009769、target検索1.026430。推論microは.961114だったが、中央値比は.989900で、単体の改善を全探索の利益へ外挿しない。80完了seed depth3・160完了target depth2の値bits/Action/PV/depth/nodes/公開counterは一致。固定BEST oracleはfull minimax・full/delta・Scalar/Simd FT・make/unmake・親履歴/ply/accumulatorで一致した。

比較は5固定prefix、一モデル、浅い探索、4組に限る。統計的な一般倍率・棋力を認定しない。softwareは両build、限定768+18forward fixture、AI7test、Clippyが通ったが、copyfileで実行bitが落ちて最初のモデルoracle起動が拒否された。原failed46.984624秒と修復を保持し、内容SHA不変の既binaryで未実行部分だけを完了した。最終job2.928990秒、native18子を直接waitし、guardian/controller cleanup・remaining空と記録PID不在を確認。

今回新forward2,073,640（合成786を含む）、既known211.146975秒。source/control30・旧support90・closure30予約を保持した合計上界361.146975秒はretained480内。原600=318 retained480+学習native120、原失敗とUNKNOWNは変えない。2jobを消費し、追加候補/測定の開始権限はない。

Rootは保存済み18process記録から時間比を再計算し、停止source4SHAを現byte照合、圧縮archive全memberを復元SHA照合した。新forward/build/testは実行していない。原結果は[summary.json.gz](summary.json.gz)、raw・各phase失敗/停止・凍結比較source/patch・設定/実行記録は[evidence.tar.gz](evidence.tar.gz)、全byte/SHAと受入れは[acceptance.json](acceptance.json)。モデルと比較ELFは既存WT/assets参照を保持し複製・削除しない。
