export interface ParsedCccd {
    cccd: string;
    oldId: string;
    fullName: string;
    dob: string | null;      // Format YYYY-MM-DD
    gender: 'M' | 'F' | 'O';
    address: string;
    issueDate: string | null; // Format YYYY-MM-DD
}

function parseDateStr(dateStr: string): string | null {
    if (!dateStr || dateStr.length !== 8) return null;
    const d = dateStr.substring(0, 2);
    const m = dateStr.substring(2, 4);
    const y = dateStr.substring(4, 8);
    return `${y}-${m}-${d}`;
}

export function parseCccdQrData(rawUrl: string): ParsedCccd | null {
    // Format: "001090123456|012345678|NGUYEN VAN A|01011990|Nam|Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh|15042021"
    const parts = rawUrl.split('|');
    if (parts.length < 6) return null;

    const cccd = parts[0];
    const oldId = parts[1];
    const fullName = parts[2];
    const dobStr = parts[3];
    const genderStr = parts[4];
    const address = parts[5];
    const issueDateStr = parts.length >= 7 ? parts[6] : '';

    let gender: 'M' | 'F' | 'O' = 'O';
    const gLow = genderStr.toLowerCase().trim();
    if (gLow === 'nam') gender = 'M';
    else if (gLow === 'nữ' || gLow === 'nu') gender = 'F';

    return {
        cccd,
        oldId,
        fullName,
        dob: parseDateStr(dobStr),
        gender,
        address,
        issueDate: issueDateStr ? parseDateStr(issueDateStr) : null
    };
}
