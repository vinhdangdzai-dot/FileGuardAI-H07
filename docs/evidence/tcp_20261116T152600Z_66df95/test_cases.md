# TCP test cases

| TC | Input | Expected | Actual | Result | Evidence |
|---|---|---|---|---|---|
| TC01 | /download?path=baocao.pdf | HTTP 200; SQLite correct; no secret | HTTP 200; all checks true | PASS | [TC01.json](TC01.json) |
| TC02 | /download?path=b%C3%A1o%20c%C3%A1o%20t%E1%BB%91t%20nghi%E1%BB%87p.pdf | HTTP 200; SQLite correct; no secret | HTTP 200; all checks true | PASS | [TC02.json](TC02.json) |
| TC03 | /download?path=tailieu/chuong1.pdf | HTTP 200; SQLite correct; no secret | HTTP 200; all checks true | PASS | [TC03.json](TC03.json) |
| TC04 | /download?path=../docs/evidence/tcp_20261116T152600Z_66df95/outside_secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC04.json](TC04.json) |
| TC05 | /download?path=.. | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC05.json](TC05.json) |
| TC06 | /download?path=..%5Cdocs%5Cevidence%5Ctcp_20261116T152600Z_66df95%5Coutside_secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC06.json](TC06.json) |
| TC07 | /download?path=C%3A%5CUsers%5CHUU%20VINH%5CFileGuardAI_H07_MVP_10000_mau_khong_trung%5CFileGuardAI_H07%5Cdocs%5Cevidence%5Ctcp_20261116T152600Z_66df95%5Coutside_secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC07.json](TC07.json) |
| TC08 | /download?path=/etc/passwd | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC08.json](TC08.json) |
| TC09 | /download?path=C%3A%5CWindows%5Cwin.ini | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC09.json](TC09.json) |
| TC10 | /download?path=%5C%5Cserver%5Cshare%5Csecret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC10.json](TC10.json) |
| TC11 | /download?path=%2e%2e%2fdocs/evidence/tcp_20261116T152600Z_66df95/outside_secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC11.json](TC11.json) |
| TC12 | /download?path=%252e%252e%252fsecret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC12.json](TC12.json) |
| TC13 | /download?path=%25252e%25252e%25252fsecret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC13.json](TC13.json) |
| TC14 | /download?path=%2e%2e%5csecret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC14.json](TC14.json) |
| TC15 | /download?path=h07_missing_33613fd456394af09025ba467a635acf.txt | HTTP 404; SQLite correct; no secret | HTTP 404; all checks true | PASS | [TC15.json](TC15.json) |
| TC16 | /download?path=tailieu/kh%C3%B4ng%20t%E1%BB%93n%20t%E1%BA%A1i%2033ae47b7e1164e878545d906add36cec.txt | HTTP 404; SQLite correct; no secret | HTTP 404; all checks true | PASS | [TC16.json](TC16.json) |
| TC17 | /download?path=tailieu/../../secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC17.json](TC17.json) |
| TC18 | /download?path=%00secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC18.json](TC18.json) |
| TC19 | /download?path=tailieu | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC19.json](TC19.json) |
| TC20 | symlink file | HTTP 403; no external content | OSError: [WinError 1314] A required privilege is not held by the client: 'C:\\Users\\HUU VINH\\FileGuardAI_H07_MVP_10000_mau_khong_trung\\FileGuardAI_H07\\docs\\evidence\\tcp_20261116T152600Z_66df95\\outside_secret.txt' -> 'C:\\Users\\HUU VINH\\FileGuardAI_H07_MVP_10000_mau_khong_trung\\FileGuardAI_H07\\shared_files\\__tcp_ffefeff3a7ce49a3b716107c8c61bb6aTC20' | SKIP | [TC20.json](TC20.json) |
| TC21 | symlink file | HTTP 403; no external content | OSError: [WinError 1314] A required privilege is not held by the client: 'C:\\Users\\HUU VINH\\FileGuardAI_H07_MVP_10000_mau_khong_trung\\FileGuardAI_H07\\docs\\evidence\\tcp_20261116T152600Z_66df95\\outside_secret.txt' -> 'C:\\Users\\HUU VINH\\FileGuardAI_H07_MVP_10000_mau_khong_trung\\FileGuardAI_H07\\shared_files\\__tcp_ffefeff3a7ce49a3b716107c8c61bb6aTC21' | SKIP | [TC21.json](TC21.json) |
| TC22 | symlink directory | HTTP 403; no external content | OSError: [WinError 1314] A required privilege is not held by the client: 'C:\\Users\\HUU VINH\\FileGuardAI_H07_MVP_10000_mau_khong_trung\\FileGuardAI_H07\\docs\\evidence\\tcp_20261116T152600Z_66df95' -> 'C:\\Users\\HUU VINH\\FileGuardAI_H07_MVP_10000_mau_khong_trung\\FileGuardAI_H07\\shared_files\\__tcp_ffefeff3a7ce49a3b716107c8c61bb6aTC22' | SKIP | [TC22.json](TC22.json) |
| TC23 | /download?path=__tcp_ffefeff3a7ce49a3b716107c8c61bb6a_junction/outside_secret.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC23.json](TC23.json) |
| TC24 | /download?path=__tcp_ffefeff3a7ce49a3b716107c8c61bb6a_junction/missing.txt | HTTP 403; SQLite correct; no secret | HTTP 403; all checks true | PASS | [TC24.json](TC24.json) |
