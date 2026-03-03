import codecs

with codecs.open('f:/BaiTap_DuAn/QuanLyBV/QuanLyBenhVienHIS/frontend/src/app/(dashboard)/dashboard/reception/CreateVisitModal.tsx', 'r', 'utf-8') as f:
    content = f.read()

content = content.replace("import ScannerModal from '@/components/ScannerModal';", "import { useScannerListener } from '@/hooks/useScannerListener';")
content = content.replace("const [showScanner, setShowScanner] = useState(false);", "")

old_scan = """    const handleQrScanSuccess = useCallback((decodedText: string) => {
        setShowScanner(false);
        const parsed = parseCccdQrData(decodedText);

        console.log('--- NHÂN VIÊN LỄ TÂN QUÉT QR ---');
        console.log('Dữ liệu thô quét được:', decodedText);"""

new_scan = """    const handleScannerInput = useCallback((scannedText: string) => {
        if (!scannedText.includes('|')) {
            setCccdInput(scannedText);
            handleCccdScan(scannedText);
            return;
        }

        const parsed = parseCccdQrData(scannedText);

        console.log('--- MÁY QUÉT NHẬN PHÍM ---');
        console.log('Dữ liệu thô quét được:', scannedText);"""

content = content.replace(old_scan, new_scan)

old_hook_anchor = """        // concurrently trigger BHYT lookup
        handleCccdScan(parsed.cccd);
    }, [emergencyMode, newPatientForm, message, handleCccdScan]);"""

new_hook_anchor = old_hook_anchor + """

    useScannerListener({
        onScan: handleScannerInput,
    });"""

content = content.replace(old_hook_anchor, new_hook_anchor)

old_qr_btn = """                <Input
                    value={cccdInput}
                    onChange={(e) => setCccdInput(e.target.value)}
                    placeholder="Nhập số CCCD (12 chữ số)"
                    maxLength={12}
                    onPressEnter={handleCccdScan}
                    prefix={<IdcardOutlined />}
                    style={{ flex: 1 }}
                    disabled={cccdLoading}
                />
                <Button
                    type="default"
                    icon={<QrcodeOutlined />}
                    onClick={() => setShowScanner(true)}
                >
                    Quét QR
                </Button>
                <Button
                    type="primary"
                    icon={<SearchOutlined />}"""

new_qr_btn = """                <Input
                    value={cccdInput}
                    onChange={(e) => setCccdInput(e.target.value)}
                    placeholder="Nhập số CCCD (12 chữ số)"
                    maxLength={12}
                    onPressEnter={handleCccdScan}
                    prefix={<IdcardOutlined />}
                    style={{ flex: 1 }}
                    disabled={cccdLoading}
                />
                <Button
                    type="primary"
                    icon={<SearchOutlined />}"""

content = content.replace(old_qr_btn, new_qr_btn)

# Add text above it
content = content.replace('<div className="flex gap-2">', '<div className="mb-2 text-sm text-gray-500 italic">💡 Vui lòng đưa mã QR hoặc thẻ CCCD vào máy quét.</div>\n            <div className="flex gap-2">')

old_modal_1 = """                {DiffModal}
                <ScannerModal
                    open={showScanner}
                    onCancel={() => setShowScanner(false)}
                    onScanSuccess={handleQrScanSuccess}
                />
            </>"""
new_modal_1 = """                {DiffModal}
            </>"""
content = content.replace(old_modal_1, new_modal_1)

old_modal_2 = """            {DiffModal}
            <ScannerModal
                open={showScanner}
                onCancel={() => setShowScanner(false)}
                onScanSuccess={handleQrScanSuccess}
            />
        </>"""
new_modal_2 = """            {DiffModal}
        </>"""
content = content.replace(old_modal_2, new_modal_2)

with codecs.open('f:/BaiTap_DuAn/QuanLyBV/QuanLyBenhVienHIS/frontend/src/app/(dashboard)/dashboard/reception/CreateVisitModal.tsx', 'w', 'utf-8') as f:
    f.write(content)
print("Done patching CreateVisitModal.tsx")
