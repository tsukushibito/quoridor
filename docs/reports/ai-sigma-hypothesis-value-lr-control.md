# 188 学習率単因子CPU対照：NN0準備で停止

188はclaim・静的準備まで実施した。新科学開始期限2026-10-03 13:12 UTCまでにmodel jobを開始できず、LR .0025の効果は未測定。176の既定と181の代替modelの判断を変更しない。

受領13:02:32.710953809 UTC、静的実開始13:03:52.463619 UTC。配送accepted、claim、静的実開始は学習開始とは別である。初回配送本文の「13:03より前」という時計表現は誤りで、preregisterの実時計を正とする。

13:11台の管理commandは未導入の`python`を呼びexit127で終了した。管理scriptの生成・Git保存・science起動はいずれもそのcommandでは実行されなかった。13:12:22 UTCの再確認で期限超過を確認し、再送による学習を開始しなかった。187の静的intakeは確認したが、科学直前の完全なadmissionは未実施であり、物理空きや187を未実施理由に置き換えない。

実数はmodel読込0、学習step0、forward0、sample0、warm0、GPU0、checkpoint作成0、model子spawn0。子waitは該当せず、所有した科学PIDはない。停止速報をcoordinatorと187担当experimentへ配送し、両acceptedを確認した。これは結果の科学受入れではない。

私有CPU learnerと30秒/RSS896MiBのmanagerを保存した。学習開始前の13:12 guard、CPU8単logical、torch intra/inter1、weights_only CPU、LRだけ.0025、seed18180311/200step/batch128/manualSGD、26604sample cap、固定502validation、186とのabs1e-6+rtol1e-6対応、checkpoint weightbit reload/no forwardを記述した。ASTは確認済み、Torch import・実行・結果一致は未検証。managerは未知active processと187 scientific_startedを拒否する。managerの固定期限は停止版のまま保持し、この保存版で自動開始しない。

mixedtrain2260の元順を保持し、validation502は186のlineage/game/rowID順でID hash `9a8135d32480725478f493d017fbccc36c45c9c7102b7944a9a5eb40157c8141` に対応する。元dataset、176/181checkpoint、186 per-rowはreadonly参照で、173正式holdoutは読まなかった。新weights/model複製はない。

186では新4game中3gameのvalue退行、pi改善、015のwrong saturationが保存されている。188で低LRが緩和するかは欠測で、少数game相関、再利用validationで条件を選ぶ限界、容量/分布/step/教師qualityの原因未確定を保持する。

次の判断は一つ：176基準を維持し、この固定入力のLR単因子対照を必要とするなら、保存済みsourceと存在を確認したpython3管理入口で別の有限配分に載せる。今回の期限や旧科学を延長・置換しない。GPU生成や主評価の開始条件にしない。

保存会計・Git復元・backup・最終引渡しの機械記録は本issueデータを参照する。
