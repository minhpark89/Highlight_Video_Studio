# Checkpoint v1.2.5 — Meta v24 và Page credential backend

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.5`; kế thừa v1.2.4 chuyển Graph v22 → v24. Người dùng yêu cầu kiểm tra đúng docs Meta về System User/New Pages Experience và đưa phần phù hợp vào backend như MXH.

## Tài liệu và thay đổi

Đọc [docs/META_V24_BACKEND.md](docs/META_V24_BACKEND.md) để xem nguồn chính thức, yêu cầu scope/task, App Review/access level, App Secret và các giới hạn chưa xác định được.

- Làm mới đúng credential/Page trước Init, cache tối đa 300 giây và lock riêng mỗi credential; discovery lỗi giữ 60 giây rồi cho làm mới lại, không dùng Page token cũ để bắt đầu upload.
- Page token phải có binding/fingerprint đúng root token_id và Page ID. Auto sync không đổi canonical credential sang token khác.
- CREATE_CONTENT và MODERATE được kiểm tra riêng; MANAGE không được coi là chứng minh quyền đăng/bình luận. Scope đọc được thì kiểm tra thiếu; không đọc được ghi unverified. /me chỉ là identity health, không phải bằng chứng đăng được.
- Graph auth dùng Bearer header; pagination qua cursor endpoint v24. Rupload giữ OAuth/octet-stream theo docs; ràng buộc đúng HTTPS host và không theo redirect.
- API access blocked dừng lượt gửi mới cùng credential 60 giây. Init/Finish giữ sanitized receipt. Không làm lại Reel khi comment lỗi; comment kết quả không rõ/HTTP5xx giữ outcome_unknown.
- Giữ scheduler/pacing/lịch và Meta upload IDs hiện tại. Các đề xuất tăng tốc scheduler chưa được triển khai trong bản này.

## Quyền tác động

Chỉ sửa source-worktree và tạo artifact local. Không cài/khởi động bản mới trong thư mục `Highlight destop test`, không đổi lịch thật, không POST/DELETE Facebook, không thêm role/tạo token hoặc phát hành GitHub. Release/tag/bộ cài v1.2.3 đã công bố và tag v1.2.4 local được giữ nguyên.

## Đóng gói

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.5 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.5/inspect_payload.ps1
```

Không thêm/chạy test chức năng hoặc hồi quy. Rà soát source/cú pháp trước build; công cụ inspect chỉ đọc payload/hash/identity/seed, không chạy app/bộ cài hoặc gửi Meta request. Source sạch và tag local v1.2.5 cố định trước build.

**Build và payload inspection đã hoàn tất.**

- Installer: `release/Highlight_Desktop_Test_Setup_v1.2.5.exe`, **705077760 bytes**.
- SHA256: `8194509413b225e4217231bc9441be406e2f18132c3b1b0f7395c3c3b53f53b0`.
- Source commit/tag v1.2.5: `1bed062ae03f67fbedcfda468cbc818878830ba6`, build identity `source_dirty=false`, app/prerelease v1.2.5, Meta API v24.0.
- Payload khớp **19 file** source; không còn production v22, credential seed rỗng, không có dữ liệu người dùng/lịch/token/machine identity. Evidence: `checkpoints/evidence/v1.2.5/installer_payload.json`.
- AST rà soát cú pháp 10 file Python thay đổi; không execute code app. Không chạy hồi quy/chức năng hoặc POST Meta. Chưa cài vào runtime thật, chưa publish GitHub.
- Bản tiện tải được sao chép ra `E:\OPENCLAW\BOB\Highlight_Desktop_Test_Setup_v1.2.5.exe` cùng SHA256. Hash của bản sao phải khớp installer đã inspect.

Các commit cập nhật checkpoint/evidence sau build có thể nằm sau tag v1.2.5; không đổi tag hoặc code đã đóng gói. Root `CODEX_CHECKPOINT_LATEST.md` trỏ tới checkpoint này.

## Tình trạng hạn chế và lịch trễ

Rà soát trước đó thấy 7/41 credential code200 API access blocked ngay cả GET root/Page; header/UA/v24 như MXH cũng lỗi. Chưa có receipt MXH cùng token/Page/thời điểm để kết luận khác biệt POST là nguyên nhân. Thêm personal account vào app role có thể liên quan tới access level, chưa xác minh cấu hình app của từng token lỗi.

Lịch trễ trước đó có worker tiến triển nhưng batch pool/đối soát/comment/giãn token 900 giây làm chậm. V24 không có căn cứ để tự giải quyết backlog. Xem các báo cáo ở thư mục BOB: `META_BLOCK_AND_LATE_SCHEDULE_REVIEW.md`, `POST_OPTIMIZATION_REVIEW.md`, `CHECKPOINT_META_POST_TOKEN_COMPARISON_20261006.md`.
