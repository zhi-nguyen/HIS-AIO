# **TODO LIST: Backend Completion & AI Integration (Architect Revised)**

Danh sách này đã được tinh chỉnh để đảm bảo luồng vận hành (Workflow) của bệnh viện được thông suốt trước khi tích hợp AI sâu hơn.

## **0\. Queue Management System (QMS) \- NEW & CRITICAL**

**Status:** Chưa có.

**Priority:** **Highest** (Mạch máu lưu thông bệnh nhân).

**Lý do:** Để AI điều phối được, nó phải biết bệnh nhân đang đứng ở đâu.

* \[ \] **Data Models (core\_services/reception hoặc module mới qms)**  
  * \[ \] QueueNumber: Số thứ tự (VD: PK01-005 \- Phòng khám 1, số 5).  
  * \[ \] WaitingRoom: Danh sách bệnh nhân đang chờ tại một "Station" (Phòng khám, Phòng Lấy Mẫu, Nhà thuốc).  
  * \[ \] QueueStatus: WAITING, IN\_PROGRESS, COMPLETED, SKIPPED.  
* \[ \] **Logic Flow**  
  * \[ \] Khi Check-in \-\> Sinh số QueueNumber \-\> Đẩy vào WaitingRoom của Triage hoặc Bác sĩ.  
  * \[ \] Khi Bác sĩ Finish Visit \+ Order Lab \-\> Hệ thống tự động đẩy bệnh nhân sang WaitingRoom của LIS/RIS.  
* \[ \] **AI Tools**  
  * \[ \] get\_current\_queue\_length(department\_id): AI ước tính thời gian chờ.

## **1\. Laboratory Information System (LIS)**

**Status:** backend/apps/medical\_services/lis/models.py cần triển khai.

**Priority:** High (Critical cho Paraclinical Agent).

* \[ \] **Data Models**  
  * \[ \] LabCategory: Huyết học, Sinh hóa, Vi sinh, MDB (Mô bệnh học).  
  * \[ \] LabTest: Định nghĩa chỉ số (Mã, Tên, Đơn vị, Min/Max reference, Giá tiền, **TG trả kết quả**).  
  * \[ \] LabOrder: Phiếu chỉ định xét nghiệm (Link tới Visit).  
  * \[ \] LabSample: **Quan trọng**. Quản lý mẫu bệnh phẩm (Barcode, Thời gian lấy mẫu, Người lấy mẫu).  
  * \[ \] LabResult: Kết quả chi tiết. Cần trường is\_verified (Đã duyệt) và verified\_by (Bác sĩ duyệt).  
* \[ \] **Services & Logic**  
  * \[ \] Order Creation: Từ màn hình bác sĩ \-\> Tạo LabOrder \-\> Tạo LabSample (Pending).  
  * \[ \] Sample Collection: Điều dưỡng xác nhận "Đã lấy máu" \-\> Đổi trạng thái Sample.  
  * \[ \] Auto-flagging: So sánh kết quả với Min/Max \-\> Đánh dấu High/Low/Panic.  
* \[ \] **AI Tools (Function Calling)**  
  * \[ \] recommend\_lab\_tests(symptoms): Gợi ý chỉ định dựa trên triệu chứng.  
  * \[ \] interpret\_lab\_results(lab\_order\_id): Đọc và giải thích kết quả cho bác sĩ/bệnh nhân.

## **2\. Radiology Information System (RIS) / PACS**

**Status:** backend/apps/medical\_services/ris/models.py cần triển khai.

**Priority:** High.

* \[ \] **Data Models**  
  * \[ \] Modality: Loại máy (X-Quang, CT, MRI, Siêu âm).  
  * \[ \] ImagingOrder: Phiếu chỉ định.  
  * \[ \] ImagingResult: Chứa kết quả đọc (Text) và **Link ảnh DICOM** (URL tới PACS server giả lập hoặc MinIO).  
* \[ \] **Services & Logic**  
  * \[ \] Giả lập flow: Chỉ định \-\> Chụp (Pending \-\> Executed) \-\> Bác sĩ CĐHA đọc kết quả \-\> Trả kết quả về EMR.  
* \[ \] **AI Tools**  
  * \[ \] analyze\_report\_text(report\_content): Tóm tắt kết luận của bác sĩ CĐHA.

## **3\. Inpatient Department (IPD) \- Nội trú**

**Status:** backend/apps/medical\_services/inpatients đã có khung.

**Priority:** Medium (Sau khi hoàn thiện quy trình Ngoại trú \- OPD).

* \[ \] **Data Models**  
  * \[ \] Ward (Khoa), Room (Phòng), Bed (Giường). Quản lý trạng thái giường (Trống, Đang nằm, Đang dọn).  
  * \[ \] Admission: Hồ sơ nhập viện (Link tới Patient).  
  * \[ \] DailyCare: Tờ điều trị hàng ngày (Diễn biến, Y lệnh thuốc, Y lệnh chăm sóc).  
* \[ \] **Logic**  
  * \[ \] ADT (Admission, Discharge, Transfer): Nhập viện, Xuất viện, Chuyển khoa.  
  * \[ \] Chuyển bệnh nhân từ Visit (Khám bệnh) sang Admission (Nhập viện).

## **4\. Billing & Insurance (Tài chính)**

**Status:** Chưa có.

**Priority:** Medium-High (Cần thiết để khép kín quy trình).

* \[ \] **Data Models**  
  * \[ \] ServiceCatalog: Danh mục kỹ thuật & Giá (Có thể có nhiều bảng giá: BHYT, Dịch vụ, Người nước ngoài).  
  * \[ \] Invoice: Hóa đơn tổng.  
  * \[ \] InvoiceLineItem: Chi tiết (Tiền khám, Tiền thuốc, Tiền xét nghiệm).  
  * \[ \] Payment: Lịch sử thanh toán (Tạm ứng, Thanh toán cuối).  
* \[ \] **Logic**  
  * \[ \] Khi bác sĩ chỉ định (Order) \-\> Tự động tạo InvoiceLineItem (Trạng thái: Chưa thanh toán).  
  * \[ \] Chặn thực hiện CLS nếu chưa thanh toán (tùy cấu hình).

## **5\. Pharmacy Enhancements**

**Status:** Basic models exist.

**Priority:** Low (Models exist, needs refinement).

* \[ \] **Refinement**  
  * \[ \] Prescription cần trừ kho (Inventory) ngay khi Dispense (Xuất thuốc).  
  * \[ \] Lô/Hạn dùng (Lot/Expiry Date) để quản lý thuốc hết hạn.

## **6\. AI Agent "Brain" Wiring (The Integration)**

**Status:** Agents đã có, cần nối dây thần kinh vào các chi (Services mới).

**Priority:** High (Mục tiêu cuối cùng).

* \[ \] **RAG Update:**  
  * \[ \] Viết management command để index dữ liệu LabTest, ServiceCatalog, Drug vào Vector DB. Giúp AI biết bệnh viện "có gì".  
* \[ \] **Clinical Agent:**  
  * \[ \] Kết nối với EMR để lấy lịch sử khám (get\_patient\_history).  
  * \[ \] Kết nối LIS/RIS để đọc kết quả mới nhất.  
* \[ \] **Triage Agent:**  
  * \[ \] Kết nối với **QMS** để biết phòng nào đang trống.  
* \[ \] **Billing Support:**  
  * \[ \] AI trả lời câu hỏi: "Tổng chi phí dự kiến cho ca mổ ruột thừa là bao nhiêu?".

## **7\. Data Seeding**

**Status:** Cần thiết để test AI.

**Priority:** High.

* \[ \] Tạo script scripts/seed\_hospital\_flow.py:  
  * \[ \] Tạo 1 Bệnh nhân \-\> Khám (Visit) \-\> Chỉ định Lab \-\> Có kết quả Lab \-\> Kê đơn \-\> Mua thuốc.  
  * \[ \] Chạy luồng này để đảm bảo backend không bị gãy (crash) ở đâu.