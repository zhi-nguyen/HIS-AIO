# HIS-AIO (Hospital Information System - All-In-One)
## HIS-AIO là hệ thống quản lý thông tin bệnh viện toàn diện, hiện đại, được thiết kế với kiến trúc All-In-One nhằm đồng bộ hóa toàn bộ quy trình vận hành y tế. Hệ thống tích hợp sâu Động cơ Trí tuệ Nhân tạo (AI Engine), hệ thống lưu trữ và truyền tải hình ảnh (PACS), cùng các chuẩn liên thông y tế quốc tế, giúp tối ưu hóa công tác quản lý và nâng cao chất lượng khám chữa bệnh.
# Công Nghệ Sử Dụng
## Backend
 - Ngôn ngữ & Framework: Python, Django, Django REST Framework (DRF)
 - Xử lý bất đồng bộ: Celery & Redis
 - WebSockets: Django Channels (cho QMS, Reception, LIS realtime)
## Frontend
 - Ngôn ngữ & Framework: TypeScript, Next.js (App Router), React
## Styling: Tailwind CSS / CSS Modules
## State & Realtime: Hooks tùy biến tích hợp WebSockets (useQmsSocket, useClinicalSocket, useReceptionSocket)
## AI Engine & Interoperability
 - AI Framework: LangChain / LangGraph (Quản lý luồng xử lý đa Agent)
 - PACS Server: Orthanc tích hợp OHIF Viewer (thông qua Nginx)
 - Tiêu chuẩn y tế: HL7 FHIR (Mappers/Parsers), DICOM (WADO, Worklist)
# Kiến Trúc Phân Hệ (Modules)
 - Mã nguồn Backend được tổ chức theo kiến trúc Modular, chia thành các nhóm dịch vụ cốt lõi:
## 1. Dịch Vụ Cốt Lõi (Core Services)
 - Authentication: Quản lý xác thực, phân quyền nhân viên y tế, quản trị người dùng.
 - Reception & Appointments: Tiếp đón bệnh nhân, đặt lịch khám, đánh giá phân luồng (Triage) với Triage Hints từ AI.
 - QMS (Queue Management System): Quản lý hàng đợi thông minh, tích hợp dịch vụ Text-to-Speech (TTS) gọi loa.
 - Billing: Quản lý viện phí, danh mục hóa đơn, thanh toán.
 - Patients & Departments: Quản lý hồ sơ bệnh nhân, danh mục phòng ban.
 - Kiosk & Scanner: Hỗ trợ phần cứng self-service và thiết bị quét mã vạch/CCCD.
## 2. Dịch Vụ Chuyên Môn (Medical Services)
 - EMR (Electronic Medical Record): Quản lý bệnh án điện tử, tích hợp gợi ý lâm sàng từ AI.
 - LIS (Laboratory Information System): Quản lý chỉ định, kết nối máy xét nghiệm, trả kết quả.
 - RIS (Radiology Information System): Quản lý chỉ định chẩn đoán hình ảnh, tích hợp Orthanc PACS.
 - Pharmacy: Quản lý nhà thuốc bệnh viện, kê đơn, tích hợp CDSS (Hệ thống hỗ trợ quyết định lâm sàng) và kiểm tra tương tác thuốc.
 - Inpatients: Quản lý quy trình nội trú.
## 3. AI Engine 
Được thiết kế dưới dạng hệ thống Multi-Agent Workflow:
 - Các Agents chuyên biệt: Triage Agent, Clinical Agent, Pharmacist Agent, Paraclinical Agent, Consultant Agent.
 - RAG Service: Hỗ trợ truy xuất thông tin, ngữ cảnh y khoa, kết hợp kỹ thuật PII Masking để bảo vệ dữ liệu bệnh nhân.
 - Streaming WebSockets giúp phản hồi trực tiếp nội dung từ AI lên Frontend theo thời gian thực.
