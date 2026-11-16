# File tạo và chỉnh sửa trong lần cải tiến LR v2

Đường dẫn tương đối từ thư mục FileGuardAI_H07. Danh mục gồm mã nguồn, tài liệu và artifact/bằng chứng. Không liệt kê __pycache__, .pytest_cache hoặc package trong .venv. Hai model baseline/v2 lưu riêng; model triển khai và CSV gốc không thay đổi. Các thư mục tải nguồn thất bại chỉ là thư mục trống, không chứa dữ liệu giả lập.

| Trạng thái | File | SHA-256 |
|---|---|---|
| Sửa | [app/ml_features.py](../app/ml_features.py) | 49e1069017f87d7bd21a4562655a0783b447523e3847cbbef579bf731de9818b |
| Sửa | [app/templates/ai_evaluation.html](../app/templates/ai_evaluation.html) | 0ed3f4dc3bcf3bd7f9738aa7436665d6b34622511aff366f30eaf4c8054518c7 |
| Sửa | [tools/verify_evaluation_http.py](../tools/verify_evaluation_http.py) | 5b678acedb99aa94889f2c256046346b140303d707948cdd4228aa088ad49159 |
| Sửa | [README.md](../README.md) | 30f1ee921670ee42dbea11cc839ca91d00456ad1eb1274357cbd462667996417 |
| Sửa | [docs/evaluations/latest.json](../docs/evaluations/latest.json) | 5408d1d51c3d133f5e9e33082c667a0dec03e7848b05e83e3196a91107f1e441 |
| Tạo | [ml/improve.py](../ml/improve.py) | dac63b4550f69b04ec3f1bdb5831cc0cc04f839b950dd59699803cc864ae7479 |
| Tạo | [ml/external_corpus.py](../ml/external_corpus.py) | 29efc9dba0c8900689feb84dd5a236c38b1f18ef4741573fa8fdfa6b2850f480 |
| Tạo | [tests/test_improvement.py](../tests/test_improvement.py) | 0a9a8c906d70ff098db0d580481a7f4646334162326c7c5ddb4a8cbb5df8461a |
| Tạo | [docs/CAI_TIEN_LR_V2.md](../docs/CAI_TIEN_LR_V2.md) | c14629fe809f1897992bf7aa9e3ecd979872106c3e234da03456db7416b9cc7e |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/.matplotlib/fontlist-v3.11.0.json](../docs/evaluations/20261116T154448Z_7a27a7/.matplotlib/fontlist-v3.11.0.json) | 703a87c72f70cfde75a6c0dfa209518ef8702d72a5b33b04b64a950e3166221b |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/baseline_model.joblib](../docs/evaluations/20261116T154448Z_7a27a7/baseline_model.joblib) | 4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/confusion_matrix.png](../docs/evaluations/20261116T154448Z_7a27a7/confusion_matrix.png) | 0ed5bf1e0ec0b6cbee8275484e561981e28263a4b391c58f084747b6d598e1b0 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/development_split.csv](../docs/evaluations/20261116T154448Z_7a27a7/development_split.csv) | 287ed005863c7b093348ac7a62469428c3f522972c6c613a9e5de58974d3a536 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/environment.txt](../docs/evaluations/20261116T154448Z_7a27a7/environment.txt) | 274f7248c8b8a9be1e116a55a42d16575f2e96291f1b87e132a9afde15be8e13 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/external_analysis.json](../docs/evaluations/20261116T154448Z_7a27a7/external_analysis.json) | f3a84b32036a15e7f738958d4b728bf1a4e35e7b155065b960a78a7b37f521ef |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/external_manifest.json](../docs/evaluations/20261116T154448Z_7a27a7/external_manifest.json) | 5354aa9e951e24e92c12242c8cc57f69881beb673e85ce7f8ae6d2b1a94a3b76 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/external_predictions.csv](../docs/evaluations/20261116T154448Z_7a27a7/external_predictions.csv) | 80e5bf3ffa3ce7cd0058c316065e2da26d8b79f5b056c705eed279eb0fc44175 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/fn_analysis.json](../docs/evaluations/20261116T154448Z_7a27a7/fn_analysis.json) | 37e33ab8485372288ee9d39096b9bb132cf755136fbe6d29c29a12f98c82fe79 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/holdout_predictions.csv](../docs/evaluations/20261116T154448Z_7a27a7/holdout_predictions.csv) | e43722fe0c2985cc072371b71541513856cbc63ca146e5951d3910fe7e8993a0 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/improved_model.joblib](../docs/evaluations/20261116T154448Z_7a27a7/improved_model.joblib) | 07e73c85cdbbd4a8acbc785565514a8330e3252483602c191c34208e04f8e368 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/latency.png](../docs/evaluations/20261116T154448Z_7a27a7/latency.png) | 2bc21c044ac14bd1e523b8d5ef06f96db502ba7a7afd42f82c7f776a1c97dd1a |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/manifest.json](../docs/evaluations/20261116T154448Z_7a27a7/manifest.json) | 17a521f4365e50ad544dc5a4279a7b522e2ede675e09af368772dabbe1f4f3e0 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/metrics.png](../docs/evaluations/20261116T154448Z_7a27a7/metrics.png) | 1547b136c9562557a2b13068f7ed42ac563a0a0d08bf157490c5839761001820 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/protocol.json](../docs/evaluations/20261116T154448Z_7a27a7/protocol.json) | cf5c28639463503a2ab3d4ed0e292fc7d4ad3fc058bf7d1113c3541609104ce7 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/REPORT.md](../docs/evaluations/20261116T154448Z_7a27a7/REPORT.md) | 17514a5a9db0dc428c18ba06704f6da744d0e55b3e49f6c6ed1bc1dade5bcd88 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/results.json](../docs/evaluations/20261116T154448Z_7a27a7/results.json) | 5484102f0a279ef3d9ffd5fe0b4830d0e6a908b8e04083309df83155043ccbf3 |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/selection.json](../docs/evaluations/20261116T154448Z_7a27a7/selection.json) | 05b7380f1f33cb939f5a32617c26810ac9d429c14b5fad02484dc96eedc0e43a |
| Tạo artifact | [docs/evaluations/20261116T154448Z_7a27a7/supplement_manifest.json](../docs/evaluations/20261116T154448Z_7a27a7/supplement_manifest.json) | 7774297eb4d219015fcadc7154d138d7a4f66de5be9314d2176799a18c4f04ac |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/external_cases.csv](../data/external/20261116T154731Z_66a7c6/external_cases.csv) | eb0db38471c5450c745e44d65066f515f2272a8594a81d08827b15337d332b6c |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/external_manifest.json](../data/external/20261116T154731Z_66a7c6/external_manifest.json) | 5354aa9e951e24e92c12242c8cc57f69881beb673e85ce7f8ae6d2b1a94a3b76 |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/flask_commit.json](../data/external/20261116T154731Z_66a7c6/flask_commit.json) | 0de097f087fb282ba812d5f46bd8f9866e780ac7c0dcf1fabb956b717f7eb20d |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/Flask_LICENSE.txt](../data/external/20261116T154731Z_66a7c6/Flask_LICENSE.txt) | 489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/flask_tree.json](../data/external/20261116T154731Z_66a7c6/flask_tree.json) | a13a92ac25c22fa186a53f0e695aa02674ad26d67bb157ab02bd7c96749d4d37 |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/LFI-Jhaddix.txt](../data/external/20261116T154731Z_66a7c6/LFI-Jhaddix.txt) | 2fe4a8e45cb25ced4cd21344744c7821acdf050ce07bf3299d7ef3529cacf1a3 |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/README.md](../data/external/20261116T154731Z_66a7c6/README.md) | 7a3beaed6bcbc90afa262a7690a2897981ea5f1985f57fb633b487778ca27ea3 |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/seclists_commit.json](../data/external/20261116T154731Z_66a7c6/seclists_commit.json) | e7c99d0fafb8133dfc04023cfa5381de16333b358b21e20d77067196dbc74cc4 |
| Tạo artifact | [data/external/20261116T154731Z_66a7c6/SecLists_LICENSE.txt](../data/external/20261116T154731Z_66a7c6/SecLists_LICENSE.txt) | 3dbdc93d5f8829de0941744841730a09c106d0732e5ae0e98ca1d77be7ded66c |
| Tạo artifact | [docs/evidence/improvement_20261116/pytest.txt](../docs/evidence/improvement_20261116/pytest.txt) | d0e697bb894bf29e49f4d7699da719f061083bf968fc51d2eb884521a99eeb54 |
| Tạo artifact | [docs/evidence/improvement_20261116/pytest.xml](../docs/evidence/improvement_20261116/pytest.xml) | a52585fd9f388f8f327c4f8493edd057e10073772798bc06b6b1570e640308b0 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/events.sqlite3](../docs/evidence/tcp_20261116T155000Z_ee53b7/events.sqlite3) | f6b85e24fb20d92eca6cafcd37a7be7be675b4dedb97468565d801effec9399d |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/outside_secret.txt](../docs/evidence/tcp_20261116T155000Z_ee53b7/outside_secret.txt) | 53f3b03edaf4d895a258ba4fc1d5a71727dc48b8b9f1ae896dd57e2619f1180f |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/smoke_http.txt](../docs/evidence/tcp_20261116T155000Z_ee53b7/smoke_http.txt) | 840a6711f89d75ee5f4fd56e893e6b1066c90450b3c2550968bd8cbbde7e5a30 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/summary.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/summary.json) | 74775dde4894c150c5f84bf8b41694d266bac108846c35e0466fcad1efa7291b |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC01.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC01.json) | 5c41cdc4c6404bf58970b826a3cacd4b2643c0e38a68f8101e20e45bb5b8fc28 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC02.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC02.json) | b7430a8c3d890c4068ec7a0446afaa8f91d0a8ad1550d7f17a80b0ffaae7695b |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC03.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC03.json) | 261727ec245d8c419b3221b0b40913e3016809c6fb4c71ca0b3013bb5127ef6a |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC04.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC04.json) | 37bf26fb53f3f8228e75834442bb09df845e05b232aca89ebb47e4e5aa55f239 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC05.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC05.json) | 01a162ade332052f48000197e02c54b7db0974b0b6528b2b349623af9c5a97e1 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC06.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC06.json) | fb7dcaaf360d00eefdce649513e2eece7e72b3c9687a104f75df45a0779c5344 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC07.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC07.json) | c646b98dd2c0438f735eacc1d9af869a1f44493457bb141834d06cbcfe05d678 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC08.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC08.json) | 418dd6c989049f9de247946d8834f1d44868ccc9cdf40eb78e09a18f7649af63 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC09.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC09.json) | abf164c402f7e359f7b102dad1b2d28a6781a1537354708a326a2fbab1e27e6a |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC10.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC10.json) | 965effa66b55555e05e9794a17b6f23f38fc8048baaf22b799d2be98b134633c |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC11.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC11.json) | 1cb858966ef6a1712b54680045620005bea298540b049251465d4ffeb63ec596 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC12.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC12.json) | 3b32887ed6daafa26bddeb6fa9e4fa8403109f1e52ba9e337186b51e738ef4c6 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC13.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC13.json) | b9b7afed78d474113a55a0178696f51dc3ab051d11811ffdd6cec47a897fbc8b |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC14.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC14.json) | 6b2bc1191299a06e8e2b2c6c718b0f49b1d69820e65910ca848fc5cc5c694486 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC15.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC15.json) | aec34c281e9e9d69149c89f231d193552b62b63cc8ad24dbbbdcd9316c115b67 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC16.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC16.json) | c91c7d508d3f32916605ac28ad676e5d93f33df65792682922064e32f2ce9fbd |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC17.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC17.json) | 806f78db3633c5b33ae4564e5a93b301d7cde39c7d19b217dcb9ce44191afdae |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC18.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC18.json) | 0e515b07da1f427124384d9ac265c2635c99d7b8365c5d0089c07b141c1aa9eb |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC19.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC19.json) | 5c0da7152b5d1bc5f95a449f6ba5eb270e813efeb36408983dfae5d2ed78c9bc |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC20.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC20.json) | a86d32b824ce5fe7519c90af713bf911a158d290d6e69890684a82f3376003f6 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC21.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC21.json) | 7d0a93ec475462953ee18886c64ac5661a6e3625dcacd00e893020bd4c449a3d |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC22.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC22.json) | e0599d75a16767346388ae7cee022d1aaa0ece71da991bb7988c763c503b0c7c |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC23.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC23.json) | c543004490394f9dad0bfe3259680bd56ca77275c32e8530801f0049a9f85592 |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/TC24.json](../docs/evidence/tcp_20261116T155000Z_ee53b7/TC24.json) | ca7aed3e98fffd718256705109c7eab1b355fe3aa51805c3129861e80f627b5c |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/test_cases.csv](../docs/evidence/tcp_20261116T155000Z_ee53b7/test_cases.csv) | 56c359c4c186595c20af0a2b5fa68903638e792f0679d92fc0806502f7e3f67d |
| Tạo artifact | [docs/evidence/tcp_20261116T155000Z_ee53b7/test_cases.md](../docs/evidence/tcp_20261116T155000Z_ee53b7/test_cases.md) | fb2b94b93658907e30ed089df389575c0ad5bc867bee727f4830e15140935c06 |
| Tạo artifact | [docs/evaluations/dashboard_http_20261116T154448Z_7a27a7.json](../docs/evaluations/dashboard_http_20261116T154448Z_7a27a7.json) | 02cb2c1294b8e21970e16a6b5a963399f174b0abb454b45307ac0d02fde85584 |
| Tạo artifact | [docs/evaluations/http_3245b6dbb578/events.sqlite3](../docs/evaluations/http_3245b6dbb578/events.sqlite3) | 9ec8ec87a7e6ce82911733385b4a3e543ceca2d399494b52f6fec7e3855fbb89 |

Tạo thêm chính file danh mục này: docs/LR_V2_FILES.md (không tự hash).
