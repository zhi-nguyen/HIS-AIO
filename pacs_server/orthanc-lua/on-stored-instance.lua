-- ==========================================================================
-- Orthanc Lua Script: Webhook khi Study ổn định
-- ==========================================================================
-- Hook: OnStableStudy
-- Mục đích: Khi Orthanc nhận xong toàn bộ ảnh của 1 study (không có ảnh mới
-- trong 60 giây — cấu hình bởi "StableAge"), script này tự động gọi
-- webhook về Django HIS backend để thông báo có study mới.
--
-- Tại sao dùng OnStableStudy thay vì OnStoredInstance?
-- → Một ca CT có thể có 500+ slices. Nếu dùng OnStoredInstance sẽ gọi
--   webhook 500 lần. OnStableStudy chỉ gọi 1 lần khi study hoàn tất.
-- ==========================================================================

-- URL của Django backend webhook
local DJANGO_WEBHOOK_URL = "http://backend:8000/api/v1/ris/orthanc-webhook/"

function OnStableStudy(studyId, tags, metadata)
    -- studyId: Orthanc internal ID (không phải StudyInstanceUID)
    -- Lấy thông tin chi tiết từ Orthanc REST API nội bộ
    local studyInfo = ParseJson(RestApiGet("/studies/" .. studyId))

    local studyInstanceUID = studyInfo["MainDicomTags"]["StudyInstanceUID"]
    local accessionNumber = studyInfo["MainDicomTags"]["AccessionNumber"] or ""
    local patientName = studyInfo["PatientMainDicomTags"]["PatientName"] or ""
    local patientID = studyInfo["PatientMainDicomTags"]["PatientID"] or ""
    local studyDescription = studyInfo["MainDicomTags"]["StudyDescription"] or ""
    local numberOfSeries = #studyInfo["Series"]

    -- Log thông tin
    print("=== OnStableStudy ===")
    print("Orthanc ID: " .. studyId)
    print("StudyInstanceUID: " .. studyInstanceUID)
    print("AccessionNumber: " .. accessionNumber)
    print("PatientID: " .. patientID)
    print("PatientName: " .. patientName)
    print("Series count: " .. numberOfSeries)

    -- Chuẩn bị payload JSON gửi về Django
    local payload = {
        ["orthanc_id"] = studyId,
        ["study_instance_uid"] = studyInstanceUID,
        ["accession_number"] = accessionNumber,
        ["patient_id"] = patientID,
        ["patient_name"] = patientName,
        ["study_description"] = studyDescription,
        ["number_of_series"] = numberOfSeries
    }

    local jsonPayload = DumpJson(payload, true)

    -- Gửi HTTP POST đến Django webhook
    -- Orthanc hỗ trợ HttpPost(url, body, content-type)
    local headers = {
        ["Content-Type"] = "application/json"
    }

    -- Gửi webhook, bọc trong pcall để không crash nếu Django offline
    local success, result = pcall(function()
        return HttpPost(DJANGO_WEBHOOK_URL, jsonPayload, headers)
    end)

    if success then
        print("Webhook sent successfully to Django for study: " .. studyInstanceUID)
    else
        print("WARNING: Failed to send webhook to Django: " .. tostring(result))
        print("Django backend may be offline. Study will need manual sync.")
    end

    print("=== End OnStableStudy ===")
end
