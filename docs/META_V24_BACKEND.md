# Meta v24: System User, Page token, Reel và First Comment

Đối chiếu tài liệu chính thức ngày 2026-10-06. Backend/app v1.2.5 dùng Graph API **v24.0**. App v1.2.3 đang cài dùng v22.0; v1.2.4 là bộ cài local chỉ chuyển phiên bản API trước yêu cầu bổ sung backend. Không sửa tag/bộ cài v1.2.4 hay release v1.2.3 đã công bố.

## Kết luận từ Meta

- [Changelog v24](https://developers.facebook.com/docs/graph-api/changelog/version24.0/): phát hành 2025-10-08. Không ghi thay đổi riêng giúp System User/NPE hết hạn chế. Trang tài liệu hiện tại có ví dụ v25/v26; không coi các ví dụ này là thay đổi riêng của v24.
- [Access Tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/): System User dùng cho hành động tự động trên tài sản doanh nghiệp được cấp quyền. Employee System User cần được gán tài sản; app và token phải có quyền phù hợp. Page token đại diện hành động của Page.
- [System Users](https://developers.facebook.com/docs/business-management-apis/system-users/): tài sản phải thuộc hoặc được Business quản lý. Nếu phần mềm làm thay cho khách hàng/người dùng thật, cần quan hệ ủy quyền Facebook Login phù hợp; không thể suy ra quyền của họ từ token System User bất kỳ.
- [Pages overview](https://developers.facebook.com/docs/pages-api/overview/): Page token riêng theo Page, người dùng và app. `CREATE_CONTENT` dùng đăng nội dung; `MODERATE` dùng trả lời bình luận; `MANAGE` dùng quản lý/gán tác vụ. Người có Admin access trong UI có tất cả tác vụ, nhưng backend không suy từ riêng chuỗi `MANAGE` rằng Meta đã trả `CREATE_CONTENT`/`MODERATE`.
- [Reels Publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing/): Page token, tác vụ `CREATE_CONTENT`, các scope `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`. Luồng Start → upload → Finish. Binary upload dùng HTTPS `rupload.facebook.com`, `Authorization: OAuth`, offset/file_size và `application/octet-stream`. Vì vậy không đổi MIME sang `video/mp4` chỉ vì mẫu MXH dùng MIME đó.
- [Object comments](https://developers.facebook.com/docs/graph-api/reference/object/comments/): tạo comment trên đối tượng Page cần Page token, `MODERATE`, `pages_manage_engagement`. Tài liệu nêu hỗ trợ New Pages Experience, bao gồm Video trong phần tạo comment.
- [Permissions](https://developers.facebook.com/docs/permissions/): scope đăng bài phụ thuộc `pages_read_engagement`, `pages_show_list`; scope quản lý bình luận phụ thuộc `pages_read_user_content`, `pages_show_list`. Chỉ yêu cầu các quyền phục vụ chức năng sử dụng.

## Đã đưa vào backend

1. Dùng shared Graph version v24 cho đăng Reel, bình luận, recovery/cancel, Token Vault, health và Insights.
2. Làm mới đúng root credential → `/me/accounts` → Page token trước mỗi lượt bắt đầu upload. Chọn theo chính `token_id` đã gắn với bài và đúng `page_id`, kiểm tra fingerprint/tasks; không dùng root token thay Page token khi discovery lỗi.
3. Cache kết quả làm mới tối đa 300 giây trong process, có lock riêng cho từng credential để các worker chờ một lượt Sync chung. Không thêm lock mạng toàn cục. Lỗi discovery giữ 60 giây rồi cho thử làm mới; không dùng kết quả Page token cũ để tiếp tục lượt upload sau lỗi đó.
4. Sync tự động không đổi credential chính của Page sang token khác. Binding bị thu hồi thì lượt gửi bị chặn; giữ token_id gốc và Meta upload ID để chẩn đoán/recovery.
5. Preflight phân biệt `publish`, `comment`, `read`. Đăng cần `CREATE_CONTENT`; comment cần `MODERATE`; đọc trạng thái không bị chặn chỉ vì thiếu tác vụ tạo nội dung. Giữ các alias NPE cụ thể đã được các bản trước lưu (`PROFILE_PLUS_CREATE_CONTENT`, `PROFILE_PLUS_MODERATE`) để tương thích dữ liệu cũ, không suy thêm quyền từ alias `MANAGE`.
6. [GET user permissions](https://developers.facebook.com/docs/graph-api/reference/user/permissions/) được dùng để đọc scope khi Meta cho phép introspection. Scope được xác minh mà thiếu thì báo tên scope và dừng thao tác tương ứng. Endpoint lỗi, trả rỗng hoặc không hỗ trợ loại token thì ghi `unverified`; không giả định scope đã được cấp và không coi trường hợp đó là bằng chứng System User không có quyền. Meta vẫn quyết định cấp quyền thực tế trên endpoint đăng/comment. Nhãn `SYS` do người dùng nhập không phải chứng nhận loại token từ Meta.
7. Graph dùng header Bearer để tránh token trong URL/body và lỗi kết nối. Discovery phân trang bằng `after` trên chính endpoint v24, không tải nguyên `paging.next` mang token. Upload chỉ gửi token đến HTTPS host `rupload.facebook.com`, không theo redirect sang đích khác.
8. Khi Meta trả code 200 kèm `API access blocked`, tạm dừng các lượt gửi mới cùng credential 60 giây. Đây là giảm request lặp; không phải cơ chế gỡ hạn chế. Bản ghi Init/Finish giữ operation, API endpoint không chứa token, HTTP/code/subcode/trace; không bị thay bằng một lần GET thành công sau đó.
9. Kết quả comment không xác nhận rõ hoặc HTTP 5xx được giữ `outcome_unknown`, tránh retry comment tạo trùng. Comment thất bại không làm đăng lại Reel. Giữ các guard upload ID, Finish, reconciliation, journal và lịch hiện có.
10. Batch health chỉ xác minh danh tính `/me`; cập nhật bằng merge dưới lock vault để không ghi đè metadata Page/scopes/counter vừa được worker khác cập nhật.

## Yêu cầu cấu hình phía Meta

[Pages overview](https://developers.facebook.com/docs/pages-api/overview/) ghi rõ app Development có thể yêu cầu quyền từ người có role trong app; với người dùng ngoài các role liên quan, cần App Review/Advanced Access theo loại app và use case. Vì vậy thêm tài khoản cá nhân vào role rồi hoạt động lại có thể liên quan tới access level/app configuration; chưa chứng minh đây là nguyên nhân chính xác của các credential đang bị block.

Quy trình System User hợp lệ: app thuộc Business phù hợp → gán System User quyền app → gán quyền trên đúng Page/tài sản → sinh token có scope cần thiết → lấy Page token và kiểm tra tác vụ → gọi endpoint. Backend không tự thêm tài khoản, thay role, tạo/thu hồi token hoặc đổi app cấp token.

[Secure requests](https://developers.facebook.com/docs/graph-api/guides/secure-requests/) hướng dẫn `appsecret_proof`. Nếu app bật **Require App Secret**, cần backend máy chủ tin cậy giữ App Secret và proxy request để thêm proof. Bộ cài desktop này không chứa App Secret và không tự xử lý cấu hình đó bằng cách nhúng secret. Yêu cầu proof tại endpoint tạo System User token không phải bằng chứng mọi Reel call luôn bắt buộc proof.

Hướng dẫn Reel hiện tại nêu giới hạn 30 bài API trong cửa sổ 24 giờ và lịch Meta phải cách hiện tại hơn 10 phút, trong 29 ngày. Không coi 15 phút giãn token của app là quota bắt buộc do Meta công bố. Đợt này giữ scheduler/pacing hiện có; đề xuất tách dispatcher/worker, tối ưu đối soát/comment và hiển thị lý do chờ nằm trong `POST_OPTIMIZATION_REVIEW.md` và `META_BLOCK_AND_LATE_SCHEDULE_REVIEW.md` ở thư mục BOB.

## Bằng chứng và giới hạn

Snapshot tài liệu: `E:\OPENCLAW\BOB\support\meta-v24-docs-20261006`, metadata `sources*.json`. Một số đường dẫn cũ trả 404; chúng không được dùng làm căn cứ.

Mẫu MXH đã được đọc IL, không chạy mẫu: cùng luồng Start/upload/Finish, mặc định v24, gọi `/me/accounts` trước publish, semaphore theo KeyId. GET theo header/UA/version giống MXH vẫn trả `API access blocked` với các credential đang lỗi trong phiên rà soát. Không xác nhận MXH đăng được đúng cùng Page/token/thời điểm bằng một receipt POST; không hứa đổi v24 sẽ bỏ hạn chế.

Không chạy test chức năng/hồi quy hoặc đăng bài thật trong lượt đóng gói. Chỉ rà soát source/cú pháp, build bằng `-SkipTests`, rồi đọc payload và đối chiếu hash/identity/state. Tại mốc đóng gói chưa cài bộ mới vào app đang chạy và chưa phát hành GitHub. Sau đó người dùng đã yêu cầu deploy v1.2.5 để tự tải/cài; trạng thái phát hành và tải công khai được ghi trong checkpoint/evidence trên nhánh release/v1.2.5.
