# VXGI導入前のテーブル空間と木材描画

日付: 2026-09-30。Beads: `quoridor-29v`。
設計正本: [§10.2](../design/quoridor-3d-webapp-design-rust-wasm-v1.md)。
作業場所: 主チェックアウト `/workspaces/quoridor`。ユーザー希望: 暖かい照明の落ち着いた室内。

初回のテーブル・材質強化、照明比較、IBL単独＋GTAO導入、その後の接地感修正を時系列で記録する。
現在の採用照明とAOは末尾の「駒の接触位置とHDRI由来の直接光」を参照。

## 実装

- 実写HDRI「Comfy Café」を背景と材質のIBLに使用。背景と反射の回転を一致させる。
- 共通PMREM render targetを背景とIBLへ使い、背景用に同じHDRIをもう一度変換しない。
- 暖色SpotLightを室内灯の方角へ配置。影はWebGPUで2048²、WebGL 2で1024²。
- AgX、露出0.9。HDRI読込成功時にfallback AmbientLightを無効化する。
- 厚み、面取り、脚を持つ有限サイズの木製テーブル。盤底と天板の高さを一致させる。
- 単色の市松模様から、同系色の濃い木製マスと溝へ変更。枠・マス・壁の角を面取りする。
- 盤・壁・駒・テーブルの金属度は0。塗膜はroughnessとclearcoatで表現。
- 木製の旋盤加工に近い駒。先手の丸、後手の六角、従来の色による識別を保持。
- 生成した木目base colorを使用。微細凹凸と粗さの変動は独立した周期的な微細繊維で調整。
- 箱のUVは面の実寸と位置に基づき、マスごとに同じ木目を繰り返したり、寸法によって木目を引き伸ばしたりするのを抑える。
- アセットはローカル同梱。URLにVite base pathを反映。取得は中断可能で、10秒の期限を設ける。
- アセット失敗時にも単色PBRとfallback照明で対局を続ける。
- 新規対局/やり直しはアセットとcanvasを再利用。renderer破棄時はtexture、PMREM target、bitmap、shadow、geometry、materialを解放。
- 基本描画は変更時に描画する。OrbitControlsとアニメーションの更新用RAFは継続し、同一フレームを静止中に送信しない。

### 実物の参照と近似

[Gigamic標準版の公式商品ページ](https://www.gigamic.com/jeux-a-deux/75-quoridor-3421273322915.html)で、
盤・壁・駒が木製と確認した。
[公式商品写真](https://www.gigamic.com/766-large_default/quoridor.jpg)から、
濃い色の盤、明るい壁、着色した駒、溝、丸みのある外周を参照した。
公式写真は実行時のアセットへ含めない。

樹種・塗膜の組成・粗さの実測値は確認できていない。
生成木目は細かな広葉樹の外観を意図したもので、実物の樹種をブナと断定しない。
生成画像の継ぎ目の完全一致も計測で保証したものではない。縮尺と見える繰り返しを画面で確認する。
既存HUDと対応するプレイヤー色/形状を優先したため、実物の全パーツの完全な形状・色複製ではない。

## 採用アセット

正本は [asset README](../../apps/web/public/assets/tabletop/README.md)。

| ファイル | 出所 | サイズ | SHA256 |
| --- | --- | --- | --- |
| `comfy-cafe-2k.hdr` | Poly Haven / Sergej Majboroda、CC0 | 2048 × 1024、6,260,522 bytes | `00597d2a2174b7803c10bd2d690922e170bb614bce6c98c9c9b688698f1d234d` |
| `beech-albedo.png` | built-in image_gen、2026-09-30生成、内容変更なし | 1254 × 1254、2,452,019 bytes | `cc1ebb9b08e6c95336b841601d9dcb4df9b7e577f4c1f1ac4dfa522f8f1f7f2e` |

HDRI出所: [Comfy Café](https://polyhaven.com/a/comfy_cafe)。
ライセンス: [Poly Haven CC0](https://polyhaven.com/license)。
取得ファイルのMD5は公式APIの値と一致した。
使用する2枚の合計は約8.3 MiB。高解像度の未採用素材や参考写真はGit管理対象へ追加しない。

### 生成プロンプト

built-in `image_gen`を使用。CLI/API fallbackは使用していない。

```text
Use case: photorealistic-natural
Asset type: seamless PBR base-color texture for wooden Quoridor board game pieces in a Three.js application.
Primary request: one square, edge-to-edge, high-resolution albedo photograph of clean fine-grained pale honey-colored hardwood, resembling sanded beech used for wooden board games.
Composition/framing: orthographic top-down macro material scan, grain mostly vertical, uniform scale across entire image. A single continuous wood surface, no frame, no seams, no separate boards.
Materials/textures: subtle elongated fibers and very fine pores, restrained natural variation, light warm beige with no large knots, no damage. The grain must remain natural and visible without being exaggerated.
Lighting: perfectly even diffuse illumination, no baked cast shadows, no gradients, no specular highlights, no ambient occlusion, no vignette. This is ONLY the base color, not a beauty render.
Constraints: seamless tileable on both axes with matching edges, full opaque square image, no text, no logo, no borders, no objects. Do not include the Quoridor board or a room.
```

## 照明と将来のVXGI

[公式VXGINode](https://threejs.org/docs/pages/VXGINode.html)は間接拡散光とAOを扱い、
直接光をボクセルへ注入する。将来この実装で反射光を計算する場合には、環境と整合する直接光/影、
または環境光を注入する別実装が必要になる。現時点のIBL＋GTAOにVXGIは必須ではない。
通常の生成画像を実測HDRI相当の照明データとは扱わない。

使用中のThree.js 0.186.1の `EnvironmentNode`、`PhysicalLightingModel`、
`ContextNode.builtinGIContext` を確認した。
`builtinGIContext` は環境の間接光へAOを適用し、GIの遮蔽を二重に掛けないよう補正する。
統合時はこの経路を使い、環境拡散光、直接光、GIの明るさとAOの重複を比較検証する。
現在のIBL成功をVXGI対応の成功として数えない。

テーブルと脚は現在 `GI_STATIC`から除外する。
Phase 5で盤周辺の天板を固定bounds内のGI対象へ含める方法を検証する。
部屋の実形状、環境の視差、環境光自体をボクセルへ注入する実装は含まない。

## 検証

### 結果

| 確認 | 結果・根拠 |
| --- | --- |
| strict TypeScript / boundary | `npm run typecheck`、`node scripts/check-boundaries.mjs` 成功 |
| production `/` | 46ケース確認。初回42成功、4件は起動待機の競合と初回ソフトウェア描画の5秒制限で失敗。待機修正後、該当4ケースを再実行して4/4成功 |
| production `/quoridor/` | 待機修正後の全46ケースが成功（6.0分） |
| 新規アセット検証 | 両baseで3/3成功。読込・再利用・renderer復旧、404時の対局継続と再取得、取得途中の破棄を確認 |
| 静止時の描画 | アセット描画後、submitted frame数が静止中に増加しないことを確認 |
| 通常production | `npm run build`成功。`scripts/smoke-ordinary-production.mjs` 成功。キーボード操作、テストフック非同梱、ブラウザエラーなし |
| 通常版の画面撮影 | 実UIで駒を移動、壁を設置して撮影。アセット2枚のHTTP 200、ブラウザエラーなし、テストフックなし |
| 差分 | `git diff --check` 成功 |

テストフック付き検証は、通常previewの`dist/`を保持するため
`.artifacts/tabletop/production/{root,subpath}`を出力先、4274を検証portにした。
`APP_BASE`と`VITE_PHASE1_E2E=1`を指定し、`npm run build -w @quoridor/web -- --outDir <path> --emptyOutDir`、
該当出力先を使うVite preview、`E2E_BASE_URL=... npm run test:e2e`を順番に実行した。
通常の再実行はREADMEの`PREVIEW_PORT=4274 npm run verify:production`で両baseを確認できる。
通常版はその後`npm run build`で作り、4173で起動した。

ローカルの描画方式はChromium headless / SwiftShader / WebGL 2。
初回PBR/PMREMの準備が5秒を超えるケースを確認し、Playwrightのexpect待機を10秒へ変更した。
時計制御を含む長いUIケースのみ60秒とした。アニメーションの190msという実装値や、Rust/AIの検証条件は変更していない。
Phase 0の診断テストはrenderer起動とrules game準備を別々に待つよう修正した。
開発Viteがファイル変更を反映しなかった試行は、再起動して`CHOKIDAR_USEPOLLING=true`を指定した。
上記productionの検証ではbuildした静的出力を使用している。

### スクリーンショットとログ

- [通常版デスクトップ 1440 × 900](../../.artifacts/tabletop/final-desktop.png)
- [通常版縦長画面 390 × 844](../../.artifacts/tabletop/final-mobile.png)
- [通常版の撮影・HTTP・エラー結果](../../.artifacts/tabletop/ordinary-capture.log)
- [ルート初回全46ケース](../../.artifacts/tabletop/production-tests.log)
- [ルート待機修正後の4ケース](../../.artifacts/tabletop/root-corrected-tests.log)
- [サブパス全46ケース](../../.artifacts/tabletop/subpath-tests.log)
- [通常build](../../.artifacts/tabletop/ordinary-build.log)
- [通常smoke](../../.artifacts/tabletop/ordinary-smoke.log)

HUDの盤面寸法とスクロールなしを1280 × 720、1440 × 900、1920 × 1080、390 × 844で確認した。
1440 × 900の盤全体は1125.9 × 631.6px、390 × 844では370.0 × 333.7px。
デスクトップ/縦長の通常版画像を目視し、木目、面取り、塗膜の反射、壁と盤の接地影、HUDとの位置関係を確認した。

### 未検証・後続

ホストChromeの実GPU、WebGPU実描画、VXGI/TRAA、実GPUのFPS/VRAMは未検証。
この報告の画像と成功結果はWebGL 2の基本PBR/IBL描画を示す。
環境光の完全な物理復元や、部屋全体の3D geometry/視差を実装したものではない。
初回のshader準備を含む実際の操作感と画質は、起動した通常previewで人間が確認できる。

## IBL単独照明の比較（2026-09-30）

ユーザーの照明・SSAOに関する質問に対し、製品コードを変更せずに同じ`BoardRenderer`と
`BoardScene`を読み込む一時fixtureで比較した。HUDを省いた1280 × 800の同一カメラ、同一材質、
AgX / exposure 0.9、backgroundIntensity 0.55、同じHDRIと木目を使用。
Chromium headless / SwiftShader / WebGL 2でアセットready、ブラウザ例外なしを確認した。

| 条件 | 観察 |
| --- | --- |
| 現在のIBL 0.7 + SpotLight 260 | 盤面右側に明るい部分があり、盤とテーブルの境目・壁の周辺に投影影がある |
| IBL 0.7のみ（SpotLight 0） | 少し暗くなるが盤面・駒・木目は判読可能。局所的な投影影と接地感が弱くなる |
| IBL 1.0のみ（SpotLight 0） | 明るさを確保でき、SpotLightによる局所的な明暗差が減る。接触部分の遮蔽は依然未計算 |

これは照明候補の比較であり、通常previewの設定変更やAOの実装・画質検証はしていない。
IBLだけの場合に必要なのは単純な増光だけでなく、盤とテーブル、駒の底、壁と溝の局所遮蔽。
推奨はIBL中心の照明と小さい半径・弱い強度の画面空間AO。現在のThree/TSL構成では
[GTAONode](https://threejs.org/docs/pages/GTAONode.html)を候補とし、`builtinAOContext`で
材質の間接照明へ適用する。最終画像や背景へ一律に乗算しない。画面外の遮蔽物、
広範囲の投影影、色の反射はこのAOで再現できない。半解像度を出発点としてノイズと負荷を検証する。

[Sceneの設定](https://threejs.org/docs/pages/Scene.html)では背景と環境照明の強度は独立している。
背景が明るく見えることだけでは物体の照度の十分さは判断できない。
将来の[Three VXGINode](https://threejs.org/docs/pages/VXGINode.html)は直接光だけをボクセルへ注入するため、
IBL単独からそのまま反射光を計算する構成にはならない。導入時は環境と整合する直接光を追加するか、
環境光の注入を別途実装する必要がある。VXGIに含まれるAOと画面空間AOの強い二重適用も避ける。

- [比較画像（左: 現在、中央: IBL 0.7、右: IBL 1.0）](../../.artifacts/tabletop/lighting-comparison.png)
- [撮影条件と例外結果](../../.artifacts/tabletop/lighting-comparison.json)
- 再現: Vite devを5274で起動し、`PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright node .artifacts/tabletop/compare-lighting.mjs`。
  fixtureと撮影スクリプトは`.artifacts/tabletop/lighting-comparison.{html,ts}`および`compare-lighting.mjs`に保存。

## IBL単独＋GTAO導入（2026-09-30）

Beads: `quoridor-6r2`。ユーザーの「SpotLightが無い方が自然」「GTAOは組み込んで」を受け、
通常照明をIBL単独へ変更した。環境強度1.0、背景強度0.55、AgX / exposure 0.9。
HDRIの取得失敗時だけ既存のAmbientLightを使う。VXGIは今回実装していない。

### 描画構成と所有

- `ambient-occlusion.ts`にGTAOの描画構成をまとめた。深度・view-space法線を全解像度で取得し、
  GTAOとbilateral blurを半解像度で計算、材質の環境照明へ`builtinAOContext`で適用する。
- 初期設定は半径0.45、thickness 0.75、16 samples、AOの混合強度0.65。
  1マスの間隔は1 world unit。最も遮蔽された部分でもAO係数0.35を残す。
- [BilateralBlurNode](https://threejs.org/docs/pages/BilateralBlurNode.html)はsigma 1、sigmaColor 0.1。
  時間方向の蓄積を使わず、小さい空間フィルターでノイズを抑える。
  このフィルターの境界判定はAO値の差に基づき、深度・法線を使うdenoiseではない。
- AO計算用layerをGI用layerから分離し、盤・確定壁・駒・テーブルを含める。
  合法手マーカーと操作プレビューはAOを生成しない。背景とHUDへAOを一律乗算しない。
- pre-passは通常cameraを複製して各描画時に同期する。異なるlayerのpassが同じcameraの
  cached render listを更新すると、beautyの描画途中でlistが変わって停止する問題を回避した。
- AO依存passはbeautyより前に評価する。評価を起動するquadの出力先は1 × 1の非表示target。
  geometry描画中にAO依存passが入れ子になると、共有screen-size uniformが書き換わり、
  AO画像ができても材質へ正しく反映されないことを比較で確認した。この先行評価で解消した。
- `renderer.setAnimationLoop`を使い、Threeのframe単位のnode更新と描画callbackを合わせる。
  対局・カメラ・プレビュー・材質などに変更があるときだけpipelineを実行する。
- 所有するpre/beauty/GTAO/blur target、1 × 1 target、pipeline/blur材質・noise textureを
  renderer破棄と復旧時に解放する。通常の新規対局では再作成しない。
- DenoiseNodeの候補構成ではTSL/shaderエラー、depthAwareBlurをRTT経由で使う候補構成では
  shader生成の再帰エラーが発生した。今回動作確認できたBilateralBlurNodeを採用した。
  Three本体やnode_modulesは変更していない。これを全環境でのaddon不具合と断定しない。

### 視覚効果の確認

同一カメラ・材質・IBL・露出で、AO混合強度だけを0と0.65に切り替えて撮影した。
1440 × 900、Chromium headless / SwiftShader / WebGL 2。
AO有効時の出力は720 × 450。アセットはready、ブラウザ例外とconsole errorは0。

| 比較領域 | 変化したpixel数 | RGB各channelの平均絶対差（0〜255） |
| --- | --- | --- |
| 背景（y 0〜139） | 0 | 0 |
| 駒の接触部周辺 | 3,364 | 2.638 |
| 盤とテーブルの接触部周辺 | 29,230 | 8.055 |
| 壁の接触部周辺 | 7,400 | 5.442 |

この差分は画質の定量評価ではなく、背景を変えずに接触部の材質照明が変わったことを示す。
目視でも盤の底、駒の足元、壁と溝に局所的な暗さが加わることを確認した。
広範囲の投影影、画面外の遮蔽物、色の反射はGTAOでは計算しない。
実GPUの負荷・WebGPUの画質は今回未検証。

- [AOなし](../../.artifacts/tabletop/gtao-off.png)
- [AOあり](../../.artifacts/tabletop/gtao-on.png)
- [AOの計算結果](../../.artifacts/tabletop/gtao-mask.png)
- [条件と画面差分](../../.artifacts/tabletop/gtao-comparison.json)
- 再現: Vite devを5274で起動し、`PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright node .artifacts/tabletop/capture-gtao.mjs`。
  一時fixtureは`.artifacts/tabletop/gtao-comparison.{html,ts}`。比較用の強度変更やshader採取は製品コードに同梱しない。

### 検証時に修正した待機

時間制御を伴う対局操作のE2Eは、`pauseAt`の10秒送りを100ms送りへ変更した。
アニメーション中断・undo・restart・破棄の確認に不要な数百フレームのソフトウェア描画を避けるため。
同ケースはGTAOを含む多くのカメラ/対局フレームを描くため、全体上限を90秒とした。
アプリの190msアニメーションと、対局の状態・入力に対する期待値は維持した。

### 最終ローカル検証

先行評価を含む最終構成で以下を確認した。途中の検証は環境の再起動で中断されたため、
最終構成の関連20ケースを通常URLとサブパスで改めて実行した。全E2Eの再実行ではない。

| 確認 | 結果 |
| --- | --- |
| `npm run build`（release WASM、型検査、通常production） | 成功。Viteのchunkサイズ警告あり |
| 関連E2E・通常URL | 20/20成功 |
| 同じ関連E2E・`/quoridor/`配信 | 20/20成功 |
| AO・アセット・renderer | 半解像度resize、対局リセット時の再利用、renderer復旧、取得失敗時のfallback、取得中の破棄、静止時の描画停止を確認 |
| 操作・HUD・復帰 | pointer/keyboard/touch、camera反転とresize、アニメーション中断、AI結果取消、対局モード切替、保存復帰・削除を確認 |
| 通常production smoke | keyboard移動成功、テスト用globalなし、page errorなし |
| 通常production撮影 | HDRI/木目はHTTP 200、移動と壁配置を実UIで実行、例外・console errorなし |

- [最終desktop画面（1440 × 900）](../../.artifacts/tabletop/gtao-final-desktop.png)
- [最終mobile画面（390 × 844）](../../.artifacts/tabletop/gtao-final-mobile.png)
- [通常buildログ](../../.artifacts/tabletop/gtao-ordinary-build.log)
- [両baseの関連E2Eログ](../../.artifacts/tabletop/gtao-accepted-tests.log)
- [通常production smokeログ](../../.artifacts/tabletop/gtao-ordinary-smoke.log)
- [通常production撮影ログ](../../.artifacts/tabletop/gtao-ordinary-capture.log)

画像は通常productionを`npm run preview`で4173へ配信して撮影した。
ホストではポート転送後の`http://localhost:4173/`から確認できる。
検証環境はChromium headless / SwiftShader / WebGL 2。実GPU・WebGPUの画質と負荷は未検証。
変更は未コミット。

## 駒の接触位置とHDRI由来の直接光（2026-09-30）

Beads: `quoridor-c6r`。ユーザーはGTAO導入後も駒と盤の境界が暗くならず、接地感がないと評価した。
その後「IBLを弱めてDirectionalLightの直接光と影を加える」「向きをIBL画像に合わせて計算する」と指定。

### 原因の切り分け

- 駒の足の高さは0.10、中心が0.21なので底面は0.16。一方マス上面は0.14で、
  駒が0.02 world unit浮いていた。マス上面と駒底面を共通定数から計算するよう修正した。
- AO maskを拡大すると駒周囲に遮蔽があった。材質をAO値そのもので表示した結果もmaskと一致し、
  UVの位置ずれやAOの完全な未適用ではなかった。
- 全解像度、半径/強度の増加も比較したが、足元の細い遮蔽は暗い木材上で十分に目立たなかった。
  強い設定では溝や駒自身も暗くなる。前節のpixel差分は「材質への適用」の確認であり、
  ユーザーが十分と感じる接地感の根拠にはならなかった。
- 最終採用ではGTAOを半解像度・半径0.45・16 samples・混合強度0.65に維持し、
  直接光の投影影を追加した。接触AOの別方式や影用の平面は追加していない。

### 主光源の方向

`environment-light.ts`でdecoded HDR画像を読み、linear RGBの輝度を計算する。
equirectangularの上半球を調べ、各画素の重みは緯度のcosに比例する球面面積とする。
処理量を制限するため、横幅512程度の間隔で画素中心をサンプリングする。

球面面積で重み付けした95 percentileを超える輝度を主光源候補とし、
方位32 × 仰角8の区画で余剰輝度×面積の合計が最大の区画を選ぶ。
その重心から30度以内を再積分し、方向と色を求める。
画像端のseamをまたぐ光源も方向vectorでまとめるため、別々の光として平均しない。
反対向きの複数光源を全て平均して、実在しない頭上方向を作ることも避ける。

HDRLoaderのflipYとThreeの`equirectUV`に合わせて画素を方向へ変換し、
`scene.environmentRotation`を適用する。ライトのpositionはこの方向×20、targetは盤の中心。
光線が進む方向はその逆方向。カメラ反転・resize・対局操作では変えない。

今回のComfy CaféとY軸90度回転からの結果:

| 値 | 計算結果 |
| --- | --- |
| 盤中心から光源へ向かうworld方向 | `(0.538714, 0.544123, -0.643208)` |
| 選択領域の余剰輝度エネルギー / 上半球の候補全体 | 約52.2% |
| 正規化したlinear RGBの光色 | `(0.951077, 1.0, 0.998493)` |

計算方向へカメラを向け、通常のPMREM背景で天井の照明が画面中央へ来ることを目視確認した。
今回の主光源は窓ではなく、この天井照明と推定される。

- [計算方向を向いた背景](../../.artifacts/tabletop/pawn-light-source.png)
- [方向・色・shadow map・例外の記録](../../.artifacts/tabletop/pawn-lighting.json)
- Threeの参照: [equirectUV](https://github.com/mrdoob/three.js/blob/r186/src/nodes/utils/EquirectUV.js)、
  [環境回転](https://github.com/mrdoob/three.js/blob/r186/src/nodes/accessors/MaterialProperties.js)、
  [DirectionalLight](https://threejs.org/docs/pages/DirectionalLight.html)。

### 採用した構成と制約

IBL強度0.65、DirectionalLight強度4、背景強度0.55、AgX / exposure 0.9。
PCF shadow map 2048 × 2048、radius 5、orthographic範囲±8、bias -0.0001、normalBias 0.012。
盤・壁・駒・テーブルをshadowの対象にし、AO/beauty用cameraのlayer変更に影響されない専用layerを指定。
renderer破棄時にshadow資源も解放する。HDRIから方向を得られない場合はIBL強度1.0・直接光0、
HDRI取得失敗時は既存のAmbientLightで対局を続ける。

これは室内の主光源を平行光で近似した構成。面光源の距離減衰や、距離に応じた半影は再現しない。
HDRIから主光源を除去していないため、厳密な光エネルギー分解ではない。直接光の強さは比較で調整した。
VXGIは未導入。実GPU・WebGPUの画質と負荷も未検証。

### 検証と完成画面

| 確認 | 結果 |
| --- | --- |
| `npm run build` | release WASM・型検査・通常production成功。既存のchunkサイズ警告あり |
| `npm run test:render` | 6/6成功: 上下半球、環境回転、seam、反対向き光源、球面面積、half float、均一/無効画像 |
| 関連E2E・通常URLと`/quoridor/` | 各8/8成功。復旧後の同一方向・shadow map、fallback、破棄、対局/入力、camera反転/resizeを確認 |
| 通常production smoke | keyboard移動成功、テスト用globalなし、page errorなし |
| 通常production撮影 | 実UIで移動・壁配置、HDRI/木目HTTP 200、例外・console errorなし |

方向のテストは`tests/render/environment-light.test.mjs`に保存し、`npm run check`にも組み込んだ。
この修正で全てのRust検査や全E2Eを再実行したものではない。

- [完成desktop画面](../../.artifacts/tabletop/pawn-shadow-final-desktop.png)
- [駒周囲の拡大](../../.artifacts/tabletop/pawn-shadow-final-contact.png)
- [完成mobile画面](../../.artifacts/tabletop/pawn-shadow-final-mobile.png)
- [同一カメラでの以前のIBL単独](../../.artifacts/tabletop/pawn-light-before.png)
- [同一カメラでの直接光追加](../../.artifacts/tabletop/pawn-light-new.png)
- [buildログ](../../.artifacts/tabletop/pawn-ordinary-build.log)
- [方向計算のテスト](../../.artifacts/tabletop/environment-light-tests.log)
- [両baseの関連E2E](../../.artifacts/tabletop/pawn-shadow-e2e.log)
- [通常production smoke](../../.artifacts/tabletop/pawn-ordinary-smoke.log)
- [通常production撮影](../../.artifacts/tabletop/pawn-ordinary-capture.log)

比較用fixtureは`.artifacts/tabletop/pawn-lighting.{html,ts}`、撮影は`capture-pawn-lighting.mjs`。
Vite dev 5274へ接続し、以前のIBL強度と駒高さ、直接光なし、採用設定、光源方向の背景を順に撮影する。
通常版は4173で配信。ホストはポート転送後の`http://localhost:4173/`から確認できる。

### ユーザー確認とGit保存

2026-09-30、ユーザーがホストで画面を確認し「良い感じ」と評価、プッシュを指示した。
実装・選択したruntimeアセット・テストは`db23c9f`に保存。
設計・検証結果は続くドキュメントのコミットに保存する。
スクリーンショット、比較fixture、ログは既存方針に従いローカルの`.artifacts/tabletop/`に保持する。
