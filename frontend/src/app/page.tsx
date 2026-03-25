// src/app/page.tsx
'use client';

import { useSession, signIn, signOut } from 'next-auth/react';
import { useState, FormEvent } from 'react';

type Mensaje = { de: 'usuario' | 'bot'; texto: string };

export default function Page() {
  const { data: session } = useSession();
  const [chat, setChat] = useState<Mensaje[]>([
    {
      de: 'bot',
      texto: '¡Hola! Soy OrientaGov, tu asistente para trámites administrativos del Estado peruano. Puedo ayudarte con:\n\n🏦 SBS: trámites bancarios, seguros y AFP\n💰 SUNAT: trámites tributarios y aduaneros\n🏢 SUNARP: registro de propiedades y empresas\n\n¿En qué te puedo ayudar hoy?'
    }
  ]);
  const [msg, setMsg] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  // Si no hay sesión, mostramos pantalla de login
  if (!session) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-6">
        <div className="text-center">
          <div className="text-5xl mb-3">🇵🇪</div>
          <h1 className="text-2xl font-bold text-red-700 mb-1">OrientaGov</h1>
          <p className="text-gray-500 text-sm">Asistente de trámites del Estado Peruano</p>
        </div>
        <div className="bg-white rounded-xl shadow-md p-8 flex flex-col items-center gap-4 w-full max-w-sm">
          <p className="text-gray-600 text-center text-sm">
            Inicia sesión para acceder al asistente
          </p>
          <button
            onClick={() => signIn('google')}
            className="bg-red-700 hover:bg-red-800 text-white font-semibold px-6 py-3 rounded-lg flex items-center gap-2 w-full justify-center transition-colors"
          >
            <span>🔐</span>
            Ingresar con Google
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center max-w-xs">
          Información basada en documentos TUPA oficiales de SBS, SUNAT y SUNARP
        </p>
      </div>
    );
  }

  // Función para enviar mensaje
  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    if (!msg) return;
    setLoading(true);

    const userEmail = session.user?.email ?? '';
    const res = await fetch(
      `/api/agent?idagente=${encodeURIComponent(userEmail)}&msg=${encodeURIComponent(msg)}`
    );
    const texto = await res.text();

    setChat((c) => [
      ...c,
      { de: 'usuario', texto: msg },
      { de: 'bot', texto }
    ]);

    setMsg('');
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col max-w-3xl mx-auto">

      {/* Header usuario */}
      <div className="flex justify-between items-center mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-red-700 text-white flex items-center justify-center text-sm font-bold">
            {session.user?.email?.[0].toUpperCase()}
          </div>
          <span className="text-sm text-gray-600">{session.user?.email}</span>
        </div>
        <button
          onClick={() => signOut()}
          className="text-xs text-red-700 hover:underline border border-red-200 px-3 py-1 rounded-full hover:bg-red-50 transition-colors"
        >
          Cerrar sesión
        </button>
      </div>

      {/* Área de chat */}
      <div className="flex-1 overflow-y-auto space-y-3 pb-4 px-1">
        {chat.map((m, i) => (
          <div
            key={i}
            className={`p-3 rounded-xl max-w-[80%] text-sm leading-relaxed ${
              m.de === 'usuario'
                ? 'ml-auto bg-red-700 text-white text-right shadow-sm'
                : 'mr-auto bg-white border border-gray-200 text-gray-800 shadow-sm'
            }`}
          >
            {m.de === 'bot' && (
              <div className="flex items-center gap-1 mb-1 text-red-700 font-semibold text-xs">
                <span>🇵🇪</span> OrientaGov
              </div>
            )}
            {m.texto.split('\n').map((linea, j) => (
              <span key={j}>
                {linea}
                <br />
              </span>
            ))}
          </div>
        ))}
        {loading && (
          <div className="mr-auto bg-white border border-gray-200 text-gray-400 text-sm p-3 rounded-xl shadow-sm animate-pulse">
            OrientaGov está procesando tu consulta...
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={enviar} className="mt-2 flex gap-2">
        <input
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400"
          placeholder="Escribe tu consulta sobre trámites..."
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          disabled={loading}
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-red-700 hover:bg-red-800 text-white px-5 py-2 rounded-lg disabled:opacity-50 transition-colors text-sm font-medium"
        >
          {loading ? '...' : 'Enviar'}
        </button>
      </form>
    </div>
  );
}
