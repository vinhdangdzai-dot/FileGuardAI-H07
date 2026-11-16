# File tạo/sửa trong lần rà soát tổng hợp

Phạm vi: mã nguồn, tài liệu và bằng chứng trong dự án; loại trừ __pycache__/.pytest_cache, không có thay đổi package trong .venv. File cũ được giữ nguyên trừ những file mã nguồn/README liệt kê là Sửa. Dữ liệu, model, SQLite thật và các artifact cũ trong snapshot được kiểm chứng không đổi.

| Trạng thái | File | SHA-256 |
|---|---|---|
| Sửa | [app/database.py](../app/database.py) | 3d27dd3982ff60083cd5dd714c42da334d324d17c671a6b62175112341effeac |
| Sửa | [app/security.py](../app/security.py) | fcb281a68e73dd44248d116d63db56a110ea874d1e9372abef37b6681ed5e552 |
| Sửa | [app/web.py](../app/web.py) | 64b1954db2cbad9e78db154448ea812f35d3a15e79a388b3d0d5d6830acebc46 |
| Sửa | [ml/generate_dataset.py](../ml/generate_dataset.py) | a96e0bf4df95b8acdd58833cc1cf700df5506feda5eda03773f8fdeff2856f30 |
| Sửa | [ml/train_model.py](../ml/train_model.py) | f3a80482920e8bee98039b60095c72cca8a884ce0cfd583a8c3600913cd84702 |
| Sửa | [tools/verify_evaluation_http.py](../tools/verify_evaluation_http.py) | ae902238b52437e6b06576c413559f443c92c6d388af5af30b7033af7d0d9178 |
| Sửa | [tools/verify_tcp.py](../tools/verify_tcp.py) | 1139d4abb481763055f38dec3a4b43c902ae3d7af6f7fba59a99e6d27cd123d7 |
| Sửa | [tests/test_improvement.py](../tests/test_improvement.py) | 95b45cf386a2475103ffc0a1afa19f3b75bee93bde21e737443047c7f1dd3c65 |
| Sửa | [README.md](../README.md) | f5dd954e9c785db5c20e1421a295bf1edb8b440e17b2179ddc30f4f2e9737c13 |
| Tạo | [app/evaluation_results.py](../app/evaluation_results.py) | 13418a96bb02a05d0f23962c055733984d34391cbb68c930166ea3d11f696b0d |
| Tạo | [tools/audit_project.py](../tools/audit_project.py) | bf830e644954aa0d6f1de40fe93f4be839dd03ba1b254fb67e778340394722fa |
| Tạo | [tests/test_review.py](../tests/test_review.py) | 1e4a0d7c4af873dbf75ba8db3b6726da334722219d567d40cf135d8a9e4199d5 |
| Tạo | [docs/BAO_CAO_TONG_HOP.md](../docs/BAO_CAO_TONG_HOP.md) | 108a685f24137540d2a5790159eccaac5a54f3b0a61e090107b026a7b8402210 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/audit.json](../docs/reviews/review_20261116T163259Z_049c87/audit.json) | f6bd26ddb75eeeaf1ca378442ffeff6c16f445539afaeeaf09b90c841d60c3af |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/before.json](../docs/reviews/review_20261116T163259Z_049c87/before.json) | f1af32767a2a6049d9800805cd93d22032a6bfba07790790704c39cd91c47bcd |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/canonical_overlap.csv](../docs/reviews/review_20261116T163259Z_049c87/canonical_overlap.csv) | eebffc334f2f8d989b92b66c4753f2e960a57bc163dbb7f772a73329cf3b6e92 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/dependencies.txt](../docs/reviews/review_20261116T163259Z_049c87/dependencies.txt) | 62a7bed1b63f3145e4a1f662db6de145fcc24a75271861405b20d49df601b4ee |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/final_state.json](../docs/reviews/review_20261116T163259Z_049c87/final_state.json) | 9ffc12ac16752e9acfa6bbeb93b842b1726b617d06085580d689328eb907ed96 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/methodology.json](../docs/reviews/review_20261116T163259Z_049c87/methodology.json) | 3788eac2e5914502d07fc1ec8583112763b441a61524cdfe63a4e9b0d42a2ccb |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/pytest.txt](../docs/reviews/review_20261116T163259Z_049c87/pytest.txt) | 992e6b1a299858659f185e06a8db846d61e7847d3ce15b5873a4d619c70f855b |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/pytest.xml](../docs/reviews/review_20261116T163259Z_049c87/pytest.xml) | c730b2d91d8cf96711bbc2283d36656c494132e246ac45de6943cbda3fcd4b86 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/pytest_final.txt](../docs/reviews/review_20261116T163259Z_049c87/pytest_final.txt) | 7577180cefead005306223b6a60aea4cfd89f11a1ad567c9ddb47e6aa9b83b74 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/pytest_final.xml](../docs/reviews/review_20261116T163259Z_049c87/pytest_final.xml) | c17de1d891b3db83fa2e851fe6b3bcd306e3e504aaeb131a9d931b9159fa12c4 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/sensitivity_predictions.csv](../docs/reviews/review_20261116T163259Z_049c87/sensitivity_predictions.csv) | 703470f3a590c29d15aad7ddacb4da56ad44acc76fc4a1943acbed3762598c10 |
| Tạo bằng chứng | [docs/reviews/review_20261116T163259Z_049c87/verification.json](../docs/reviews/review_20261116T163259Z_049c87/verification.json) | 18090cf562572b86405ac2e6d225e7b8416fb89c8f0f8e6d228d8efa2e758de3 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/events.sqlite3](../docs/evidence/tcp_20261116T163844Z_cc01e8/events.sqlite3) | d665e490626a9d38ded496822bd68ad70f5e2d67484885b45b92bf905c705524 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/outside_secret.txt](../docs/evidence/tcp_20261116T163844Z_cc01e8/outside_secret.txt) | 2138adfc8e4dcbbf86c3e8db915796c0d675c8b2c81b5bcee57db67bb1633189 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/smoke_http.txt](../docs/evidence/tcp_20261116T163844Z_cc01e8/smoke_http.txt) | 840a6711f89d75ee5f4fd56e893e6b1066c90450b3c2550968bd8cbbde7e5a30 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/summary.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/summary.json) | 82be95c8f3a37364c218c60de3d3e0efb28a0fab739f519490e68f8342f06b08 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC01.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC01.json) | f72f5f9c59663d537df23eac7554176eba81c108fb772733817b70e553d090a6 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC02.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC02.json) | 2b4af8c6897addcb4bfee18db064021edb360373852319d5536ca7c5eddf0b53 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC03.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC03.json) | ddb0e6e17133ff2258967bd87c1a53e548786a2deeab759dcf19b66434fb7a02 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC04.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC04.json) | 4e877f08261764361de8a1602b94aa9e64c301cf6a441b71b5552d1ece39e2f0 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC05.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC05.json) | b968769a960d87ddaf4b4da12089dac6debb9d11939fe380006147e1fa95b994 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC06.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC06.json) | 2553123e1a076f12bbf3e020bd254ea0a7f9740ce185583f81479009e3ba34cd |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC07.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC07.json) | ce2d1c39e89cfb49983593ff5e9f6cad2717eaa0e834ddf4c549112439af39c3 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC08.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC08.json) | 1c2d7d84e2919077360262a6a8e0d7afeb0ca3369f5cf8b478aee6b3a4cbe986 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC09.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC09.json) | 8f8468fa827b50f7cb4b3e6bb3b1acfc0f2166df9bc5f73c3ef3f11813a6481b |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC10.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC10.json) | eb410e0f11e19d025058d5af5d1dcd00d35bb6fca6e574b987724f9d7005df38 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC11.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC11.json) | d499797bb53613513cbbbcc7a4017c2fb50c8cb8bc565e16bbd4791a3e3d7eb6 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC12.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC12.json) | 2c1e16b9f07c195eae170f35c9ecab95f125aef00f254e6e3bc34e22e315728e |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC13.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC13.json) | c21e1ba766216d2c47bbb0d81fe1100f02b7727786c64999e9b53f2fd5f2a4f3 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC14.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC14.json) | 4a7da2abd7acba2f3b897722851c9f2c4745cb5b1967c00d90fe213a4c7320fb |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC15.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC15.json) | 7193120aff06406988a08586d4676a1f655c115da6fd5762679a1e80fb0c067f |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC16.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC16.json) | 2123cec0dfaca2810a7d67fc0310acc2066151b871fc5a23e7ecfec1a157f3d5 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC17.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC17.json) | 4975ac7dab3a50cc81c480cb258c1733eb110971aafa66fdff8a53a7d7de0594 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC18.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC18.json) | 6ea33c5035b74a52c78d6c71ba56ef3a3ded7ab9d75950d1f6b391f148a4935a |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC19.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC19.json) | d3d10b227f8ac42b09dc275a63226170f9c43bab8e5463ab828a57cec7fc2aaf |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC20.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC20.json) | 3f0b667d0e0c77d1e050d77eb3814e7356149c89a26048dbc2977cae44ad01f3 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC21.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC21.json) | 836788182011bdc3552138b70c2e36eb02554da1ae2a024bf1ef3c445243c491 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC22.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC22.json) | ea4191a131c167a5cb017de3224ea770e9579af14f9034588261bcd568e08917 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC23.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC23.json) | 09f3c7830a6c0a706041a0b0cee9c4b988af6825deb218b37880cf3d74f12fcf |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC24.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC24.json) | 57e8bbd080167b04778a5017d8b7249afc00c8ba8fa5bb712f5632822e227152 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC25.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC25.json) | 192caea1f0fe995a2152cc39c2cc8ad2cca89c322a37378821f41602ac424a82 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC26.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC26.json) | 5f554381a39626c89250f76e35621bd8266fb69d7ef2e1206c51da5827c3de3e |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC27.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC27.json) | 1e41806e6eacf9ac47a3453860e43ccab6ef6c5161ce79745ad7ad54f0279df2 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC28.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC28.json) | 96386cef812040f321cefa9c72e28f2f57ea776eacaeed0d8fdd2bfdb23ee2a7 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC29.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC29.json) | eb849bfba0ad27534c9b0c9e1e1241ebf724561a1e05f9f60e9fd2d920b238eb |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC30.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC30.json) | 2a349192e1a8c15aaf8dedad162d0534a1fbe5892b91972ffcd3a6d4a815c922 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC31.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC31.json) | df7fec5442961e4bfceeaab5b54f166f58f495ec25f6bc14017d44127b431210 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC32.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC32.json) | f81546cb64df0fc31f753a101bf68451f36b4abf9ec734698a300d58dc44f133 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC33.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC33.json) | 0fa8f1ac259d52a280105bc08834a0fca19fbe3329f3f6114e2a095986c6f47e |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC34.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC34.json) | 65c3174f965d35cb3e926e5bb8dd3dc1ab950727a1da65ddbb6356b91c89feb9 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC35.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC35.json) | 6c60a17ca49f87570886328e42672d5fd0fcf9510e928c99382fe173cac38081 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/TC36.json](../docs/evidence/tcp_20261116T163844Z_cc01e8/TC36.json) | e99c838e37eea69a60e562c92058b7b1259786cbf70f92905fc42e92b90118cf |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/test_cases.csv](../docs/evidence/tcp_20261116T163844Z_cc01e8/test_cases.csv) | dc7ebf8ee3fc687e7b0a492fde06712fec64810f5823e7b29525190acf848de9 |
| Tạo bằng chứng | [docs/evidence/tcp_20261116T163844Z_cc01e8/test_cases.md](../docs/evidence/tcp_20261116T163844Z_cc01e8/test_cases.md) | ca5a90bebd940bc1da34360389229f2bab1f4013030a9a69d50a3cc0091e5295 |
| Tạo bằng chứng | [docs/evaluations/dashboard_http_20261116T154448Z_7a27a7_http_9ccf89f23170.json](../docs/evaluations/dashboard_http_20261116T154448Z_7a27a7_http_9ccf89f23170.json) | aa7498dd46a5fa711bdc15b3034aa4300e896ca2d1937ed5eccaf7196a1d3c9f |
| Tạo bằng chứng | [docs/evaluations/http_9ccf89f23170/events.sqlite3](../docs/evaluations/http_9ccf89f23170/events.sqlite3) | 09ffd31336cae36cb09b70082e32074739e8315a285d783d5f841601f78e3578 |

Tạo thêm chính file docs/REVIEW_FILES.md (không tự hash).

Tạo thêm [manifest.json](reviews/review_20261116T163259Z_049c87/manifest.json) của lượt rà soát; SHA-256: fc5bc4a6315a31caa026f9b230dcf93862b97a39b899489cc4b93822a3a07b4b.
