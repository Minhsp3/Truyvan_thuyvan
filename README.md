# Trang truy vấn sản lượng và lưu lượng

Ứng dụng Streamlit hiển thị số liệu tháng hiện tại của ba nhà máy Buôn Kuốp, Buôn Tua Srah và Srêpốk 3, đồng thời tìm năm đồng dạng từ dữ liệu lịch sử.

## Chạy từ GitHub

GitHub lưu trữ mã nguồn; để mở dashboard trên Internet, triển khai repository này bằng
[Streamlit Community Cloud](https://share.streamlit.io/):

1. Đẩy mã nguồn và dữ liệu lên nhánh `main` của repository.
2. Trong Streamlit Community Cloud, chọn **Create app** và kết nối repository GitHub.
3. Chọn nhánh `main`, đặt **Main file path** là `streamlit_app.py`, rồi bấm **Deploy**.

Nền tảng tự cài các thư viện trong `requirements.txt` và tự cấp cổng chạy. Không chạy
`run_dashboard.py` trên Community Cloud vì tệp đó chỉ dành cho máy Windows/LAN.

Repository cũng hỗ trợ GitHub Codespaces. Khi mở Codespace, môi trường tự cài thư viện,
chạy `streamlit_app.py` trên cổng 8501 và mở cổng này trong phần **Ports**.

> Lưu ý: hệ thống tệp của Community Cloud chỉ là tạm thời. Muốn cập nhật dữ liệu lâu dài,
> hãy thay các file Excel trong repository rồi commit/push lên GitHub. File tải lên từ giao
> diện và thay đổi tạo ra khi ứng dụng đang chạy sẽ mất khi ứng dụng khởi động lại.

## Chạy ứng dụng

Khởi động theo giao diện terminal có địa chỉ Local và LAN:

```powershell
.\.venv\Scripts\python.exe run_dashboard.py
```

Hoặc nhấp đúp `run_dashboard.bat`.

Dashboard ưu tiên chạy tại `http://127.0.0.1:8501`. Nếu cổng này đang được dùng,
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
