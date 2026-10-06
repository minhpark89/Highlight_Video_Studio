# Checkpoint v1.2.4 — Meta Graph API v24.0

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.4`. Người dùng yêu cầu build theo Meta API 24 như MXH; bản v1.2.3 dùng v22.0.

## Thay đổi

- Thêm `src/publisher/meta_api.py`: GRAPH_API_VERSION v24.0 và GRAPH_BASE_URL dùng chung.
- Chuyển mặc định Reel Init/upload/Finish, comment, đối soát, phục hồi, hủy lịch sang v24.0 qua MetaReelPoster.
- Token identity/discovery, bulk token health và Page Insights dùng cùng Graph base v24.0.
- URL avatar dự phòng và banner đăng bài cập nhật v24.0.
- App/launcher/installer nhận dạng v1.2.4. `/api/system/info` và `build_identity.json` ghi meta_graph_api_version.
- Cập nhật hai expected URL trong test hiện hữu theo v24.0; chưa thêm test case hoặc chạy test.

Không đổi worker/queue/token/Page binding, pacing 900s, nội dung, First Comment, upload ID hoặc quy tắc phục hồi giao dịch. Bản này thực hiện yêu cầu đổi API; các tối ưu scheduler vẫn là đề xuất trong `E:\OPENCLAW\BOB\META_BLOCK_AND_LATE_SCHEDULE_REVIEW.md`.

## Giới hạn đã biết

GET chẩn đoán trước build đã cho thấy v24.0 và kiểu authentication của MXH vẫn nhận API access blocked trên credential bị hạn chế. Đổi phiên bản API không chứng minh giải quyết App Roles/quyền hoặc backlog scheduler. Ảnh App giữ lịch còn do dispatcher theo đợt, đối soát tuần tự và pacing cùng token; chưa triển khai sửa các phần này.

Runtime đang chạy ở `E:\OPENCLAW\BOB\Highlight destop test` vẫn v1.2.3 trong lúc build. Chưa tự cài, dừng process, sửa queue live hoặc chủ động POST/DELETE Meta/CMS.

## Build

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.4 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.4/inspect_payload.ps1
```

Các kiểm tra đóng gói đọc payload/identity/hash/seed, không chạy app hoặc đăng bài. Không chạy test hồi quy vì người dùng chỉ yêu cầu build. Source sạch trước đóng gói, tag local v1.2.4 chỉ vào source đã đóng gói; checkpoint có thể có commit mới hơn sau build.

Artifact dự kiến: `release/Highlight_Desktop_Test_Setup_v1.2.4.exe`, `.sha256`, checkpoint bản mới. Chưa có kết quả build ở thời điểm viết đoạn này; bổ sung evidence sau khi tạo artifact thành công. Chưa phát hành GitHub.
