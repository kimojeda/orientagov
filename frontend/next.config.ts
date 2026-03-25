import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  
  // Habilita standalone output para optimizar para Docker/Cloud Run
  output: 'standalone',
  
  // Configuración para producción en Cloud Run
  compress: true,
  
  // Deshabilita la generación de source maps en producción (opcional)
  productionBrowserSourceMaps: false,
};

export default nextConfig;
