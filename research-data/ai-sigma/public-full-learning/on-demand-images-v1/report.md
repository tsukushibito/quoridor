# 学習画像を必要時だけ生成する

ユーザー方針に従い、通常trainerの初期・観測・epoch・終了persistからPNG/SVGの自動描画を撤去した。全数値曲線/CSV、INITIAL/BEST/LAST、選定・減衰・早期停止・教師・乱数・数学は維持する。画像は保存記録を指定する明示CLIで一つの形式だけ生成する。PNGの外部Python自動起動を撤去し、描画環境のPythonを呼出側が明示する。SVGはMatplotlib不要、PNGは明示要求時のみimportする。画像はfreeze必須資産に含まれない。

mainのJSON array記録を維持した6pathの最小patchのみ適用し、実WTのJSONL.gz append/fulltrainer/計測hookを丸ごと取り込まない。bindingの全before/after SHA、停止source2archive、producer evidence各memberのbytesを照合した。mainのtrain ASTは描画2callを除き完全一致、FROZEN_ARTIFACTS ASTも一致した。

main実体でTorch importを拒否した関連5 NN0テストがPASS。初期/epoch/終了相当の数値persist、精度と全点、描画起動なし、選択したPNG/SVG入口とscope/format拒否を確認した。実fit/model/CUDA/newE/Sigmaは実行しない。producerによるWT/main staging各5 NN0 PASSと明示toy PNG/SVGのdirectwait/目視は別証拠であり混算しない。元mock fixtureの失敗とgit apply checkのnew-file header拒否は保全し、patch dry-run/適用後の6SHA一致を確認した。Ruff整形/checkとPrettier対象docs整形/checkを実施した。

元323の本学習はpausedのまま。新しい優先度1/2供給改善323.4は別許可・別対象で、転送/展開/worker数学の採用は本結果から認定しない。過去画像・raw・ソース・モデル・失敗・費・UNKNOWNは保全する。
