# Trang truy vấn sản lượng và lưu lượng

Ứng dụng Streamlit hiển thị số liệu tháng hiện tại của ba nhà máy Buôn Kuốp, Buôn Tua Srah và Srêpốk 3, đồng thời tìm năm đồng dạng từ dữ liệu lịch sử.

## Chạy ứng dụng

Khởi động theo giao diện terminal có địa chỉ Local và LAN:

```powershell
.\.venv\Scripts\python.exe run_dashboard.py
```

Hoặc nhấp đúp `run_dashboard.bat`.

Dashboard ưu tiên chạy tại `http://127.0.0.1:10005`. Nếu cổng này đang được dùng,
trình khởi động tự chọn cổng trống kế tiếp. Máy khác trong cùng mạng nội bộ dùng
địa chỉ `LAN access` được in trên terminal.

Môi trường `.venv` của dự án đã chứa toàn bộ thư viện cần thiết. Trong VS Code,
hãy mở đúng thư mục dự án; file `.vscode/settings.json` sẽ tự chọn interpreter này.

Nếu VS Code vẫn đang mở một terminal cũ, hãy đóng terminal đó, mở terminal mới rồi
chạy lại lệnh trên.

Đặt các file `.xlsx`, `.xls` hoặc `.xlsm` trong cùng thư mục với ứng dụng. Có thể tải file trực tiếp từ thanh bên của trang.

Ứng dụng cũng tự đọc dữ liệu ngày trong hai thư mục:

- `San luong`: các báo cáo `BCSX_Thang` theo tháng.
- `Thuy van ngay`: các báo cáo `TV_Ngay` của ba nhà máy.

Ngày cập nhật là ngày mới nhất có đủ dữ liệu của cả ba nhà máy trong cả hai thư mục.
Nếu đang giữa tháng, sản lượng dự kiến của tháng bằng sản lượng thực tế đã phát cộng
sản lượng từng ngày còn lại của năm đồng dạng. Các tháng sau lấy tổng tháng của năm đồng dạng.

Ứng dụng nhận dạng hai kiểu dữ liệu chính:

1. Bảng dài có các cột `Năm`, `Tháng`, `Nhà máy`, `Sản lượng`, `Lưu lượng`.
2. Workbook có mỗi sheet mang tên một năm, 12 cột tháng, các hàng sản lượng và lưu lượng của từng nhà máy.

Năm đồng dạng được xếp hạng theo toàn bộ quy luật sản lượng và lưu lượng từ
tháng 1 đến kỳ dữ liệu hiện tại. Sai lệch tuyệt đối bình quân của từng chuỗi
được chuẩn hóa theo mức trung bình của chuỗi hiện tại, sau đó tổng hợp thành
điểm chung. Năm lịch sử thiếu dữ liệu trong giai đoạn so sánh sẽ bị loại.
