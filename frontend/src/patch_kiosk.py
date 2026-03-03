import codecs

with codecs.open('f:/BaiTap_DuAn/QuanLyBV/QuanLyBenhVienHIS/frontend/src/app/kiosk/page.tsx', 'r', 'utf-8') as f:
    content = f.read()

content = content.replace("import ScannerModal from '@/components/ScannerModal';", "import { useScannerListener } from '@/hooks/useScannerListener';")
content = content.replace("const [showScanner, setShowScanner] = useState(false);", "")

old_scan = """    const handleQrScanSuccess = useCallback((decodedText: string) => {
        setShowScanner(false);
        const parsed = parseCccdQrData(decodedText);

        console.log('--- KHÁCH HÀNG QUÉT QR TẠI KIOSK ---');
        console.log('Dữ liệu thô quét được:', decodedText);"""

new_scan = """    const handleScannerInput = useCallback((scannedText: string) => {
        if (!scannedText.includes('|')) {
            setScanData(scannedText);
            handleIdentify(scannedText);
            return;
        }

        const parsed = parseCccdQrData(scannedText);

        console.log('--- KHÁCH HÀNG QUÉT MÃ TẠI KIOSK ---');
        console.log('Dữ liệu thô quét được:', scannedText);"""

content = content.replace(old_scan, new_scan)

old_hook_anchor = """        setScanData(parsed.cccd);
        handleIdentify(parsed.cccd);
    }, [handleIdentify]);"""

new_hook_anchor = old_hook_anchor + """

    useScannerListener({
        onScan: handleScannerInput,
        preventDefaultOnMatch: true,
    });"""

content = content.replace(old_hook_anchor, new_hook_anchor)

old_qr_btn = """                                    <Button
                                        type="default"
                                        size="large"
                                        block
                                        onClick={() => setShowScanner(true)}
                                        icon={<QrcodeOutlined />}
                                        style={{
                                            height: 56,
                                            fontSize: 16,
                                            borderRadius: 16,
                                            background: 'rgba(255,255,255,0.1)',
                                            borderColor: 'rgba(255,255,255,0.2)',
                                            color: '#fff',
                                            fontWeight: 500,
                                        }}
                                    >
                                        Quét QR Camera
                                    </Button>
                                    <Button"""

new_qr_btn = """                                    <Button"""

content = content.replace(old_qr_btn, new_qr_btn)

content = content.replace('<div className="grid grid-cols-2 gap-4">', '<div className="grid grid-cols-1 gap-4">')

content = content.replace('Đặt thẻ CCCD hoặc thẻ BHYT lên máy quét, hoặc nhập mã số bên dưới', 'Vui lòng đưa mã QR hoặc thẻ CCCD vào máy quét, hoặc tự nhập mã số bên dưới')

old_modal = """            <ScannerModal
                open={showScanner}
                onCancel={() => setShowScanner(false)}
                onScanSuccess={handleQrScanSuccess}
            />"""
new_modal = ""
content = content.replace(old_modal, new_modal)

with codecs.open('f:/BaiTap_DuAn/QuanLyBV/QuanLyBenhVienHIS/frontend/src/app/kiosk/page.tsx', 'w', 'utf-8') as f:
    f.write(content)
print("Done patching Kiosk page")
