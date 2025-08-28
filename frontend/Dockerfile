# =========================================================================
# STUFE 1: Build-Umgebung - Baut die React-Anwendung
# =========================================================================
FROM node:18-alpine AS builder

# Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# Die package.json und die pnpm-lock.yaml kopieren
COPY package.json pnpm-lock.yaml ./

# pnpm installieren, da die Lock-Datei eine pnpm-Datei ist
RUN npm install -g pnpm

# Die Frontend-Abhängigkeiten mit pnpm installieren
RUN pnpm install

# Den Rest des Frontend-Codes kopieren
COPY . .

# Die Anwendung für die Produktion bauen. 
# Dies erstellt einen optimierten 'dist'-Ordner.
RUN pnpm build

# =========================================================================
# STUFE 2: Produktions-Umgebung - Liefert die gebauten Dateien aus
# =========================================================================
FROM nginx:stable-alpine AS production

# Den Port 80 freigeben, auf dem Nginx standardmäßig läuft
EXPOSE 80

# Die benutzerdefinierte Nginx-Konfiguration kopieren.
# Diese überschreibt die Standardkonfiguration, um unsere SPA korrekt auszuliefern.
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf

# Die gebauten, statischen Dateien aus der Build-Umgebung in das
# öffentliche HTML-Verzeichnis von Nginx kopieren.
COPY --from=builder /app/dist /usr/share/nginx/html

# Der Standardbefehl des Nginx-Images startet den Server, 
# daher ist kein CMD hier nötig.