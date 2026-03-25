# Dockerfile para Next.js optimizado para Cloud Run
# Multi-stage build para reducir el tamaño de la imagen

# Etapa 1: Dependencias
FROM node:20-alpine AS deps
WORKDIR /app

# Instalar dependencias basadas en el package.json
COPY package.json package-lock.json* ./
RUN npm ci

# Etapa 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copiar dependencias desde la etapa anterior
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Deshabilitar telemetría de Next.js durante el build
ENV NEXT_TELEMETRY_DISABLED=1

# Construir la aplicación
RUN npm run build

# Etapa 3: Runner (producción)
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Crear usuario no-root para seguridad
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copiar archivos necesarios desde builder
COPY --from=builder /app/public ./public

# Copiar archivos del build standalone
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Cloud Run inyecta el PORT automáticamente
EXPOSE 8080
ENV PORT=8080
ENV HOSTNAME="0.0.0.0"

# Iniciar la aplicación
CMD ["node", "server.js"]
