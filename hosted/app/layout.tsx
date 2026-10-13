import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'Kiki Control Room',description:'One Kiki. One shared history. A private place to get things moving.'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
