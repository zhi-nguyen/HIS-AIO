import type { Metadata } from "next";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider } from "antd";
import viVN from "antd/locale/vi_VN";
import { Geist } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";

/**
 * Root Layout
 * Cấu hình Ant Design với Next.js App Router
 */

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HIS - Hệ thống Quản lý Bệnh viện",
  description: "Hospital Information System with AI Integration",
  icons: {
    icon: "/favicon.ico",
  },
};

// Ant Design Theme - Healthcare Blue
const antTheme = {
  token: {
    colorPrimary: "#1E88E5",
    colorSuccess: "#4CAF50",
    colorWarning: "#FF9800",
    colorError: "#F44336",
    colorInfo: "#2196F3",
    borderRadius: 6,
    fontFamily: "'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 16,
  },
  components: {
    Layout: {
      siderBg: "#001529",
      headerBg: "#ffffff",
    },
    Menu: {
      darkItemBg: "#001529",
      darkItemSelectedBg: "#1E88E5",
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className={`${geistSans.variable} antialiased`}>
        <AntdRegistry>
          <ConfigProvider locale={viVN} theme={antTheme}>
            <AuthProvider>
              {children}
            </AuthProvider>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
