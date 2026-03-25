// src/app/layout.tsx
import './globals.css';
import type { ReactNode } from 'react';
import AuthProvider from './AuthProvider';

export const metadata = {
  title: 'OrientaGov',
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🇵🇪</text></svg>'
  }
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="flex flex-col h-screen bg-gray-50">
        <AuthProvider>
          {/* Barra superior estilo gob.pe */}
          <header className="bg-red-700 text-white px-6 py-3 flex items-center gap-3 shadow-md">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🇵🇪</span>
              <div>
                <div className="text-xl font-bold leading-tight tracking-wide">OrientaGov</div>
                <div className="text-xs opacity-80">Asistente de trámites del Estado Peruano</div>
              </div>
            </div>
            <div className="ml-auto flex items-center gap-6">
  <div className="flex items-center gap-1 opacity-90 hover:opacity-100">
    <img src="/logos/sbs.png" alt="SBS" className="h-6 object-contain brightness-0 invert" />
  </div>
  <div className="flex items-center gap-1 opacity-90 hover:opacity-100">
    <img src="/logos/sunat.png" alt="SUNAT" className="h-6 object-contain brightness-0 invert" />
  </div>
  <div className="flex items-center gap-1 opacity-90 hover:opacity-100">
    <img src="/logos/sunarp.png" alt="SUNARP" className="h-6 object-contain brightness-0 invert" />
  </div>
</div>
          </header>

          {/* Barra secundaria gris estilo gob.pe */}
          <div className="bg-gray-100 border-b border-gray-200 px-6 py-1">
            <p className="text-xs text-gray-500">
              Información basada en documentos TUPA oficiales del Estado Peruano
            </p>
          </div>

          <main className="flex-1 overflow-auto bg-gray-50 p-4">
            {children}
          </main>

          <footer className="bg-red-700 text-white text-center text-xs py-2 opacity-90">
            OrientaGov — Demo desarrollado para el curso de IA Generativa · Universidad Ricardo Palma 2026
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}