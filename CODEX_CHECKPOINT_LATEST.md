# CODEX CHECKPOINT — Highlight Desktop Test v1.1.9-autopublish5

Cập nhật: 2026-10-05 11:44 Asia/Saigon. Branch: `release/v1.1.9`.

## Bản đóng gói

- Source commit: `b40e27d3f1b94c8447ff29438db1500fa2a1d9e8`; build identity ghi source sạch.
- Tag mới: `v1.1.9-autopublish5`; giữ nguyên `autopublish4`.
- Installer: `704501760` bytes.
- SHA-256: `40ffe07f9f08cda10b2b8763b97eb9802319c4b1ebed07ae7041e107a60c6ed8`.
- Release đích: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.1.9-autopublish5
- Installer đích: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-autopublish5/Highlight_Desktop_Test_Setup_v1.1.9-autopublish5.exe

Checkpoint asset này ghi trạng thái đã kiểm chứng trước khi publish. Bằng chứng công khai sau publish được ghi tại `release/autopublish5_release.json`, `support/autopublish5/evidence/public_download_verify.json` và `E:/OPENCLAW/BOB/CODEX_CHECKPOINT_LATEST.md`.

## Phần app đã sửa

Lưu `meta_last_publish_attempt` riêng với lần đọc trạng thái: thời gian, endpoint, operation, HTTP, code/subcode, error message, trace ID, Token ID và trạng thái accepted/rejected/unknown. Không lưu giá trị access token trong báo cáo.

Dashboard hiện đúng effective recovery token, giữ Token ID gốc riêng. Số lần đọc trạng thái và số lần thử đăng được tách rõ. Modal Kiểm tra Meta hiển thị credential ACTIVE, mapping Page đã xác minh, quyền tạo nội dung, phản hồi đăng gần nhất và nút Sao chép báo cáo lỗi.

Chức năng Đồng bộ quyền và thử đăng lại cùng scheduler tiếp tục dùng video hiện có, làm mới Page token, xác minh đúng Page/quyền và đối soát trước khi retry. Kết quả accepted hoặc unknown không được coi là đã đăng. Không tạo upload mới cho hai bài này.

Số luồng đăng và Content/LLM nhập trực tiếp 1–32. Kiểm tra UI đã nhập 7/6, lưu qua reload; chặn 33 và 2.5; trả lại cấu hình người dùng 8/4.

## Lỗi thực tế của hai bài

Page Lucas Bryant `1366749239846014`. Các probe trước bản sửa xác minh Autopost23 và Autopost25 đều ACTIVE, kiểu SYSTEM_USER, Page được xuất bản, mapping đúng và có CREATE_CONTENT; Page/video GET HTTP 200, không có copyright match. Lần retry trên app mới cũng làm mới credential thành công.

| Local post | Meta ID giữ nguyên | Token thực sự dùng | Lệnh đăng | Kết quả |
| --- | --- | --- | --- | --- |
| `post_1791121129_7e1a6d` | `1373334701223226` | Autopost25, `tok_1791016031_29` | POST `/v22.0/1366749239846014/video_reels`, finish | HTTP 400, 368/4854002 |
| `post_1791121324_dae163` | `1722433486142952` | Autopost23, `tok_1791016027_24` | POST `/v22.0/1722433486142952`, publish existing | HTTP 400, 368/4854002 |

Phản hồi Meta nguyên văn: “Bạn cần xác nhận danh tính của mình rồi mới có thể đăng dưới tên Trang này. Hãy mở ứng dụng Facebook trên điện thoại và làm theo hướng dẫn.”

- Bài thứ nhất: receipt lúc 11:40:21, trace `ALncBOxh9PuXtSW7sbd6ayw`; upload complete, processing/publishing not_started.
- Bài thứ hai: receipt lúc 11:40:29, trace `AtL8l4bTj3ND0wNU7WvSK2r`; video ready, processing complete, publishing scheduled.
- Token ID gốc của cả hai vẫn là `tok_1791016027_24`; lựa chọn phục hồi của bài thứ nhất lưu riêng.
- UI audit lúc 11:43: bài thứ nhất 174 lần đọc / 20 lần thử đăng; bài thứ hai 104 lần đọc / 21 lần thử đăng. GET thành công không xóa receipt POST bị từ chối.

Token hợp lệ không đảm bảo Meta cho phép xuất bản dưới tên Page. Đây là checkpoint xác minh quyền xuất bản do Meta thực thi. App không thể bỏ qua. Quản trị viên cần hoàn tất hướng dẫn Facebook trên điện thoại hoặc kiểm tra tài khoản quản lý và đúng Page trong Meta Business Suite, rồi để app retry hoặc dùng nút phục hồi.

## Cài thử và dữ liệu

Cài có kiểm soát vào `E:/OPENCLAW/BOB/Highlight destop test` lúc 11:37:54, chỉ khi render/content worker rảnh và hai upload đã được đọc lại. 26 file mutable giữ nguyên hash qua extraction; 24 code hash của app cài đặt khớp payload. Không chạy lại migration/repair cũ. Render queue đã resume.

Audit read-only lúc `2026-10-05T11:42:49+07:00`: **398/400 bài published; 398 First Comments posted**. Đã đọc lại 11 bài phục hồi trước và 11 comment qua Meta API. Giữ nguyên tất cả 400 record, Page/Token IDs, article URLs, package IDs; 303 upload IDs, 138 video IDs và 388 post IDs cũ.

App được quan sát ở `http://127.0.0.1:54541`, Python PID `14640`. Scheduler thread sống, last cycle OK. Port sẽ thay đổi sau restart; rediscover trước khi gọi API.

## Kiểm chứng và evidence

- Full suite: **482 passed, 3 skipped, 29 subtests passed**.
- `git diff --check` sạch; hai HTML mirrors giống nhau.
- Payload: 8.006 entries; posts seed rỗng; không runtime state hoặc credential seed; source identity sạch.
- UI thật: hiệu lực Token phục hồi, Token gốc riêng, số lần đọc/đăng, HTTP/endpoint/code/trace, nút phục hồi và copy JSON qua clipboard đều đạt. JSON copy không có raw credential.
- Evidence local: `support/autopublish5/evidence/payload_verify.json`, `pre_install_snapshot.json`, `install_preservation.json`, `live_ui_verify.json`, `recovery_saved_credentials.json`, `diagnostic_ui_verify.json`, `final_live_audit.json`.
- Probe token/Page trước đó: `support/autopublish4/evidence/meta_page_token_probe.json`, `meta_debug_token_probe.json` và hai receipt recovery cũ. Không relabel evidence cũ thành kết quả bản mới.

## Bước tiếp theo cụ thể

1. Quản trị viên xử lý yêu cầu xác minh danh tính trên Facebook cho quyền đăng dưới tên Lucas Bryant.
2. Trong app mở Kiểm tra Meta cho từng bài, chọn đúng Token quản lý Page, bấm Đồng bộ quyền và thử đăng lại; hoặc để scheduler retry theo backoff.
3. Đọc lại đúng `1373334701223226` và `1722433486142952`; chỉ đạt khi Meta báo published, app xác minh permalink và First Comment posted.
4. Mục tiêu cuối là 400/400 bài và 400/400 comment. Hiện chưa đạt do Meta vẫn từ chối hai POST; không ghi nhận thành công giả và không upload lại.

## Final public deployment — 2026-10-05 12:02 Asia/Saigon

- GitHub release ID `403373771`, tag `v1.1.9-autopublish5`, `draft=false`, `prerelease=true`.
- Public release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.1.9-autopublish5
- Public installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-autopublish5/Highlight_Desktop_Test_Setup_v1.1.9-autopublish5.exe
- Installer SHA-256: `40ffe07f9f08cda10b2b8763b97eb9802319c4b1ebed07ae7041e107a60c6ed8`; bytes `704501760`.
- Public download check passed without authentication: checkpoint and checksum HTTP 200 with exact content; installer HTTP 206 prefix matched and GitHub full asset digest matched.
- Packaged source commit: `b40e27d3f1b94c8447ff29438db1500fa2a1d9e8`; initial documentation commit: `9adff4910375744226cba4209b76139e7f85eb13`. Later checkpoint-only commits retain the same packaged code and tag.
- Latest live read-only audit at 12:02:55: 400 records preserved; `398/400` published and `398/400` First Comments posted; both unresolved IDs still read HTTP 200 but Meta POST still returns `368/4854002`.
- The two IDs remain `1373334701223226` and `1722433486142952`; no re-upload was made. After Facebook identity confirmation, use the app recovery button or leave scheduler running until both IDs and comments verify.

Evidence: `support/autopublish5/evidence/public_download_verify.json`, `diagnostic_ui_verify.json`, `final_live_audit.json`, `install_preservation.json`.
