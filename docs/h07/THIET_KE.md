# Kiến trúc, Activity, Sequence và ERD

## Kiến trúc triển khai

```mermaid
flowchart TB
    Browser[Browser localhost] --> Flask[Flask web.py]
    Flask --> Auth[auth.py: role / CSRF / throttle]
    Flask --> ML[ml_features v1 + Logistic Regression advisory]
    Flask --> Guard[security.py: validate / lstat / containment / regular file]
    Guard --> Repo[(shared_files public)]
    ML --> Log[database.py: parameterized insert]
    Guard --> Log
    Auth --> Log
    Log --> DB[(Private SQLite: access_logs + security_events)]
    Auth --> Dashboard[Dashboard / AI results / admin CSV export]
    Dashboard --> DB
    Dashboard --> Eval[(Versioned evaluation JSON and PNG)]
    Operator[Local OS operator] --> Hash[(Private password hashes)]
    Operator --> Backup[Online SQLite backup CLI]
    Operator --> Training[Offline training / validation / evaluation]
    Training --> Eval
```

Không có đường từ score AI sang cấp quyền filesystem. V2 nằm trong
artifact thực nghiệm; download vẫn dùng v1. FILES_ROOT không được chứa
DB, credential hoặc model; startup từ chối cấu hình vi phạm. Hai role
đăng nhập là admin và auditor, không có self-registration/upload/model
deployment API. Operator OS là tác nhân riêng, không đồng nhất cookie admin.

## Activity tải tệp

```mermaid
flowchart TD
    S([GET download]) --> D[Flask decode query một lần]
    D --> AI[AI advisory; skip input quá dài; lỗi ghi error]
    AI --> Q{Đúng một path?}
    Q -->|Không| B[403 BLOCK]
    Q -->|Có| V{Cú pháp / components an toàn?}
    V -->|Không| B
    V -->|Có| R{Link/reparse / containment hợp lệ?}
    R -->|Không| B
    R -->|Có| O[Mở file được cấp quyền]
    O -->|Không tồn tại| M[404 MISS]
    O -->|Regular file| A[200 ALLOW: stream handle]
    O -->|Permission/nonregular| B
    A --> L[(Insert access log)]
    M --> L
    B --> L
    L --> E([Response])
```

Nguồn UML Activity chuẩn PlantUML: [download_activity.puml](diagrams/download_activity.puml).

## Sequence

```mermaid
sequenceDiagram
    actor U as User
    participant W as Flask
    participant AI as LR advisory
    participant S as Security
    participant F as File repository
    participant DB as SQLite
    U->>W: GET /download?path=...
    W->>AI: score(raw after transport decode)
    AI-->>W: score/label or error
    W->>S: open_authorized(root, raw)
    S->>F: validate components / metadata / resolve / open
    F-->>S: regular handle or missing/rejected
    S-->>W: authorized handle / 404 / 403
    W->>DB: parameterized access event
    W-->>U: 200/403/404
```

## ERD thực tế (không bịa bảng users)

```mermaid
erDiagram
    access_logs {
        INTEGER id PK
        TEXT created_at
        TEXT client_ip
        TEXT requested_path
        REAL ml_score "nullable"
        TEXT ml_label
        TEXT action
        INTEGER http_status
        TEXT reason
        REAL duration_ms
    }
    security_events {
        INTEGER id PK
        TEXT created_at
        TEXT client_ip
        TEXT actor_role
        TEXT event
    }
```

Hai bảng độc lập, không có FK giả định. `actor_role` là nhãn sự kiện,
không FK users vì tài khoản admin/auditor cấu hình bằng hash file/env.
Access log: một dòng mỗi download; `ml_score` NULL khi unavailable/error/
skipped, action ALLOW/BLOCK/MISS tương ứng 200/403/404; `duration_ms` đo
xử lý trước truyền hết body, không phải latency end-to-end. Security
events không lưu mật khẩu, token hoặc cookie. Index: created_at cho
access_logs, (client_ip,created_at) cho security_events. Trigger cấm
UPDATE/DELETE cả hai bảng; INSERT được phép. Migration additive lúc
startup tạo bảng/index/trigger, không đổi hoặc xóa event cũ.

Session lưu role, trạng thái và CSRF trong cookie có chữ ký Flask;
không lưu password vào session. Hash password nằm ngoài kho public/Git.
