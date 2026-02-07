import { redirect } from 'next/navigation';

/**
 * Root Page
 * Redirect về trang login
 */
export default function HomePage() {
  redirect('/login');
}
